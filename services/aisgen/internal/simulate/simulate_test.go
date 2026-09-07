package simulate

import (
	"reflect"
	"testing"
	"time"

	"github.com/sagardrishti/go/store"
)

func smallConfig(seed int64) Config {
	return Config{
		Seed:           seed,
		StartUTC:       time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC),
		NumVessels:     21, // multiple of 7: guarantees every confounder bucket in applyConfoundersAndCollect fires at least once
		Duration:       2 * time.Hour,
		ReportInterval: 10 * time.Minute, // 12 ticks/vessel — fast to run, long enough to exercise gaps/jumps
	}
}

// This is the test services/aisgen/README.md says "must exist before
// [the shared-ingest-path claim] is repeated anywhere else (a slide, the
// evidence dossier, a viva answer)". The guarantee is structural, not
// behavioural: Result.Positions/Statics are LITERALLY packages/go/store's
// own row types, the same ones aisd's recorder builds and passes to
// store.WritePositions/WriteStatic — so there is no second encoding that
// could diverge. Asserted via reflection so a future refactor that
// accidentally introduces a parallel row type fails this test with a
// readable message, not just a compile error somewhere else.
func TestPositionsAndStaticsAreAisdsOwnStoreTypes(t *testing.T) {
	res := Run(smallConfig(1))

	wantPos := reflect.TypeOf([]store.PositionRow(nil)).String()
	gotPos := reflect.TypeOf(res.Positions).String()
	if gotPos != wantPos {
		t.Errorf("Result.Positions type = %s, want %s", gotPos, wantPos)
	}

	wantStatic := reflect.TypeOf([]store.StaticRow(nil)).String()
	gotStatic := reflect.TypeOf(res.Statics).String()
	if gotStatic != wantStatic {
		t.Errorf("Result.Statics type = %s, want %s", gotStatic, wantStatic)
	}
}

// samePositionRow compares by VALUE, dereferencing the pointer fields.
// store.PositionRow carries several *float64/*int16 fields (nullable AIS
// values) — plain `==`/`!=` on the struct compares those pointers'
// addresses, not what they point to, so two independently-built rows
// with identical readings would almost always look "different" purely
// because two runs allocate separate backing floats. Caught by this
// test's first version failing on exactly that.
func samePositionRow(a, b store.PositionRow) bool {
	return a.Time.Equal(b.Time) &&
		a.MMSI == b.MMSI &&
		a.Lat == b.Lat &&
		a.Lon == b.Lon &&
		samePtr(a.SOGKnots, b.SOGKnots) &&
		samePtr(a.COGDegrees, b.COGDegrees) &&
		sameIntPtr(a.TrueHeading, b.TrueHeading) &&
		a.AOI == b.AOI &&
		a.Source == b.Source &&
		a.DataQuality == b.DataQuality &&
		sameStringPtr(a.QualityReason, b.QualityReason)
}

func samePtr(a, b *float64) bool {
	if a == nil || b == nil {
		return a == b
	}
	return *a == *b
}

func sameIntPtr(a, b *int16) bool {
	if a == nil || b == nil {
		return a == b
	}
	return *a == *b
}

func sameStringPtr(a, b *string) bool {
	if a == nil || b == nil {
		return a == b
	}
	return *a == *b
}

func TestRunIsDeterministicForAGivenSeed(t *testing.T) {
	a := Run(smallConfig(42))
	b := Run(smallConfig(42))

	if len(a.Positions) != len(b.Positions) {
		t.Fatalf("position count differs: %d vs %d", len(a.Positions), len(b.Positions))
	}
	for i := range a.Positions {
		if !samePositionRow(a.Positions[i], b.Positions[i]) {
			t.Fatalf("position row %d differs between two runs with the same seed:\n%+v\n%+v",
				i, a.Positions[i], b.Positions[i])
		}
	}
	if len(a.Ground.Events) != len(b.Ground.Events) {
		t.Fatalf("ground truth event count differs: %d vs %d", len(a.Ground.Events), len(b.Ground.Events))
	}
}

func TestDifferentSeedsProduceDifferentRuns(t *testing.T) {
	a := Run(smallConfig(1))
	b := Run(smallConfig(2))
	if len(a.Positions) > 0 && len(b.Positions) > 0 && samePositionRow(a.Positions[0], b.Positions[0]) {
		t.Error("two different seeds produced an identical first row — rng seeding is likely not wired through")
	}
}

func TestRunLabelsExactlyOneDischarger(t *testing.T) {
	res := Run(smallConfig(7))

	count := 0
	for _, e := range res.Ground.Events {
		if e.Label == "discharger" {
			count++
		}
	}
	if count != 1 {
		t.Errorf("ground truth contains %d discharger events, want exactly 1", count)
	}
}

func TestRunProducesEveryConfounderType(t *testing.T) {
	res := Run(smallConfig(9))

	seen := map[string]bool{}
	for _, e := range res.Ground.Events {
		if e.Confounder != "" {
			seen[e.Confounder] = true
		}
	}
	for _, want := range []string{"ais_gap", "position_jump", "mmsi_duplicate"} {
		if !seen[want] {
			t.Errorf("ground truth never recorded a %q confounder event with 21 vessels (multiple of 7)", want)
		}
	}
}

func TestEveryRowCarriesTheConfiguredSource(t *testing.T) {
	res := Run(smallConfig(3))
	for i, r := range res.Positions {
		if r.Source != "aisgen" {
			t.Fatalf("position row %d Source = %q, want %q", i, r.Source, "aisgen")
		}
	}
	for i, r := range res.Statics {
		if r.Source != "aisgen" {
			t.Fatalf("static row %d Source = %q, want %q", i, r.Source, "aisgen")
		}
	}
}

func TestCustomSourceIsRespected(t *testing.T) {
	cfg := smallConfig(4)
	cfg.Source = "aisgen-test"
	res := Run(cfg)
	if len(res.Positions) == 0 {
		t.Fatal("no positions generated")
	}
	if res.Positions[0].Source != "aisgen-test" {
		t.Errorf("Source = %q, want %q", res.Positions[0].Source, "aisgen-test")
	}
}

func TestPositionsStayWithinValidCoordinateRange(t *testing.T) {
	res := Run(smallConfig(5))
	for i, r := range res.Positions {
		if r.Lat < -90 || r.Lat > 90 {
			t.Errorf("row %d has an out-of-range latitude %v", i, r.Lat)
		}
		if r.Lon < -180 || r.Lon > 180 {
			t.Errorf("row %d has an out-of-range longitude %v", i, r.Lon)
		}
	}
}

func TestMMSIDuplicateConfounderAddsRowsUnderADifferentMMSI(t *testing.T) {
	res := Run(smallConfig(9))

	mmsiSet := map[int64]bool{}
	for _, r := range res.Positions {
		mmsiSet[r.MMSI] = true
	}

	dupFound := false
	for mmsi := range mmsiSet {
		if mmsi >= 900500000 {
			dupFound = true
			break
		}
	}
	if !dupFound {
		t.Error("expected at least one duplicated-MMSI track (>= 900500000) among generated positions")
	}
}
