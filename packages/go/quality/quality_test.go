package quality

import "testing"

func TestCheck(t *testing.T) {
	cases := []struct {
		name       string
		mmsi       int64
		lat, lon   float64
		sog        float64
		sogValid   bool
		wantStatus string
		wantReason string
	}{
		{"clean", 123456789, 19.0, 72.8, 12.4, true, OK, ""},
		{"zero mmsi", 0, 19.0, 72.8, 12.4, true, Unreliable, "mmsi_zero"},
		{"negative mmsi", -5, 19.0, 72.8, 12.4, true, Unreliable, "mmsi_zero"},
		{"null island", 123456789, 0, 0, 0, true, Unreliable, "null_island"},
		{"lat out of range", 123456789, 91, 72.8, 5, true, Unreliable, "out_of_range"},
		{"lon out of range", 123456789, 19, 181, 5, true, Unreliable, "out_of_range"},
		{"implausible speed", 123456789, 19, 72.8, 80, true, Unreliable, "implausible_speed"},
		{"not available sentinel is caller's job to mark invalid", 123456789, 19, 72.8, 102.3, false, OK, ""},
		{"sog invalid is ignored even if numerically absurd", 123456789, 19, 72.8, 999, false, OK, ""},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			status, reason := Check(c.mmsi, c.lat, c.lon, c.sog, c.sogValid)
			if status != c.wantStatus || reason != c.wantReason {
				t.Errorf("Check(...) = (%q, %q), want (%q, %q)", status, reason, c.wantStatus, c.wantReason)
			}
		})
	}
}

func TestCheckStatic(t *testing.T) {
	if status, _ := CheckStatic(123456789); status != OK {
		t.Errorf("expected OK, got %q", status)
	}
	if status, reason := CheckStatic(0); status != Unreliable || reason != "mmsi_zero" {
		t.Errorf("expected unreliable/mmsi_zero, got %q/%q", status, reason)
	}
}
