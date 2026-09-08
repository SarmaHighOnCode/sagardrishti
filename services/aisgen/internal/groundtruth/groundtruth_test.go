package groundtruth

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestWriteJSONRoundTrips(t *testing.T) {
	run := Run{
		GeneratedAtUTC: time.Date(2026, 5, 25, 6, 0, 0, 0, time.UTC),
		Seed:           7,
		Events: []Event{
			{Label: Discharger, MMSI: 900000001, VesselName: "SYNTHETIC tanker 1",
				AOI: "arabian_sea", TimeUTC: time.Date(2026, 5, 25, 6, 40, 0, 0, time.UTC),
				Lat: 18.7, Lon: 72.3, RateM3PerHour: 4.2, DurationMinutes: 55},
			{Label: InnocentNearSlick, MMSI: 900000002, VesselName: "SYNTHETIC container 2",
				AOI: "arabian_sea", TimeUTC: time.Date(2026, 5, 25, 6, 40, 0, 0, time.UTC),
				Lat: 18.71, Lon: 72.31},
		},
	}

	path := filepath.Join(t.TempDir(), "ground_truth.json")
	if err := WriteJSON(path, run); err != nil {
		t.Fatalf("WriteJSON: %v", err)
	}

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}

	var got Run
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatalf("Unmarshal wrote-then-read JSON: %v", err)
	}

	if got.Seed != run.Seed {
		t.Errorf("Seed = %v, want %v", got.Seed, run.Seed)
	}
	if len(got.Events) != 2 {
		t.Fatalf("len(Events) = %d, want 2", len(got.Events))
	}
	if got.Events[0].Label != Discharger {
		t.Errorf("Events[0].Label = %v, want %v", got.Events[0].Label, Discharger)
	}
	if got.Events[1].Label != InnocentNearSlick {
		t.Errorf("Events[1].Label = %v, want %v", got.Events[1].Label, InnocentNearSlick)
	}
	if got.Events[0].RateM3PerHour != 4.2 {
		t.Errorf("Events[0].RateM3PerHour = %v, want 4.2", got.Events[0].RateM3PerHour)
	}
}

func TestWriteJSONIsHumanReadable(t *testing.T) {
	path := filepath.Join(t.TempDir(), "ground_truth.json")
	if err := WriteJSON(path, Run{Seed: 1}); err != nil {
		t.Fatalf("WriteJSON: %v", err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile: %v", err)
	}
	if !containsNewlineIndent(data) {
		t.Error("WriteJSON output has no indentation — it should be readable without re-formatting")
	}
}

func containsNewlineIndent(data []byte) bool {
	for i := 0; i < len(data)-3; i++ {
		if data[i] == '\n' && data[i+1] == ' ' && data[i+2] == ' ' {
			return true
		}
	}
	return false
}

func TestWriteJSONReturnsErrorForAnUnwritablePath(t *testing.T) {
	err := WriteJSON(filepath.Join(t.TempDir(), "no-such-dir", "ground_truth.json"), Run{})
	if err == nil {
		t.Error("WriteJSON to a nonexistent directory should return an error, not silently succeed")
	}
}
