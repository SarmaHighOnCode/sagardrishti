package confounders

import (
	"testing"
	"time"

	"github.com/sagardrishti/go/store"
)

func makeTrack(n int) []store.PositionRow {
	rows := make([]store.PositionRow, n)
	for i := range rows {
		rows[i] = store.PositionRow{
			Time: time.Unix(int64(i)*60, 0),
			MMSI: 900000001,
			Lat:  10 + float64(i)*0.01,
			Lon:  75,
		}
	}
	return rows
}

func TestApplyGapRemovesExactlyTheRequestedWindow(t *testing.T) {
	rows := makeTrack(10)
	got := ApplyGap(rows, 3, 4) // remove indices 3,4,5,6
	if len(got) != 6 {
		t.Fatalf("len = %d, want 6", len(got))
	}
	// The row immediately after the gap should be the original index 7.
	if got[3].Lat != rows[7].Lat {
		t.Errorf("row after gap = %v, want original index 7 (%v)", got[3].Lat, rows[7].Lat)
	}
}

func TestApplyGapClampsOutOfRangeWindow(t *testing.T) {
	rows := makeTrack(5)

	if got := ApplyGap(rows, 3, 100); len(got) != 3 {
		t.Errorf("gap running past the end: len = %d, want 3", len(got))
	}
	if got := ApplyGap(rows, -5, 2); len(got) != 3 {
		t.Errorf("negative startIdx should clamp to 0: len = %d, want 3", len(got))
	}
	if got := ApplyGap(rows, 50, 2); len(got) != 5 {
		t.Errorf("startIdx past the end should be a no-op: len = %d, want 5", len(got))
	}
}

func TestApplyGapOnEmptyOrZeroLengthIsNoop(t *testing.T) {
	if got := ApplyGap(nil, 0, 5); got != nil {
		t.Errorf("ApplyGap(nil,...) = %v, want nil", got)
	}
	rows := makeTrack(5)
	if got := ApplyGap(rows, 2, 0); len(got) != 5 {
		t.Errorf("zero-length gap should be a no-op: len = %d, want 5", len(got))
	}
}

func TestApplyPositionJumpChangesOnlyTheTargetRow(t *testing.T) {
	rows := makeTrack(5)
	got := ApplyPositionJump(rows, 2, 0, 0)

	if got[2].Lat != 0 || got[2].Lon != 0 {
		t.Errorf("jumped row = (%v,%v), want (0,0)", got[2].Lat, got[2].Lon)
	}
	for i, r := range got {
		if i == 2 {
			continue
		}
		if r.Lat != rows[i].Lat || r.Lon != rows[i].Lon {
			t.Errorf("row %d changed, want it untouched", i)
		}
		if r.Time != rows[i].Time || r.MMSI != rows[i].MMSI {
			t.Errorf("row %d's identity/timestamp changed, want them untouched by a position jump", i)
		}
	}
}

func TestApplyPositionJumpOutOfRangeIsNoop(t *testing.T) {
	rows := makeTrack(3)
	if got := ApplyPositionJump(rows, 99, 1, 1); len(got) != 3 || got[0].Lat != rows[0].Lat {
		t.Error("out-of-range idx should return rows unchanged")
	}
}

func TestApplyPositionJumpDoesNotMutateTheInput(t *testing.T) {
	rows := makeTrack(3)
	originalLat := rows[1].Lat
	_ = ApplyPositionJump(rows, 1, 999, 999)
	if rows[1].Lat != originalLat {
		t.Error("ApplyPositionJump mutated its input slice in place")
	}
}

func TestDuplicateMMSIOverwritesMMSIAndLeavesRestUnchanged(t *testing.T) {
	rows := makeTrack(4)
	got := DuplicateMMSI(rows, 900000099)

	for i, r := range got {
		if r.MMSI != 900000099 {
			t.Errorf("row %d MMSI = %d, want 900000099", i, r.MMSI)
		}
		if r.Lat != rows[i].Lat || r.Time != rows[i].Time {
			t.Errorf("row %d position/time changed by a pure MMSI duplication", i)
		}
	}
	// Original track must be untouched — the caller appends both.
	if rows[0].MMSI != 900000001 {
		t.Error("DuplicateMMSI mutated the original track's MMSI")
	}
}
