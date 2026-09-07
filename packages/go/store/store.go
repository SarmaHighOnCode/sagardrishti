// Package store batches decoded AIS records into TimescaleDB. Every write
// goes through a temp-table COPY followed by an ON CONFLICT DO NOTHING
// upsert: WAL replay after a crash between "DB commit succeeded" and "WAL
// segment deleted" will re-send rows aisd already wrote, and a plain COPY
// would abort the whole batch on the resulting primary-key collision.
//
// Promoted out of services/aisd/internal/store (5 Sept 2026, see ADR 0005)
// so services/aisgen can import it too. That import is the whole point:
// "the ingest path is identical for real and synthetic data" is true
// because both binaries call WritePositions/WriteStatic on this exact
// package, not because their callers happen to agree by convention.
package store

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type PositionRow struct {
	Time          time.Time
	MMSI          int64
	Lat, Lon      float64
	SOGKnots      *float64
	COGDegrees    *float64
	TrueHeading   *int16
	NavStatus     *int16
	RateOfTurn    *float64
	AOI           string
	Source        string
	DataQuality   string
	QualityReason *string
}

type StaticRow struct {
	Time         time.Time
	MMSI         int64
	IMO          *int64
	CallSign     *string
	ShipName     *string
	ShipType     *int16
	DimBow       *float64
	DimStern     *float64
	DimPort      *float64
	DimStarboard *float64
	Destination  *string
	Source       string
}

// Store wraps a connection pool. All methods are safe to call
// concurrently, though aisd's design only ever has one writer goroutine.
type Store struct {
	pool *pgxpool.Pool
}

func Connect(ctx context.Context, databaseURL string) (*Store, error) {
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping: %w", err)
	}
	return &Store{pool: pool}, nil
}

func (s *Store) Close() { s.pool.Close() }

func (s *Store) Ping(ctx context.Context) error { return s.pool.Ping(ctx) }

var positionColumns = []string{
	"time", "mmsi", "lat", "lon", "sog_knots", "cog_degrees",
	"true_heading", "nav_status", "rate_of_turn", "aoi", "source",
	"data_quality", "quality_reason",
}

// WritePositions upserts a batch of position rows. A batch with zero rows
// is a no-op - callers are not expected to guard against this themselves.
func (s *Store) WritePositions(ctx context.Context, rows []PositionRow) error {
	if len(rows) == 0 {
		return nil
	}
	values := make([][]any, len(rows))
	for i, r := range rows {
		values[i] = []any{
			r.Time, r.MMSI, r.Lat, r.Lon, r.SOGKnots, r.COGDegrees,
			r.TrueHeading, r.NavStatus, r.RateOfTurn, r.AOI, r.Source,
			r.DataQuality, r.QualityReason,
		}
	}
	return s.copyUpsert(ctx, "ais_positions", "ais_positions_staging", positionColumns,
		[]string{"mmsi", "time"}, values)
}

var staticColumns = []string{
	"time", "mmsi", "imo", "call_sign", "ship_name", "ship_type",
	"dim_bow", "dim_stern", "dim_port", "dim_starboard", "destination", "source",
}

// WriteStatic upserts a batch of static/voyage rows.
func (s *Store) WriteStatic(ctx context.Context, rows []StaticRow) error {
	if len(rows) == 0 {
		return nil
	}
	values := make([][]any, len(rows))
	for i, r := range rows {
		values[i] = []any{
			r.Time, r.MMSI, r.IMO, r.CallSign, r.ShipName, r.ShipType,
			r.DimBow, r.DimStern, r.DimPort, r.DimStarboard, r.Destination, r.Source,
		}
	}
	return s.copyUpsert(ctx, "ais_static", "ais_static_staging", staticColumns,
		[]string{"mmsi", "time"}, values)
}

// copyUpsert COPYs values into a same-shape temp table, then folds them
// into target with ON CONFLICT DO NOTHING on conflictCols. All inside one
// transaction so a mid-batch failure leaves target untouched.
func (s *Store) copyUpsert(ctx context.Context, target, stagingName string, columns, conflictCols []string, values [][]any) error {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback(ctx) //nolint:errcheck // no-op if Commit already succeeded

	createSQL := fmt.Sprintf(
		`CREATE TEMP TABLE %s (LIKE %s) ON COMMIT DROP`, stagingName, target,
	)
	if _, err := tx.Exec(ctx, createSQL); err != nil {
		return fmt.Errorf("create staging table: %w", err)
	}

	_, err = tx.CopyFrom(ctx,
		pgx.Identifier{stagingName},
		columns,
		pgx.CopyFromRows(values),
	)
	if err != nil {
		return fmt.Errorf("copy into staging: %w", err)
	}

	insertSQL := fmt.Sprintf(
		`INSERT INTO %s (%s) SELECT %s FROM %s ON CONFLICT (%s) DO NOTHING`,
		target, joinCols(columns), joinCols(columns), stagingName, joinCols(conflictCols),
	)
	if _, err := tx.Exec(ctx, insertSQL); err != nil {
		return fmt.Errorf("upsert from staging: %w", err)
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("commit: %w", err)
	}
	return nil
}

func joinCols(cols []string) string {
	out := ""
	for i, c := range cols {
		if i > 0 {
			out += ", "
		}
		out += c
	}
	return out
}
