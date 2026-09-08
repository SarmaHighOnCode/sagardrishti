package lanes

import (
	"math"
	"testing"

	"github.com/sagardrishti/go/aoi"
)

func TestDefaultLanesStayInsideTheirDeclaredAOI(t *testing.T) {
	// A lane tagged "arabian_sea" whose points don't classify into
	// arabian_sea would tag every generated row with an AOI its own
	// positions don't actually fall in - aisd's own aoi.Classify is the
	// authority here, not a second guess at the box boundaries.
	aois := aoi.Default()
	for _, l := range Default() {
		insideCount := 0
		for _, p := range l.Points {
			if aoi.Classify(aois, p.Lat, p.Lon) == l.AOI {
				insideCount++
			}
		}
		// Not every point must classify (gulf_approach and malacca_approach
		// deliberately run off the AOI's edge, per their own comments) -
		// but the majority must, or the lane is mistagged outright.
		if insideCount < len(l.Points)/2 {
			t.Errorf("lane %q tagged AOI %q, but only %d/%d points classify into it",
				l.Name, l.AOI, insideCount, len(l.Points))
		}
	}
}

func TestLengthKmIsPositiveAndAdditive(t *testing.T) {
	l := Lane{Points: []Waypoint{{Lat: 0, Lon: 0}, {Lat: 1, Lon: 0}, {Lat: 2, Lon: 0}}}
	full := l.LengthKm()
	if full <= 0 {
		t.Fatalf("LengthKm() = %v, want > 0", full)
	}

	half := Lane{Points: []Waypoint{{Lat: 0, Lon: 0}, {Lat: 1, Lon: 0}}}.LengthKm()
	if math.Abs(full-2*half) > 0.01 {
		t.Errorf("two equal 1-degree segments should sum to ~2x one: full=%v, half=%v", full, half)
	}
}

func TestPointAtStartAndEndMatchWaypoints(t *testing.T) {
	l := Lane{Points: []Waypoint{{Lat: 10, Lon: 70}, {Lat: 20, Lon: 75}}}

	lat, lon, _ := l.PointAt(0, 0)
	if math.Abs(lat-10) > 1e-6 || math.Abs(lon-70) > 1e-6 {
		t.Errorf("PointAt(0,0) = (%v,%v), want the first waypoint (10,70)", lat, lon)
	}

	lat, lon, _ = l.PointAt(l.LengthKm(), 0)
	if math.Abs(lat-20) > 1e-6 || math.Abs(lon-75) > 1e-6 {
		t.Errorf("PointAt(length,0) = (%v,%v), want the last waypoint (20,75)", lat, lon)
	}
}

func TestPointAtClampsPastTheEnds(t *testing.T) {
	l := Lane{Points: []Waypoint{{Lat: 10, Lon: 70}, {Lat: 20, Lon: 75}}}

	lat, lon, _ := l.PointAt(-50, 0)
	wantLat, wantLon, _ := l.PointAt(0, 0)
	if lat != wantLat || lon != wantLon {
		t.Errorf("PointAt(-50,0) = (%v,%v), want it clamped to the start (%v,%v)", lat, lon, wantLat, wantLon)
	}

	lat, lon, _ = l.PointAt(l.LengthKm()+1000, 0)
	wantLat, wantLon, _ = l.PointAt(l.LengthKm(), 0)
	if lat != wantLat || lon != wantLon {
		t.Errorf("PointAt(length+1000,0) = (%v,%v), want it clamped to the end (%v,%v)", lat, lon, wantLat, wantLon)
	}
}

func TestLateralOffsetMovesThePointButNotZero(t *testing.T) {
	l := Lane{Points: []Waypoint{{Lat: 10, Lon: 70}, {Lat: 10, Lon: 80}}}
	halfway := l.LengthKm() / 2

	centreLat, centreLon, _ := l.PointAt(halfway, 0)
	offLat, offLon, _ := l.PointAt(halfway, 5)

	if centreLat == offLat && centreLon == offLon {
		t.Error("a non-zero lateral offset produced the exact same point as zero offset")
	}

	// Roughly 5km of displacement, not some wildly wrong magnitude - loose
	// bound since applyLateralOffset is a small-angle approximation.
	dLat := (offLat - centreLat) * 111.32
	dLon := (offLon - centreLon) * 111.32 * math.Cos(centreLat*math.Pi/180)
	dist := math.Hypot(dLat, dLon)
	if dist < 3 || dist > 7 {
		t.Errorf("lateral offset of 5km produced an actual displacement of %.2fkm", dist)
	}
}

func TestSingleAndEmptyPointLanesDoNotPanic(t *testing.T) {
	single := Lane{Points: []Waypoint{{Lat: 1, Lon: 2}}}
	if lat, lon, _ := single.PointAt(0, 0); lat != 1 || lon != 2 {
		t.Errorf("single-point lane PointAt = (%v,%v), want (1,2)", lat, lon)
	}

	empty := Lane{}
	if lat, lon, _ := empty.PointAt(0, 0); lat != 0 || lon != 0 {
		t.Errorf("empty lane PointAt = (%v,%v), want (0,0)", lat, lon)
	}
	if got := empty.LengthKm(); got != 0 {
		t.Errorf("empty lane LengthKm() = %v, want 0", got)
	}
}
