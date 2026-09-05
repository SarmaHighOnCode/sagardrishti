// Package aoi defines the areas of interest the recorder subscribes to and
// classifies incoming positions against.
//
// Bounding boxes are a deliberate approximation of the actual EEZ polygons:
// AISStream's subscription API only accepts rectangular boxes. Tune these
// with the team once real traffic density is visible - see
// docs/DATA_SOURCES.md section 3.1.
package aoi

// Box is a rectangular bounding box as AISStream expects it: a
// [southwest, northeast] pair of [latitude, longitude] corners.
type Box [2][2]float64

// Named is a bounding box with the AOI name aisd tags stored rows with.
type Named struct {
	Name string
	Box  Box
}

// Default returns the two AOIs the roadmap calls for from day one:
// Arabian Sea (Gulf of Kutch to Kanyakumari, out to the EEZ) and
// Bay of Bengal (Kanyakumari to the Sundarbans).
func Default() []Named {
	return []Named{
		{
			Name: "arabian_sea",
			// SW corner ~out to the EEZ off Gujarat/Kutch, NE corner near
			// Kanyakumari's northern shoulder.
			Box: Box{{6.0, 60.0}, {24.5, 76.5}},
		},
		{
			Name: "bay_of_bengal",
			// SW corner near Kanyakumari, NE corner past the Sundarbans.
			Box: Box{{6.0, 77.0}, {22.5, 93.0}},
		},
	}
}

// Classify returns the name of the first AOI whose box contains (lat, lon),
// or "" if the point falls in none of them. A point can legitimately miss
// every AOI at the seam between two boxes' float boundaries or if AISStream
// forwards a message just outside the subscribed box; callers should store
// it anyway rather than drop it.
func Classify(aois []Named, lat, lon float64) string {
	for _, a := range aois {
		sw, ne := a.Box[0], a.Box[1]
		if lat >= sw[0] && lat <= ne[0] && lon >= sw[1] && lon <= ne[1] {
			return a.Name
		}
	}
	return ""
}

// BoundingBoxes extracts the raw [][2][2]float64 shape the AISStream
// subscribe message wants, preserving AOI order.
func BoundingBoxes(aois []Named) [][2][2]float64 {
	out := make([][2][2]float64, len(aois))
	for i, a := range aois {
		out[i] = a.Box
	}
	return out
}
