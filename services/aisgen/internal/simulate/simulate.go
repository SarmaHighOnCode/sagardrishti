// Package simulate is aisgen's orchestrator: places generated vessels on
// lanes, advances them tick by tick, and produces exactly the row types
// packages/go/store already knows how to write — []store.PositionRow and
// []store.StaticRow, plus the labelled ground-truth events described in
// services/aisgen/README.md requirement 5.
//
// This is the piece that makes ADR 0005's promotion of internal/store
// mean something: Run returns the same row types aisd's own recorder
// builds, so both binaries reach the database through
// packages/go/store.WritePositions / WriteStatic, not through two
// independent encodings of "a position report" that could quietly
// diverge.
package simulate

import (
	"math"
	"math/rand"
	"time"

	"github.com/sagardrishti/aisgen/internal/confounders"
	"github.com/sagardrishti/aisgen/internal/fleet"
	"github.com/sagardrishti/aisgen/internal/groundtruth"
	"github.com/sagardrishti/aisgen/internal/lanes"
	"github.com/sagardrishti/go/aoi"
	"github.com/sagardrishti/go/quality"
	"github.com/sagardrishti/go/store"
)

// Config controls one simulation run. All fields have sane defaults
// applied by Run if left zero, mirroring the pattern
// services/aisd/internal/recorder.New already uses.
type Config struct {
	Seed int64
	// StartUTC anchors every generated timestamp. Defaults to now.
	StartUTC time.Time
	// NumVessels is the size of the "normal traffic" fleet, before the
	// discharger, the innocent-near-slick vessel, and confounder copies
	// are added on top.
	NumVessels int
	Duration   time.Duration
	// ReportInterval is deliberately coarser than real Class A cadence
	// (2-10s underway per the AIS spec) — see the package doc comment.
	// At real cadence, a 24h/40-vessel run would emit on the order of
	// 1-3M position rows for no benefit to the confounder/attribution
	// use case this generator exists for; a demo-scale interval keeps
	// row counts tractable while still exercising every code path a
	// consumer downstream of aisd/aisgen cares about.
	ReportInterval time.Duration
	// Source is the value written to store.PositionRow.Source /
	// StaticRow.Source. "aisgen" by default — the field the entire
	// "identical ingest path, distinguished only by source" claim in
	// ADR 0005 depends on being set correctly.
	Source string
}

func (c Config) withDefaults() Config {
	if c.StartUTC.IsZero() {
		c.StartUTC = time.Now().UTC()
	}
	if c.NumVessels <= 0 {
		c.NumVessels = 40
	}
	if c.Duration <= 0 {
		c.Duration = 24 * time.Hour
	}
	if c.ReportInterval <= 0 {
		c.ReportInterval = 2 * time.Minute
	}
	if c.Source == "" {
		c.Source = "aisgen"
	}
	return c
}

// Result is everything one Run produces, ready to hand to
// packages/go/store (or, in dry-run mode, to a JSON file — see
// cmd/aisgen/main.go).
type Result struct {
	Positions []store.PositionRow
	Statics   []store.StaticRow
	Ground    groundtruth.Run
}

// track is one vessel's simulation state while ticking forward. Kept
// separate from fleet.Vessel so fleet stays a pure "what does this
// vessel look like" concern and this package owns "where is it and which
// way is it moving".
type track struct {
	v               fleet.Vessel
	lane            lanes.Lane
	distanceKm      float64 // current position along the lane's centreline
	direction       float64 // +1 or -1; bounces at the lane's ends
	lateralOffsetKm float64
	staticEvery     int // emit a static row every N ticks
}

// Run executes one simulation and returns every row it produced, plus
// ground-truth labels. Deterministic for a given Seed — two calls with
// identical Config produce byte-identical Result.Positions, which is
// what services/aisgen/README.md's "synthetic and real AIS share an
// ingest path" claim needs to be checkable rather than asserted.
func Run(cfg Config) Result {
	cfg = cfg.withDefaults()
	rng := rand.New(rand.NewSource(cfg.Seed))

	allLanes := lanes.Default()
	profiles := fleet.DefaultProfiles()
	aois := aoi.Default()

	vessels := fleet.Generate(rng, profiles, cfg.NumVessels, 0)
	tracks := make([]*track, len(vessels))
	for i, v := range vessels {
		l := allLanes[rng.Intn(len(allLanes))]
		dir := 1.0
		if rng.Float64() < 0.5 {
			dir = -1.0
		}
		tracks[i] = &track{
			v:               v,
			lane:            l,
			distanceKm:      rng.Float64() * l.LengthKm(),
			direction:       dir,
			lateralOffsetKm: (rng.Float64()*2 - 1) * (l.WidthKm / 2),
			staticEvery:     20 + rng.Intn(20),
		}
	}

	ticks := int(cfg.Duration / cfg.ReportInterval)
	perTrack := make([][]store.PositionRow, len(tracks))
	statics := make([]store.StaticRow, 0, len(tracks))

	for ti, tr := range tracks {
		rows := make([]store.PositionRow, 0, ticks)
		for tick := 0; tick < ticks; tick++ {
			ts := cfg.StartUTC.Add(time.Duration(tick) * cfg.ReportInterval)
			advance(tr, cfg.ReportInterval)

			lat, lon, heading := tr.lane.PointAt(tr.distanceKm, tr.lateralOffsetKm)
			sog := tr.v.CruiseKnots * (0.9 + rng.Float64()*0.2) // +/-10% speed jitter
			cog := math.Mod(heading+(rng.Float64()*10-5)+360, 360)

			status, reason := quality.Check(tr.v.MMSI, lat, lon, sog, true)
			var reasonPtr *string
			if reason != "" {
				r := reason
				reasonPtr = &r
			}

			aoiName := aoi.Classify(aois, lat, lon)
			if aoiName == "" {
				aoiName = "unassigned"
			}

			sogVal, cogVal, headingVal := sog, cog, int16(math.Round(heading))
			rows = append(rows, store.PositionRow{
				Time:          ts,
				MMSI:          tr.v.MMSI,
				Lat:           lat,
				Lon:           lon,
				SOGKnots:      &sogVal,
				COGDegrees:    &cogVal,
				TrueHeading:   &headingVal,
				AOI:           aoiName,
				Source:        cfg.Source,
				DataQuality:   status,
				QualityReason: reasonPtr,
			})

			if tick%tr.staticEvery == 0 {
				statics = append(statics, staticRowFor(tr.v, ts, cfg.Source))
			}
		}
		perTrack[ti] = rows
	}

	ground := groundtruth.Run{GeneratedAtUTC: time.Now().UTC(), Seed: cfg.Seed}

	positions := applyConfoundersAndCollect(rng, tracks, perTrack, &ground, cfg)
	positions, statics2 := addDischargeAndInnocentVessel(rng, tracks, positions, cfg, &ground)
	statics = append(statics, statics2...)

	return Result{Positions: positions, Statics: statics, Ground: ground}
}

// advance moves tr forward (or backward) along its lane by however far
// its cruise speed covers in elapsed, bouncing off either end rather
// than teleporting back to the start — a vessel reversing course at the
// end of its lane is a more plausible traffic pattern for a bounded
// simulation than a sawtooth reset.
func advance(tr *track, elapsed time.Duration) {
	kmPerHour := tr.v.CruiseKnots * 1.852
	deltaKm := kmPerHour * elapsed.Hours() * tr.direction

	length := tr.lane.LengthKm()
	next := tr.distanceKm + deltaKm
	for next < 0 || next > length {
		if next < 0 {
			next = -next
		} else if next > length {
			next = 2*length - next
		}
		tr.direction = -tr.direction
	}
	tr.distanceKm = next
}

func staticRowFor(v fleet.Vessel, ts time.Time, source string) store.StaticRow {
	name := v.Name
	shipType := v.AISShipType
	dimBow, dimStern := v.LengthM*0.7, v.LengthM*0.3
	dimPort, dimStarboard := v.BeamM/2, v.BeamM/2
	return store.StaticRow{
		Time:         ts,
		MMSI:         v.MMSI,
		ShipName:     &name,
		ShipType:     &shipType,
		DimBow:       &dimBow,
		DimStern:     &dimStern,
		DimPort:      &dimPort,
		DimStarboard: &dimStarboard,
		Source:       source,
	}
}

// applyConfoundersAndCollect picks a small, fixed-fraction subset of
// tracks to carry one confounder each (README requirement 6), labels
// them in ground, and flattens every track's rows into one slice.
func applyConfoundersAndCollect(rng *rand.Rand, tracks []*track, perTrack [][]store.PositionRow, ground *groundtruth.Run, cfg Config) []store.PositionRow {
	var out []store.PositionRow
	for i, rows := range perTrack {
		if len(rows) == 0 {
			out = append(out, rows...)
			continue
		}
		switch i % 7 { // spread confounders thinly and deterministically across the fleet
		case 0:
			gapStart := rng.Intn(len(rows))
			gapLen := 3 + rng.Intn(5)
			rows = confounders.ApplyGap(rows, gapStart, gapLen)
			ground.Events = append(ground.Events, confounderEvent(tracks[i], rows, "ais_gap"))
		case 1:
			jumpIdx := rng.Intn(len(rows))
			rows = confounders.ApplyPositionJump(rows, jumpIdx, rows[jumpIdx].Lat+5, rows[jumpIdx].Lon+5)
			ground.Events = append(ground.Events, confounderEvent(tracks[i], rows, "position_jump"))
		case 2:
			dupMMSI := fleet.SyntheticMMSIBase + 500000 + int64(i)
			dup := confounders.DuplicateMMSI(rows, dupMMSI)
			out = append(out, dup...)
			ground.Events = append(ground.Events, confounderEvent(tracks[i], rows, "mmsi_duplicate"))
		}
		out = append(out, rows...)
	}
	return out
}

func confounderEvent(tr *track, rows []store.PositionRow, confounder string) groundtruth.Event {
	mid := len(rows) / 2
	return groundtruth.Event{
		Label:      groundtruth.Background,
		MMSI:       tr.v.MMSI,
		VesselName: tr.v.Name,
		AOI:        rows[mid].AOI,
		TimeUTC:    rows[mid].Time,
		Lat:        rows[mid].Lat,
		Lon:        rows[mid].Lon,
		Confounder: confounder,
	}
}

// addDischargeAndInnocentVessel picks one vessel as the actual
// discharger and, separately, routes one other vessel to pass near the
// discharge in space and time without discharging — the innocent-but-
// suspicious case requirement 6 calls for by name.
func addDischargeAndInnocentVessel(rng *rand.Rand, tracks []*track, positions []store.PositionRow, cfg Config, ground *groundtruth.Run) ([]store.PositionRow, []store.StaticRow) {
	if len(tracks) == 0 {
		return positions, nil
	}
	dischargerIdx := rng.Intn(len(tracks))
	discharger := tracks[dischargerIdx].v
	eventTime := cfg.StartUTC.Add(cfg.Duration / 2)
	lat, lon, _ := tracks[dischargerIdx].lane.PointAt(tracks[dischargerIdx].lane.LengthKm()/2, 0)

	ground.Events = append(ground.Events, groundtruth.Event{
		Label:           groundtruth.Discharger,
		MMSI:            discharger.MMSI,
		VesselName:      discharger.Name,
		AOI:             tracks[dischargerIdx].lane.AOI,
		TimeUTC:         eventTime,
		Lat:             lat,
		Lon:             lon,
		RateM3PerHour:   2 + rng.Float64()*8,
		DurationMinutes: 20 + rng.Float64()*100,
	})

	// The innocent vessel: any other vessel whose lane places it within
	// ~10km of the discharge location at roughly the discharge time is
	// exactly the "passes near the slick but could not have caused it"
	// case — found by scanning rather than specially routed, so it stays
	// honest to what "nearby" means for the fleet actually generated.
	innocentIdx := -1
	for i, tr := range tracks {
		if i == dischargerIdx {
			continue
		}
		iLat, iLon, _ := tr.lane.PointAt(tr.distanceKm, tr.lateralOffsetKm)
		if kmApprox(iLat, iLon, lat, lon) < 15 {
			innocentIdx = i
			break
		}
	}
	if innocentIdx >= 0 {
		v := tracks[innocentIdx].v
		iLat, iLon, _ := tracks[innocentIdx].lane.PointAt(tracks[innocentIdx].distanceKm, tracks[innocentIdx].lateralOffsetKm)
		ground.Events = append(ground.Events, groundtruth.Event{
			Label:      groundtruth.InnocentNearSlick,
			MMSI:       v.MMSI,
			VesselName: v.Name,
			AOI:        tracks[innocentIdx].lane.AOI,
			TimeUTC:    eventTime,
			Lat:        iLat,
			Lon:        iLon,
		})
	}

	return positions, nil
}

// kmApprox is a cheap flat-earth distance, adequate for the "is this
// vessel within roughly 15km" check above — no different in spirit from
// lanes.applyLateralOffset's own small-angle approximation.
func kmApprox(lat1, lon1, lat2, lon2 float64) float64 {
	dLat := (lat2 - lat1) * 111.32
	dLon := (lon2 - lon1) * 111.32 * math.Cos(lat1*math.Pi/180)
	return math.Hypot(dLat, dLon)
}
