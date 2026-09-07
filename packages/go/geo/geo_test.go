package geo

import (
	"math"
	"testing"
)

func almostEqual(a, b, tol float64) bool { return math.Abs(a-b) <= tol }

func TestHaversineKm(t *testing.T) {
	// One degree of latitude is ~111.19 km everywhere - a good sanity
	// anchor that does not depend on longitude scaling by latitude.
	got := HaversineKm(0, 0, 1, 0)
	if !almostEqual(got, 111.19, 0.1) {
		t.Errorf("HaversineKm(0,0,1,0) = %v, want ~111.19", got)
	}

	if got := HaversineKm(12.9, 77.6, 12.9, 77.6); got != 0 {
		t.Errorf("HaversineKm of a point with itself = %v, want 0", got)
	}
}

func TestInitialBearingDeg(t *testing.T) {
	cases := []struct {
		name                   string
		lat1, lon1, lat2, lon2 float64
		want                   float64
	}{
		{"due north", 0, 0, 1, 0, 0},
		{"due east", 0, 0, 0, 1, 90},
		{"due south", 1, 0, 0, 0, 180},
		{"due west", 0, 1, 0, 0, 270},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := InitialBearingDeg(c.lat1, c.lon1, c.lat2, c.lon2)
			if !almostEqual(got, c.want, 0.5) {
				t.Errorf("InitialBearingDeg(%v,%v -> %v,%v) = %v, want ~%v",
					c.lat1, c.lon1, c.lat2, c.lon2, got, c.want)
			}
		})
	}
}

func TestInterpolate(t *testing.T) {
	lat, lon := Interpolate(10, 70, 20, 80, 0.5)
	if !almostEqual(lat, 15, 1e-9) || !almostEqual(lon, 75, 1e-9) {
		t.Errorf("Interpolate midpoint = (%v,%v), want (15,75)", lat, lon)
	}

	lat, lon = Interpolate(10, 70, 20, 80, 0)
	if lat != 10 || lon != 70 {
		t.Errorf("Interpolate at frac=0 = (%v,%v), want the start point unchanged", lat, lon)
	}

	lat, lon = Interpolate(10, 70, 20, 80, 1)
	if lat != 20 || lon != 80 {
		t.Errorf("Interpolate at frac=1 = (%v,%v), want the end point unchanged", lat, lon)
	}
}
