// Package geo is the small set of geodesic primitives the Go side of the
// AIS data plane needs: distance and bearing between two points, and a
// point some fraction of the way along a path. See ADR 0005 - this and
// aoi/quality/store are what services/aisgen and services/aisd share, so
// synthetic and recorded traffic use the same math, not two copies of it.
//
// Deliberately not a general geospatial library: no polygon ops, no
// projections, nothing PostGIS-shaped. Anything more than the three
// functions below belongs in a PostGIS query or in Python (GeoPandas,
// shapely) per ADR 0005's boundary, not here.
package geo

import "math"

// EarthRadiusKm is the mean radius used throughout this package. Good to
// well under 1% at the distances a shipping lane covers - nobody needs a
// WGS84 ellipsoid for "is this vessel near this lane".
const EarthRadiusKm = 6371.0088

func toRad(deg float64) float64 { return deg * math.Pi / 180 }
func toDeg(rad float64) float64 { return rad * 180 / math.Pi }

// HaversineKm returns the great-circle distance between two WGS84 points
// in kilometres. Inputs and the return value are in degrees/km, not
// radians - callers should never need math.Pi in sight.
func HaversineKm(lat1, lon1, lat2, lon2 float64) float64 {
	phi1, phi2 := toRad(lat1), toRad(lat2)
	dPhi := toRad(lat2 - lat1)
	dLambda := toRad(lon2 - lon1)

	a := math.Sin(dPhi/2)*math.Sin(dPhi/2) +
		math.Cos(phi1)*math.Cos(phi2)*math.Sin(dLambda/2)*math.Sin(dLambda/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return EarthRadiusKm * c
}

// InitialBearingDeg returns the compass bearing (0-360, 0 = true north)
// of the great-circle path from (lat1,lon1) to (lat2,lon2) at its start.
// This is what a vessel's COG should read while following a lane segment
// toward that point - it is not constant along a great circle, but a
// shipping-lane segment is short enough that the difference over its
// length is not worth modelling here.
func InitialBearingDeg(lat1, lon1, lat2, lon2 float64) float64 {
	phi1, phi2 := toRad(lat1), toRad(lat2)
	dLambda := toRad(lon2 - lon1)

	y := math.Sin(dLambda) * math.Cos(phi2)
	x := math.Cos(phi1)*math.Sin(phi2) - math.Sin(phi1)*math.Cos(phi2)*math.Cos(dLambda)
	theta := math.Atan2(y, x)
	return math.Mod(toDeg(theta)+360, 360)
}

// Interpolate returns the point a fraction (0=start, 1=end) of the way
// from (lat1,lon1) to (lat2,lon2).
//
// This is LINEAR interpolation in lat/lon space, not a great-circle
// interpolation (slerp). Deliberate simplification: a shipping-lane
// segment here spans at most a few hundred km, where the two differ by
// metres - immaterial next to the AIS position noise and lane-width
// jitter the caller adds on top. Do not reuse this for anything spanning
// ocean-basin distances or crossing the antimeridian; neither is a case
// any lane in this package's caller (services/aisgen) needs.
func Interpolate(lat1, lon1, lat2, lon2, frac float64) (lat, lon float64) {
	return lat1 + (lat2-lat1)*frac, lon1 + (lon2-lon1)*frac
}
