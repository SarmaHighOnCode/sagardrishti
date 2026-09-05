// Package quality flags implausible AIS records without ever dropping
// them. See db/README.md: rows failing the pre-filter are marked
// `unreliable`, never deleted, so they stay auditable and scoring queries
// can exclude them explicitly.
package quality

import "math"

const (
	OK         = "ok"
	Unreliable = "unreliable"

	// MaxPlausibleKnots is generous on purpose - this is a data-quality
	// gate, not a vessel-performance model. AIS SOG field also uses 102.3
	// as a "not available" sentinel; treat that as unreliable too.
	MaxPlausibleKnots = 60.0
	NotAvailableKnots = 102.3
)

// Check inspects a single position report and returns ("ok", "") or
// ("unreliable", reason).
//
// sogValid must be false whenever the caller has already recognised the
// AIS "speed not available" sentinel (102.3 knots, see NotAvailableKnots) -
// that is an extremely common, entirely legitimate reading, not a quality
// problem, and the caller is expected to store a NULL speed for it rather
// than pass it through here.
func Check(mmsi int64, lat, lon float64, sogKnots float64, sogValid bool) (status, reason string) {
	if mmsi <= 0 {
		return Unreliable, "mmsi_zero"
	}
	if lat == 0 && lon == 0 {
		return Unreliable, "null_island"
	}
	if math.Abs(lat) > 90 || math.Abs(lon) > 180 {
		return Unreliable, "out_of_range"
	}
	if sogValid && sogKnots > MaxPlausibleKnots {
		return Unreliable, "implausible_speed"
	}
	return OK, ""
}

// CheckStatic flags garbled static/voyage data. IMO and call sign are
// frequently blank in the wild (Class B, older fits) - that alone is not
// a quality failure, only an all-zero or missing MMSI is.
func CheckStatic(mmsi int64) (status, reason string) {
	if mmsi <= 0 {
		return Unreliable, "mmsi_zero"
	}
	return OK, ""
}
