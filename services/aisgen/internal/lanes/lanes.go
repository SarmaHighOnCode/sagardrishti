// Package lanes defines the shipping-lane geometry synthetic vessels
// travel along.
//
// HONEST LIMITATION, stated plainly rather than left for someone to
// assume is covered: services/aisgen/README.md requirement 1 calls for
// lane centrelines derived by KDE from RECORDED AISStream traffic ("grounded
// in real Indian traffic, not invented"). That data does not exist — aisd
// has never recorded a single row (see docs/ROADMAP.md, the missed
// 3 September milestone). The waypoints below are hand-specified from
// public knowledge of major Indian coastal shipping corridors and named
// ports, which is a reasonable placeholder but is NOT what requirement 1
// asks for. Replace Default() with a KDE-fitted version once aisd has
// weeks of recorded traffic to fit against — do not let this comment go
// stale once that happens.
package lanes

import (
	"math"

	"github.com/sagardrishti/go/geo"
)

// Waypoint is one vertex of a lane's centreline.
type Waypoint struct {
	Lat, Lon float64
}

// Lane is a named shipping corridor: an ordered polyline centreline plus
// a half-width vessels are jittered across, so no two synthetic vessels
// on the same lane sit on an identical, suspiciously straight line.
type Lane struct {
	Name    string
	AOI     string // must match an aoi.Named.Name from packages/go/aoi
	Points  []Waypoint
	WidthKm float64
}

// Default returns the hand-specified lanes for both AOIs aisd subscribes
// to. See the package doc comment for what this is a placeholder for.
func Default() []Lane {
	return []Lane{
		{
			// Kandla -> Mumbai -> Goa -> Mangalore -> Kochi -> Kanyakumari.
			// The busiest coastal corridor on the west coast: container
			// and product-tanker traffic between the major west-coast
			// ports, roughly following the continental shelf.
			Name: "west_coast_coastal",
			AOI:  "arabian_sea",
			Points: []Waypoint{
				{Lat: 22.8, Lon: 69.6}, // off Kandla
				{Lat: 20.9, Lon: 71.4}, // off Diu
				{Lat: 18.7, Lon: 72.3}, // off Mumbai/JNPT
				{Lat: 15.3, Lon: 73.2}, // off Goa
				{Lat: 12.6, Lon: 74.4}, // off Mangalore
				{Lat: 9.8, Lon: 75.8},  // off Kochi
				{Lat: 8.1, Lon: 77.3},  // off Kanyakumari
			},
			WidthKm: 15,
		},
		{
			// Mumbai toward the Gulf of Aden / Persian Gulf approach — the
			// tanker route out of our AOI's western edge. Vessels on this
			// lane are expected to exit the box before the route ends;
			// aoi.Classify already handles a point outside every box
			// ("unassigned"), so that is not a special case here.
			Name: "gulf_approach",
			AOI:  "arabian_sea",
			Points: []Waypoint{
				{Lat: 18.7, Lon: 72.3},
				{Lat: 16.0, Lon: 66.0},
				{Lat: 13.5, Lon: 60.5}, // near the AOI's western edge
			},
			WidthKm: 25,
		},
		{
			// Kanyakumari -> Chennai -> Vizag -> Sagar (Kolkata approach).
			// The east-coast mirror of west_coast_coastal.
			Name: "east_coast_coastal",
			AOI:  "bay_of_bengal",
			Points: []Waypoint{
				{Lat: 8.1, Lon: 77.6},
				{Lat: 10.8, Lon: 79.9}, // off Nagapattinam
				{Lat: 13.1, Lon: 80.6}, // off Chennai
				{Lat: 17.7, Lon: 83.6}, // off Visakhapatnam
				{Lat: 21.4, Lon: 88.3}, // off Sagar Island, Kolkata approach
			},
			WidthKm: 15,
		},
		{
			// Chennai toward the Malacca Strait approach — the east-coast
			// mirror of gulf_approach, and the other route out of the AOI.
			Name: "malacca_approach",
			AOI:  "bay_of_bengal",
			Points: []Waypoint{
				{Lat: 13.1, Lon: 80.6},
				{Lat: 10.5, Lon: 87.0},
				{Lat: 8.0, Lon: 92.8}, // near the AOI's eastern edge
			},
			WidthKm: 25,
		},
	}
}

// LengthKm is the lane's total centreline length, summed segment by
// segment. O(len(Points)); cheap enough to call once per vessel rather
// than caching, since a simulation run creates at most a few dozen
// vessels total.
func (l Lane) LengthKm() float64 {
	total := 0.0
	for i := 1; i < len(l.Points); i++ {
		a, b := l.Points[i-1], l.Points[i]
		total += geo.HaversineKm(a.Lat, a.Lon, b.Lat, b.Lon)
	}
	return total
}

// PointAt returns the position and heading at distanceKm along the
// centreline from the start (clamped to [0, LengthKm()]), plus a lateral
// offset (in km, positive = starboard side of travel) applied
// perpendicular to that heading. The offset is what gives vessels on the
// same lane distinct, non-overlapping tracks instead of stacking on one
// suspiciously exact line.
func (l Lane) PointAt(distanceKm, lateralOffsetKm float64) (lat, lon, headingDeg float64) {
	if len(l.Points) < 2 {
		if len(l.Points) == 1 {
			return l.Points[0].Lat, l.Points[0].Lon, 0
		}
		return 0, 0, 0
	}

	total := l.LengthKm()
	if distanceKm < 0 {
		distanceKm = 0
	}
	if distanceKm > total {
		distanceKm = total
	}

	// Walk segments until distanceKm falls within one of them.
	remaining := distanceKm
	for i := 1; i < len(l.Points); i++ {
		a, b := l.Points[i-1], l.Points[i]
		segKm := geo.HaversineKm(a.Lat, a.Lon, b.Lat, b.Lon)
		if remaining <= segKm || i == len(l.Points)-1 {
			frac := 0.0
			if segKm > 0 {
				frac = remaining / segKm
			}
			if frac > 1 {
				frac = 1
			}
			lat, lon = geo.Interpolate(a.Lat, a.Lon, b.Lat, b.Lon, frac)
			headingDeg = geo.InitialBearingDeg(a.Lat, a.Lon, b.Lat, b.Lon)
			return applyLateralOffset(lat, lon, headingDeg, lateralOffsetKm)
		}
		remaining -= segKm
	}

	last := l.Points[len(l.Points)-1]
	return last.Lat, last.Lon, headingDeg
}

// applyLateralOffset nudges (lat,lon) perpendicular to headingDeg by
// offsetKm. Small-angle approximation (flat-earth at the offset's own
// scale, a few km at most) — proportionate to the ~15-25km lane widths
// above, not intended for anything larger.
func applyLateralOffset(lat, lon, headingDeg, offsetKm float64) (float64, float64, float64) {
	if offsetKm == 0 {
		return lat, lon, headingDeg
	}
	perpRad := (headingDeg + 90) * (math.Pi / 180)
	dLat := (offsetKm / 111.32) * math.Cos(perpRad)
	dLon := (offsetKm / (111.32 * math.Cos(lat*math.Pi/180))) * math.Sin(perpRad)
	return lat + dLat, lon + dLon, headingDeg
}
