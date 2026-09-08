package fleet

import (
	"math/rand"
	"testing"
)

func TestGenerateProducesRequestedCount(t *testing.T) {
	rng := rand.New(rand.NewSource(1))
	vessels := Generate(rng, DefaultProfiles(), 25, 0)
	if len(vessels) != 25 {
		t.Fatalf("Generate(n=25) returned %d vessels", len(vessels))
	}
}

func TestGeneratedMMSIsAreUniqueAndInTheSyntheticRange(t *testing.T) {
	rng := rand.New(rand.NewSource(2))
	vessels := Generate(rng, DefaultProfiles(), 50, 0)

	seen := map[int64]bool{}
	for _, v := range vessels {
		if v.MMSI < SyntheticMMSIBase {
			t.Errorf("vessel MMSI %d is below SyntheticMMSIBase %d", v.MMSI, SyntheticMMSIBase)
		}
		if seen[v.MMSI] {
			t.Errorf("duplicate MMSI %d within one Generate call", v.MMSI)
		}
		seen[v.MMSI] = true
	}
}

func TestMMSIOffsetAvoidsCrossBatchCollisions(t *testing.T) {
	rng := rand.New(rand.NewSource(3))
	first := Generate(rng, DefaultProfiles(), 10, 0)
	second := Generate(rng, DefaultProfiles(), 10, 10)

	seen := map[int64]bool{}
	for _, v := range first {
		seen[v.MMSI] = true
	}
	for _, v := range second {
		if seen[v.MMSI] {
			t.Errorf("MMSI %d collided across batches with different offsets", v.MMSI)
		}
	}
}

func TestGeneratedVesselsHavePlausibleDimensionsAndSpeed(t *testing.T) {
	rng := rand.New(rand.NewSource(4))
	profiles := DefaultProfiles()
	vessels := Generate(rng, profiles, 200, 0)

	byType := map[VesselType]TypeProfile{}
	for _, p := range profiles {
		byType[p.Type] = p
	}

	for _, v := range vessels {
		p := byType[v.Type]
		if v.LengthM < p.MinLengthM || v.LengthM > p.MaxLengthM {
			t.Errorf("%s vessel length %.1fm outside profile range [%.0f,%.0f]",
				v.Type, v.LengthM, p.MinLengthM, p.MaxLengthM)
		}
		if v.CruiseKnots < p.MinKnots || v.CruiseKnots > p.MaxKnots {
			t.Errorf("%s vessel speed %.1fkn outside profile range [%.0f,%.0f]",
				v.Type, v.CruiseKnots, p.MinKnots, p.MaxKnots)
		}
		if v.BeamM <= 0 || v.BeamM >= v.LengthM {
			t.Errorf("%s vessel beam %.1fm implausible against length %.1fm", v.Type, v.BeamM, v.LengthM)
		}
	}
}

func TestEveryVesselNameIsMarkedSynthetic(t *testing.T) {
	rng := rand.New(rand.NewSource(5))
	for _, v := range Generate(rng, DefaultProfiles(), 30, 0) {
		if len(v.Name) < len("SYNTHETIC") || v.Name[:9] != "SYNTHETIC" {
			t.Errorf("vessel name %q does not start with SYNTHETIC", v.Name)
		}
	}
}

func TestWeightedPickCoversEveryProfileGivenEnoughDraws(t *testing.T) {
	rng := rand.New(rand.NewSource(6))
	profiles := DefaultProfiles()
	seen := map[VesselType]bool{}
	for _, v := range Generate(rng, profiles, 500, 0) {
		seen[v.Type] = true
	}
	for _, p := range profiles {
		if !seen[p.Type] {
			t.Errorf("type %s never generated across 500 draws — weight or picker is broken", p.Type)
		}
	}
}

func TestGenerateIsDeterministicForASeededSource(t *testing.T) {
	a := Generate(rand.New(rand.NewSource(42)), DefaultProfiles(), 10, 0)
	b := Generate(rand.New(rand.NewSource(42)), DefaultProfiles(), 10, 0)
	for i := range a {
		if a[i] != b[i] {
			t.Fatalf("same seed produced different vessel at index %d: %+v vs %+v", i, a[i], b[i])
		}
	}
}
