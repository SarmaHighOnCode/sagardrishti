package recorder

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"
	"testing"
	"time"

	"github.com/sagardrishti/aisd/internal/aisstream"
	"github.com/sagardrishti/aisd/internal/wal"
	"github.com/sagardrishti/go/aoi"
	"github.com/sagardrishti/go/store"
)

type fakeDB struct {
	mu        sync.Mutex
	failNext  bool
	positions [][]store.PositionRow
	statics   [][]store.StaticRow
}

func (f *fakeDB) WritePositions(ctx context.Context, rows []store.PositionRow) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	if f.failNext {
		f.failNext = false
		return errors.New("simulated db outage")
	}
	cp := append([]store.PositionRow(nil), rows...)
	f.positions = append(f.positions, cp)
	return nil
}

func (f *fakeDB) WriteStatic(ctx context.Context, rows []store.StaticRow) error {
	f.mu.Lock()
	defer f.mu.Unlock()
	cp := append([]store.StaticRow(nil), rows...)
	f.statics = append(f.statics, cp)
	return nil
}

func (f *fakeDB) totalPositions() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	n := 0
	for _, b := range f.positions {
		n += len(b)
	}
	return n
}

func samplePositionEnvelope(mmsi int64, lat, lon float64) []byte {
	return []byte(fmt.Sprintf(`{
  "MessageType": "PositionReport",
  "Message": {"PositionReport": {"Cog": 100, "Latitude": %v, "Longitude": %v, "NavigationalStatus": 0, "RateOfTurn": 0, "Sog": 12.3, "TrueHeading": 100, "Valid": true}},
  "MetaData": {"MMSI": %d, "time_utc": "2026-09-03 12:00:00 +0000 UTC"}
}`, lat, lon, mmsi))
}

func decodeForTest(raw []byte) (aisstream.Envelope, error) {
	return aisstream.UnmarshalEnvelope(raw)
}

func TestBuildPositionRow(t *testing.T) {
	aois := aoi.Default()

	env, err := decodeForTest(samplePositionEnvelope(123456789, 19.0, 72.8))
	if err != nil {
		t.Fatalf("decode: %v", err)
	}
	row, ok := buildPositionRow(env, aois, "aisstream")
	if !ok {
		t.Fatal("expected ok = true")
	}
	if row.MMSI != 123456789 || row.AOI != "arabian_sea" || row.DataQuality != "ok" {
		t.Errorf("unexpected row: %+v", row)
	}
	if row.SOGKnots == nil || *row.SOGKnots != 12.3 {
		t.Errorf("SOGKnots = %v, want 12.3", row.SOGKnots)
	}

	// Null Island must be flagged, not dropped.
	env2, _ := decodeForTest(samplePositionEnvelope(123456789, 0, 0))
	row2, ok := buildPositionRow(env2, aois, "aisstream")
	if !ok {
		t.Fatal("expected ok = true even for a flagged row")
	}
	if row2.DataQuality != "unreliable" {
		t.Errorf("DataQuality = %q, want unreliable", row2.DataQuality)
	}
}

func TestConsumeFlushesAtBatchSizeAndRotatesWAL(t *testing.T) {
	dir := t.TempDir()
	w, err := wal.Open(dir)
	if err != nil {
		t.Fatalf("wal.Open: %v", err)
	}
	// Windows disallows deleting a still-open file - close so TempDir
	// cleanup can remove the directory (Consume's shutdown flush does not
	// close the writer itself; only main()'s own defer does that).
	defer w.Close()

	db := &fakeDB{}
	r := New(Config{
		Source:        "aisstream",
		AOIs:          aoi.Default(),
		BatchSize:     3,
		FlushInterval: time.Hour, // effectively disabled - size trigger only
	}, w, db, nil)

	in := make(chan []byte)
	ctx, cancel := context.WithCancel(context.Background())

	done := make(chan error, 1)
	go func() { done <- r.Consume(ctx, in, func() int64 { return 0 }) }()

	for i := 0; i < 3; i++ {
		in <- samplePositionEnvelope(int64(1000+i), 19.0, 72.8)
	}

	// flush() writes to the DB, THEN calls wal.Rotate() — see recorder.go.
	// db.totalPositions() reaching 3 only proves the DB write happened;
	// Rotate() is a separate step straight after it, with no
	// synchronization the test can observe other than the WAL directory
	// itself. Waiting on the DB counter alone and then immediately
	// reading the directory is a real race: on a loaded CI runner the
	// goroutine can be observed between "DB write done" and "Rotate
	// done", making this test fail for a reason that has nothing to do
	// with a regression. Poll on the actual post-condition instead.
	deadline := time.After(2 * time.Second)
	var entries []os.DirEntry
	for {
		entries, _ = os.ReadDir(dir)
		if db.totalPositions() >= 3 && len(entries) == 1 {
			break
		}
		select {
		case <-deadline:
			t.Fatalf(
				"timed out waiting for flush+rotate: %d rows written, %d WAL segment(s) present",
				db.totalPositions(), len(entries),
			)
		case <-time.After(10 * time.Millisecond):
		}
	}

	cancel()
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatal("Consume did not return after cancel")
	}
}

func TestConsumeKeepsWALOnDBFailureThenRecovers(t *testing.T) {
	dir := t.TempDir()
	w, err := wal.Open(dir)
	if err != nil {
		t.Fatalf("wal.Open: %v", err)
	}
	// Windows disallows deleting a still-open file - close so TempDir
	// cleanup can remove the directory (Consume's shutdown flush does not
	// close the writer itself; only main()'s own defer does that).
	defer w.Close()

	db := &fakeDB{failNext: true}
	r := New(Config{
		Source:        "aisstream",
		AOIs:          aoi.Default(),
		BatchSize:     1,
		FlushInterval: time.Hour,
	}, w, db, nil)

	in := make(chan []byte)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	done := make(chan error, 1)
	go func() { done <- r.Consume(ctx, in, func() int64 { return 0 }) }()

	in <- samplePositionEnvelope(1001, 19.0, 72.8) // this flush fails (failNext)

	// Give the failed flush a moment, then confirm the segment survived it.
	time.Sleep(100 * time.Millisecond)
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatalf("expected the segment to survive a failed flush, got %d files", len(entries))
	}

	in <- samplePositionEnvelope(1002, 19.0, 72.8) // triggers a retry flush (batch size 1) that now succeeds

	deadline := time.After(2 * time.Second)
	for db.totalPositions() < 2 { // both rows land once the DB recovers
		select {
		case <-deadline:
			t.Fatalf("timed out, got %d rows", db.totalPositions())
		case <-time.After(10 * time.Millisecond):
		}
	}
}
