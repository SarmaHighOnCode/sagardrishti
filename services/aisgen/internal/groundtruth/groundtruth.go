// Package groundtruth records what actually happened in a simulation run:
// which vessel discharged, when, where, and which vessels were merely
// nearby without discharging. This is the ONLY reason a synthetic
// generator is a deliverable rather than a fallback (see
// services/aisgen/README.md requirement 5) — without it, M6 attribution
// accuracy is unmeasurable, since real discharges have no known source
// to score against.
package groundtruth

import (
	"encoding/json"
	"os"
	"time"
)

// Label distinguishes the vessel that actually discharged from a vessel
// that is merely near the slick in space and time — the "innocent but
// suspicious" case services/aisgen/README.md requirement 6 explicitly
// calls for, because a generator producing only clean-cut cases would
// let the attribution model look better than it is.
type Label string

const (
	Discharger        Label = "discharger"
	InnocentNearSlick Label = "innocent_near_slick"
	// Background is ordinary generated traffic — neither the discharger
	// nor flagged as suspiciously nearby. Recorded in ground truth only
	// when it also carries a Confounder tag, so an evaluator can check
	// whether that specific data-quality effect degraded attribution
	// accuracy for a vessel that was never a candidate to begin with.
	Background Label = "background"
)

// Event is one labelled ground-truth record. Every field a future
// evaluation script (M6) needs to score an attribution run's output
// against reality, without re-deriving any of it from the AIS rows
// themselves.
type Event struct {
	Label           Label     `json:"label"`
	MMSI            int64     `json:"mmsi"`
	VesselName      string    `json:"vessel_name"`
	AOI             string    `json:"aoi"`
	TimeUTC         time.Time `json:"time_utc"`
	Lat             float64   `json:"lat"`
	Lon             float64   `json:"lon"`
	RateM3PerHour   float64   `json:"rate_m3_per_hour,omitempty"`
	DurationMinutes float64   `json:"duration_minutes,omitempty"`
	// Confounder, when non-empty, names which internal/confounders effect
	// was applied to this vessel's track (e.g. "ais_gap", "mmsi_duplicate",
	// "position_jump") — so an evaluator can check whether the confounder
	// specifically degraded attribution accuracy for that vessel.
	Confounder string `json:"confounder,omitempty"`
}

// Run is everything one aisgen invocation produced, in the shape the
// M6 evaluator (not yet built) will consume.
type Run struct {
	GeneratedAtUTC time.Time `json:"generated_at_utc"`
	Seed           int64     `json:"seed"`
	Events         []Event   `json:"events"`
}

// WriteJSON writes r as indented JSON to path, creating or truncating it.
// Indented deliberately: this file is meant to be read by a person
// debugging an evaluation run, not just parsed by one.
func WriteJSON(path string, r Run) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	return enc.Encode(r)
}
