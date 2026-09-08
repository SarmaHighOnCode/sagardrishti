package store

import (
	"context"
	"os"
	"testing"
	"time"
)

// TestWritePositionsAgainstALiveDatabase and its sibling below are what
// TestWriteEmptyBatchesAreNoops (store_test.go) could never be: proof
// against a REAL Postgres, not just the nil-pool no-op path. Written
// after exactly the bug that gap let through — CREATE TEMP TABLE (LIKE
// target) does not copy DEFAULT expressions, so every COPY into the
// staging table failed "null value in column recorded_at violates
// not-null constraint" the first time this code ever ran against a real
// database (aisgen, 8 September 2026), despite store_test.go being green
// the whole time. See copyUpsert's own comment on the fix.
//
// Skipped unless SAGAR_TEST_DATABASE_URL is set — no live Postgres in
// CI, and that is the correct default rather than a CI job standing up
// a database just for this. Run locally against the docker-compose db:
//
//	docker compose up -d db
//	SAGAR_TEST_DATABASE_URL=postgresql://sagar:change_me_locally@localhost:5432/sagardrishti \
//	  go test ./store/... -run LiveDatabase -v
//
// (localhost, not `db` — this runs as a native process on the host, not
// inside the compose network. See db/README.md for the port-5432 gotcha
// this can collide with on a machine that also runs a native Postgres.)
func testDatabaseURL(t *testing.T) string {
	t.Helper()
	url := os.Getenv("SAGAR_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SAGAR_TEST_DATABASE_URL not set — skipping live-database test. " +
			"Set it to a real Postgres (docker compose up -d db) to run this.")
	}
	return url
}

func TestWritePositionsAgainstALiveDatabaseLiveDatabase(t *testing.T) {
	url := testDatabaseURL(t)
	ctx := context.Background()

	s, err := Connect(ctx, url)
	if err != nil {
		t.Fatalf("Connect: %v", err)
	}
	// t.Cleanup, not a plain defer: a defer in this function runs as
	// soon as the function returns, which is BEFORE the t.Cleanup
	// callback below fires (t.Cleanup runs as part of the testing
	// framework's own teardown, after the test function has already
	// returned). Registered first so it runs LAST, in Cleanup's LIFO
	// order — after the delete-cleanup below has had a chance to use
	// the still-open pool. Getting this backwards (as an earlier version
	// of this test did) closes the pool before the cleanup DELETE can
	// run, so the delete silently no-ops and test rows are left behind.
	t.Cleanup(func() { s.Close() })

	// A MMSI reserved for this test alone (see fleet.SyntheticMMSIBase's
	// own reasoning for why a high, clearly-synthetic range is safe to
	// use without colliding with anything real) so cleanup is a precise
	// DELETE, not a TRUNCATE that could destroy someone else's data on a
	// shared or already-populated database.
	const testMMSI = int64(999999001)
	now := time.Now().UTC().Truncate(time.Second)

	t.Cleanup(func() {
		cleanupCtx := context.Background()
		_, _ = s.pool.Exec(cleanupCtx, "DELETE FROM ais_positions WHERE mmsi = $1", testMMSI)
		_, _ = s.pool.Exec(cleanupCtx, "DELETE FROM ais_static WHERE mmsi = $1", testMMSI)
	})

	sog := 8.5
	rows := []PositionRow{
		{
			Time: now, MMSI: testMMSI, Lat: 10.0, Lon: 75.0,
			SOGKnots: &sog, AOI: "arabian_sea", Source: "store_test",
			DataQuality: "ok",
		},
	}

	if err := s.WritePositions(ctx, rows); err != nil {
		t.Fatalf("WritePositions against a live database: %v", err)
	}

	// recorded_at is deliberately never supplied by the caller — the
	// table's own DEFAULT now() is what is meant to stamp it. This is
	// the exact column the INCLUDING DEFAULTS fix was for: read it back
	// and confirm it is non-null and sane, not just that the insert
	// didn't error.
	var recordedAt time.Time
	var gotLat, gotLon float64
	err = s.pool.QueryRow(ctx,
		`SELECT lat, lon, recorded_at FROM ais_positions WHERE mmsi = $1`, testMMSI,
	).Scan(&gotLat, &gotLon, &recordedAt)
	if err != nil {
		t.Fatalf("row was not written or not readable back: %v", err)
	}
	if recordedAt.IsZero() {
		t.Error("recorded_at is zero — the staging table's DEFAULT now() did not apply")
	}
	if time.Since(recordedAt) > time.Minute {
		t.Errorf("recorded_at = %v, want roughly now (DEFAULT now() should have just fired)", recordedAt)
	}
	if gotLat != 10.0 || gotLon != 75.0 {
		t.Errorf("got lat/lon (%v,%v), want (10.0,75.0)", gotLat, gotLon)
	}

	// ON CONFLICT DO NOTHING on (mmsi, time): writing the identical batch
	// again must not error and must not duplicate the row.
	if err := s.WritePositions(ctx, rows); err != nil {
		t.Fatalf("WritePositions a second time (should be an idempotent no-op via ON CONFLICT): %v", err)
	}
	var count int
	if err := s.pool.QueryRow(ctx,
		`SELECT count(*) FROM ais_positions WHERE mmsi = $1`, testMMSI,
	).Scan(&count); err != nil {
		t.Fatalf("count query: %v", err)
	}
	if count != 1 {
		t.Errorf("row count after writing the same batch twice = %d, want 1 (ON CONFLICT DO NOTHING should have deduplicated)", count)
	}
}

func TestWriteStaticAgainstALiveDatabaseLiveDatabase(t *testing.T) {
	url := testDatabaseURL(t)
	ctx := context.Background()

	s, err := Connect(ctx, url)
	if err != nil {
		t.Fatalf("Connect: %v", err)
	}
	// See the sibling test's identical comment on why this is
	// t.Cleanup, not defer.
	t.Cleanup(func() { s.Close() })

	const testMMSI = int64(999999002)
	now := time.Now().UTC().Truncate(time.Second)

	t.Cleanup(func() {
		cleanupCtx := context.Background()
		_, _ = s.pool.Exec(cleanupCtx, "DELETE FROM ais_static WHERE mmsi = $1", testMMSI)
	})

	name := "STORE TEST VESSEL"
	rows := []StaticRow{
		{Time: now, MMSI: testMMSI, ShipName: &name, Source: "store_test"},
	}

	if err := s.WriteStatic(ctx, rows); err != nil {
		t.Fatalf("WriteStatic against a live database: %v", err)
	}

	var recordedAt time.Time
	err = s.pool.QueryRow(ctx,
		`SELECT recorded_at FROM ais_static WHERE mmsi = $1`, testMMSI,
	).Scan(&recordedAt)
	if err != nil {
		t.Fatalf("row was not written or not readable back: %v", err)
	}
	if recordedAt.IsZero() {
		t.Error("recorded_at is zero — the same DEFAULT-copying bug as ais_positions, on the static table")
	}
}
