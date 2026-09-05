// Package recorder wires the AISStream client, the write-ahead log and the
// database together: decode, quality-flag, batch, and flush.
package recorder

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"time"

	"github.com/sagardrishti/aisd/internal/aisstream"
	"github.com/sagardrishti/aisd/internal/aoi"
	"github.com/sagardrishti/aisd/internal/quality"
	"github.com/sagardrishti/aisd/internal/store"
	"github.com/sagardrishti/aisd/internal/wal"
)

// AIS spec "not available" sentinels.
const (
	cogNotAvailable     = 360.0
	headingNotAvailable = 511
)

// maxBatchMultiple bounds how far a batch is allowed to grow past
// BatchSize while the database is unreachable. Past that, the oldest rows
// are dropped from memory (they remain safely in the WAL - see
// docs in internal/wal - and require a manual WAL replay tool to recover,
// which is a known, documented gap for extended outages rather than an
// unbounded memory leak).
const maxBatchMultiple = 10

type Config struct {
	Source        string
	AOIs          []aoi.Named
	BatchSize     int
	FlushInterval time.Duration
	StatusPath    string
}

// DB is the persistence dependency Recorder needs. *store.Store satisfies
// it; tests use a fake so recorder logic (batching, quality flags, WAL
// interplay) is verifiable without a live Postgres.
type DB interface {
	WritePositions(ctx context.Context, rows []store.PositionRow) error
	WriteStatic(ctx context.Context, rows []store.StaticRow) error
}

type Recorder struct {
	cfg    Config
	wal    *wal.Writer
	db     DB
	logger *slog.Logger

	positions []store.PositionRow
	statics   []store.StaticRow

	status Status
}

// Status is written to StatusPath as JSON after every flush attempt, so
// `make ais-status` (tools/ais_status.py) can report health without
// needing to talk to aisd directly.
type Status struct {
	StartedAt time.Time `json:"started_at"`
	// json's "omitzero" tag option needs Go 1.24+; this module targets
	// 1.23, so a never-set timestamp serializes as the zero time rather
	// than being omitted. tools/ais_status.py treats that as "never".
	LastMessageAt      time.Time `json:"last_message_at"`
	LastFlushAt        time.Time `json:"last_flush_at"`
	LastFlushError     string    `json:"last_flush_error,omitempty"`
	MessagesReceived   int64     `json:"messages_received"`
	PositionsPersisted int64     `json:"positions_persisted"`
	StaticsPersisted   int64     `json:"statics_persisted"`
	RowsDroppedFromMem int64     `json:"rows_dropped_from_memory"`
	Reconnects         int64     `json:"reconnects"`
}

func New(cfg Config, w *wal.Writer, db DB, logger *slog.Logger) *Recorder {
	if logger == nil {
		logger = slog.Default()
	}
	if cfg.BatchSize <= 0 {
		cfg.BatchSize = 500
	}
	if cfg.FlushInterval <= 0 {
		cfg.FlushInterval = 5 * time.Second
	}
	return &Recorder{
		cfg:    cfg,
		wal:    w,
		db:     db,
		logger: logger,
		status: Status{StartedAt: time.Now().UTC()},
	}
}

// Consume reads raw envelopes from in until ctx is done or in is closed. It
// appends every message to the WAL before decoding it, so a decode failure
// never loses data - it only means that one message will not have a row
// in Postgres until a future WAL-replay tool is run.
//
// reconnects is polled (not pushed) so the recorder never needs a second
// synchronization path with the AISStream client.
func (r *Recorder) Consume(ctx context.Context, in <-chan []byte, reconnects func() int64) error {
	ticker := time.NewTicker(r.cfg.FlushInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			r.status.Reconnects = reconnects()
			_ = r.flush(context.Background()) // best-effort final flush on shutdown
			return ctx.Err()

		case raw, ok := <-in:
			if !ok {
				r.status.Reconnects = reconnects()
				_ = r.flush(context.Background())
				return nil
			}
			r.handle(raw)
			if len(r.positions)+len(r.statics) >= r.cfg.BatchSize {
				r.status.Reconnects = reconnects()
				if err := r.flush(ctx); err != nil {
					r.logger.Error("flush failed", "error", err)
				}
			}

		case <-ticker.C:
			r.status.Reconnects = reconnects()
			if err := r.flush(ctx); err != nil {
				r.logger.Error("flush failed", "error", err)
			}
		}
	}
}

func (r *Recorder) handle(raw []byte) {
	if err := r.wal.Append(raw); err != nil {
		// The WAL is the durability guarantee. If we can't even append to
		// it, keep going rather than crash the whole recorder over one
		// message - but this is loud because it means the guarantee is
		// currently not being met.
		r.logger.Error("WAL append failed - message durability at risk", "error", err)
	}
	r.status.MessagesReceived++
	r.status.LastMessageAt = time.Now().UTC()

	env, err := aisstream.UnmarshalEnvelope(raw)
	if err != nil {
		r.logger.Warn("envelope decode failed, message kept in WAL only", "error", err)
		return
	}

	if row, ok := buildPositionRow(env, r.cfg.AOIs, r.cfg.Source); ok {
		r.positions = append(r.positions, row)
	}
	if row, ok := buildStaticRow(env, r.cfg.Source); ok {
		r.statics = append(r.statics, row)
	}

	r.trimIfOversized()
}

func (r *Recorder) trimIfOversized() {
	max := r.cfg.BatchSize * maxBatchMultiple
	if excess := len(r.positions) - max; excess > 0 {
		r.logger.Warn("position batch exceeded memory cap, dropping oldest rows from memory (still in WAL)",
			"dropped", excess)
		r.positions = r.positions[excess:]
		r.status.RowsDroppedFromMem += int64(excess)
	}
	if excess := len(r.statics) - max; excess > 0 {
		r.logger.Warn("static batch exceeded memory cap, dropping oldest rows from memory (still in WAL)",
			"dropped", excess)
		r.statics = r.statics[excess:]
		r.status.RowsDroppedFromMem += int64(excess)
	}
}

// flush is also the shared implementation used by WAL replay at startup -
// see ReplayHandler.
func (r *Recorder) flush(ctx context.Context) error {
	if len(r.positions) == 0 && len(r.statics) == 0 {
		return nil
	}

	if err := r.wal.Sync(); err != nil {
		r.recordFlushError(err)
		return err
	}

	if err := r.db.WritePositions(ctx, r.positions); err != nil {
		r.recordFlushError(err)
		return err
	}
	if err := r.db.WriteStatic(ctx, r.statics); err != nil {
		r.recordFlushError(err)
		return err
	}

	if err := r.wal.Rotate(); err != nil {
		// The DB write succeeded but we failed to clear the WAL segment.
		// Not data-loss (the opposite risk - the segment will be replayed
		// again next start and de-duplicated by ON CONFLICT DO NOTHING),
		// so this is a warning, not a reason to fail the flush.
		r.logger.Warn("WAL rotate failed after successful DB commit, segment will be replayed and de-duplicated next start", "error", err)
	}

	r.status.PositionsPersisted += int64(len(r.positions))
	r.status.StaticsPersisted += int64(len(r.statics))
	r.status.LastFlushAt = time.Now().UTC()
	r.status.LastFlushError = ""
	r.positions = r.positions[:0]
	r.statics = r.statics[:0]

	r.writeStatus()
	return nil
}

func (r *Recorder) recordFlushError(err error) {
	r.status.LastFlushError = err.Error()
	r.writeStatus()
}

func (r *Recorder) writeStatus() {
	if r.cfg.StatusPath == "" {
		return
	}
	f, err := os.CreateTemp(dirOf(r.cfg.StatusPath), "aisd-status-*.tmp")
	if err != nil {
		r.logger.Error("status write failed", "error", err)
		return
	}
	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	if err := enc.Encode(r.status); err != nil {
		r.logger.Error("status encode failed", "error", err)
		_ = f.Close()
		_ = os.Remove(f.Name())
		return
	}
	_ = f.Close()
	// Rename is atomic on the same filesystem - readers (tools/ais_status.py)
	// never observe a half-written file.
	if err := os.Rename(f.Name(), r.cfg.StatusPath); err != nil {
		r.logger.Error("status rename failed", "error", err)
		_ = os.Remove(f.Name())
	}
}

func dirOf(path string) string {
	for i := len(path) - 1; i >= 0; i-- {
		if path[i] == '/' || path[i] == '\\' {
			return path[:i]
		}
	}
	return "."
}

func buildPositionRow(env aisstream.Envelope, aois []aoi.Named, source string) (store.PositionRow, bool) {
	pr, ok := aisstream.ParsePositionReport(env)
	if !ok {
		return store.PositionRow{}, false
	}

	lat, lon := pr.Latitude, pr.Longitude
	ts := env.MetaData.TimeUTC.Time
	if ts.IsZero() {
		ts = time.Now().UTC()
	}

	// 102.3 knots is the AIS "speed not available" sentinel, not a real
	// reading - see quality.NotAvailableKnots.
	sogValid := pr.Valid && pr.Sog < quality.NotAvailableKnots-0.05
	var sogPtr *float64
	if sogValid {
		v := pr.Sog
		sogPtr = &v
	}

	status, reason := quality.Check(env.MetaData.MMSI, lat, lon, pr.Sog, sogValid)
	var reasonPtr *string
	if reason != "" {
		reasonPtr = &reason
	}

	var cogPtr *float64
	if pr.Cog < cogNotAvailable {
		v := pr.Cog
		cogPtr = &v
	}
	var headingPtr *int16
	if pr.TrueHeading != headingNotAvailable {
		v := int16(pr.TrueHeading)
		headingPtr = &v
	}
	navStatus := int16(pr.NavigationalStatus)
	rot := pr.RateOfTurn

	aoiName := aoi.Classify(aois, lat, lon)
	if aoiName == "" {
		aoiName = "unassigned"
	}

	return store.PositionRow{
		Time:          ts,
		MMSI:          env.MetaData.MMSI,
		Lat:           lat,
		Lon:           lon,
		SOGKnots:      sogPtr,
		COGDegrees:    cogPtr,
		TrueHeading:   headingPtr,
		NavStatus:     &navStatus,
		RateOfTurn:    &rot,
		AOI:           aoiName,
		Source:        source,
		DataQuality:   status,
		QualityReason: reasonPtr,
	}, true
}

// ReplayInto decodes a batch of raw WAL lines recovered from a previous
// crash and durably writes any resulting rows to db. See wal.Replay: this
// is the handle callback main() passes it before starting the live feed.
func ReplayInto(ctx context.Context, db DB, aois []aoi.Named, source string, lines [][]byte) error {
	var positions []store.PositionRow
	var statics []store.StaticRow
	for _, line := range lines {
		env, err := aisstream.UnmarshalEnvelope(line)
		if err != nil {
			continue // unparseable at recording time too; nothing more to extract now
		}
		if row, ok := buildPositionRow(env, aois, source); ok {
			positions = append(positions, row)
		}
		if row, ok := buildStaticRow(env, source); ok {
			statics = append(statics, row)
		}
	}
	if err := db.WritePositions(ctx, positions); err != nil {
		return err
	}
	return db.WriteStatic(ctx, statics)
}

func buildStaticRow(env aisstream.Envelope, source string) (store.StaticRow, bool) {
	ssd, ok := aisstream.ParseShipStaticData(env)
	if !ok {
		return store.StaticRow{}, false
	}

	ts := env.MetaData.TimeUTC.Time
	if ts.IsZero() {
		ts = time.Now().UTC()
	}

	row := store.StaticRow{
		Time:   ts,
		MMSI:   env.MetaData.MMSI,
		Source: source,
	}
	if ssd.ImoNumber > 0 {
		v := ssd.ImoNumber
		row.IMO = &v
	}
	if ssd.CallSign != "" {
		v := ssd.CallSign
		row.CallSign = &v
	}
	name := ssd.Name
	if name != "" {
		row.ShipName = &name
	}
	if ssd.Type > 0 {
		v := int16(ssd.Type)
		row.ShipType = &v
	}
	if ssd.Destination != "" {
		v := ssd.Destination
		row.Destination = &v
	}
	if d := ssd.Dimension; d.A+d.B+d.C+d.D > 0 {
		a, b, c, dd := d.A, d.B, d.C, d.D
		row.DimBow, row.DimStern, row.DimPort, row.DimStarboard = &a, &b, &c, &dd
	}
	return row, true
}
