package aoi

import "testing"

func TestClassify(t *testing.T) {
	aois := Default()

	cases := []struct {
		name     string
		lat, lon float64
		want     string
	}{
		{"Mumbai offshore", 19.0, 70.0, "arabian_sea"},
		{"Kochi", 9.9, 76.2, "arabian_sea"},
		{"Chennai offshore", 13.0, 81.0, "bay_of_bengal"},
		{"Sundarbans", 21.6, 88.9, "bay_of_bengal"},
		{"Antarctica", -70.0, 70.0, ""},
		{"Pacific", 10.0, 150.0, ""},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := Classify(aois, c.lat, c.lon)
			if got != c.want {
				t.Errorf("Classify(%v, %v) = %q, want %q", c.lat, c.lon, got, c.want)
			}
		})
	}
}

func TestBoundingBoxesPreservesOrder(t *testing.T) {
	aois := Default()
	boxes := BoundingBoxes(aois)
	if len(boxes) != len(aois) {
		t.Fatalf("len(boxes) = %d, want %d", len(boxes), len(aois))
	}
	for i, a := range aois {
		if boxes[i] != a.Box {
			t.Errorf("boxes[%d] = %v, want %v", i, boxes[i], a.Box)
		}
	}
}
