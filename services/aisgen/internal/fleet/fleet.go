// Package fleet generates the population of synthetic vessels a
// simulation run populates its lanes with: type, name, dimensions, and a
// per-type speed distribution. See services/aisgen/README.md requirements
// 2-3.
package fleet

import "math/rand"

// SyntheticMMSIBase is the first MMSI issued to a generated vessel. 900
// is not an ITU-assigned Maritime Identification Digit as of this
// writing (real MIDs are 3-digit codes under 800; India's own is 419) -
// chosen specifically so a synthetic MMSI can never collide with a real
// one aisd might record into the same table. See db/README.md: aisd and
// aisgen share ais_positions, distinguished by the `source` column, not
// by MMSI range - this is a belt-and-suspenders safety margin, not the
// mechanism the distinction actually depends on.
const SyntheticMMSIBase = 900000000

// VesselType names the categories services/aisgen/README.md requirement 2
// calls for: "tanker / container / bulker / fishing / tug".
type VesselType string

const (
	Tanker    VesselType = "tanker"
	Container VesselType = "container"
	Bulker    VesselType = "bulker"
	Fishing   VesselType = "fishing"
	Tug       VesselType = "tug"
)

// TypeProfile is everything Vessel generation needs to know about one
// VesselType: how common it is, how fast it typically moves, and roughly
// how large it is (for dim_bow/dim_stern/dim_port/dim_starboard).
type TypeProfile struct {
	Type VesselType
	// Weight determines this type's share of a generated fleet -
	// proportional, not a percentage; see weightedPick.
	Weight float64
	// AIS ship_type code (COLREGS/ITU categories 70-89 cover cargo through
	// pleasure craft; these are representative single values per bucket,
	// not the full real-world spread).
	AISShipType int16
	// Cruising speed range, knots. Sampled uniformly per vessel then held
	// roughly constant with jitter - see Vessel.CruiseKnots.
	MinKnots, MaxKnots float64
	// Length range in metres, used to derive dim_bow/dim_stern (split
	// asymmetrically, as pgx/store rows do for real ships) and
	// dim_port/dim_starboard (beam, held at LengthM/7 as a rough
	// length-to-beam ratio typical of commercial ships).
	MinLengthM, MaxLengthM float64
}

// DefaultProfiles is the Indian-waters-representative distribution
// services/aisgen/README.md requirement 2 asks for: tankers and
// containers dominate Arabian Sea/Bay of Bengal transit traffic, fishing
// vessels are numerous but small, tugs are rare and slow.
func DefaultProfiles() []TypeProfile {
	return []TypeProfile{
		{Type: Tanker, Weight: 0.28, AISShipType: 80, MinKnots: 10, MaxKnots: 15, MinLengthM: 150, MaxLengthM: 330},
		{Type: Container, Weight: 0.27, AISShipType: 70, MinKnots: 14, MaxKnots: 22, MinLengthM: 180, MaxLengthM: 400},
		{Type: Bulker, Weight: 0.22, AISShipType: 70, MinKnots: 10, MaxKnots: 14, MinLengthM: 150, MaxLengthM: 300},
		{Type: Fishing, Weight: 0.18, AISShipType: 30, MinKnots: 6, MaxKnots: 11, MinLengthM: 15, MaxLengthM: 35},
		{Type: Tug, Weight: 0.05, AISShipType: 52, MinKnots: 8, MaxKnots: 12, MinLengthM: 20, MaxLengthM: 40},
	}
}

// Vessel is one generated ship: static identity plus the cruise
// parameters simulate.Simulate uses to move it and to fill in
// sog_knots/dim_* on every emitted row.
type Vessel struct {
	MMSI        int64
	Name        string
	Type        VesselType
	AISShipType int16
	LengthM     float64
	BeamM       float64
	CruiseKnots float64
	// LaneName + LaneOffsetKm + StartFractionAlongLane place this vessel
	// on one of lanes.Default()'s lanes at simulation start - see
	// simulate.Simulate, which owns picking these to keep fleet vessel-
	// shape concerns separate from lane-placement concerns.
}

// Generate returns n vessels, each independently typed by weighted
// sampling of profiles, with an MMSI counting up from SyntheticMMSIBase +
// offset so repeated calls in one process (e.g. discharger + confounder
// fleets) never collide. Deterministic for a given rng seed - callers
// wanting reproducible runs should pass a seeded *rand.Rand, not the
// global source.
func Generate(rng *rand.Rand, profiles []TypeProfile, n int, mmsiOffset int64) []Vessel {
	vessels := make([]Vessel, n)
	for i := range vessels {
		p := weightedPick(rng, profiles)
		lengthM := p.MinLengthM + rng.Float64()*(p.MaxLengthM-p.MinLengthM)
		vessels[i] = Vessel{
			MMSI:        SyntheticMMSIBase + mmsiOffset + int64(i),
			Name:        syntheticName(p.Type, mmsiOffset+int64(i)),
			Type:        p.Type,
			AISShipType: p.AISShipType,
			LengthM:     lengthM,
			BeamM:       lengthM / 7,
			CruiseKnots: p.MinKnots + rng.Float64()*(p.MaxKnots-p.MinKnots),
		}
	}
	return vessels
}

func weightedPick(rng *rand.Rand, profiles []TypeProfile) TypeProfile {
	total := 0.0
	for _, p := range profiles {
		total += p.Weight
	}
	r := rng.Float64() * total
	for _, p := range profiles {
		if r < p.Weight {
			return p
		}
		r -= p.Weight
	}
	return profiles[len(profiles)-1]
}

// syntheticName produces an identifiably-synthetic vessel name.
// "SYNTHETIC" is not decorative here — docs/HANDOVER.md and the console
// (web/src/lib/fixtures.ts's IS_SYNTHETIC flag) both key off exactly this
// word to badge generated data; dropping it would let a demo screen show
// invented vessels with no visual distinction from a real one.
func syntheticName(t VesselType, n int64) string {
	return "SYNTHETIC " + string(t) + " " + itoa(n)
}

func itoa(n int64) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
