// Package confounders introduces the deliberately messy cases
// services/aisgen/README.md requirement 6 calls for: AIS gaps, MMSI
// duplication, and position jumps. Each operates on an already-generated
// position track for one vessel, so the "clean" simulation logic in
// internal/simulate stays simple and these effects are independently
// testable.
//
// "A generator producing clean, well-behaved traffic would let the
// attribution model look far better than it is" — README's own words.
// These functions exist to make that claim untrue of this generator.
package confounders

import "github.com/sagardrishti/go/store"

// ApplyGap removes a run of consecutive rows starting at startIdx,
// simulating a receiver dropout or a vessel legitimately out of coverage.
// Out-of-range indices are clamped rather than panicking, since a caller
// picking a random gap window against a track of unknown-until-runtime
// length is the expected use.
func ApplyGap(rows []store.PositionRow, startIdx, length int) []store.PositionRow {
	if len(rows) == 0 || length <= 0 {
		return rows
	}
	if startIdx < 0 {
		startIdx = 0
	}
	if startIdx >= len(rows) {
		return rows
	}
	end := startIdx + length
	if end > len(rows) {
		end = len(rows)
	}
	out := make([]store.PositionRow, 0, len(rows)-(end-startIdx))
	out = append(out, rows[:startIdx]...)
	out = append(out, rows[end:]...)
	return out
}

// ApplyPositionJump replaces the position of the row at idx with an
// implausible location, simulating a GPS glitch or spoofed report. The
// timestamp, MMSI and every other field are left untouched — a jump
// looks exactly like a real report except for where it claims to be,
// which is what makes it a plausibility problem rather than something a
// schema check would catch.
func ApplyPositionJump(rows []store.PositionRow, idx int, jumpLat, jumpLon float64) []store.PositionRow {
	if idx < 0 || idx >= len(rows) {
		return rows
	}
	out := make([]store.PositionRow, len(rows))
	copy(out, rows)
	out[idx].Lat = jumpLat
	out[idx].Lon = jumpLon
	return out
}

// DuplicateMMSI returns a copy of rows with every row's MMSI overwritten
// to newMMSI. The caller is expected to append the result alongside the
// original track (under its real MMSI) in the same batch, so the same
// identity is broadcasting from two different tracks at once — MMSI
// spoofing/duplication, not a relabelling of one vessel.
func DuplicateMMSI(rows []store.PositionRow, newMMSI int64) []store.PositionRow {
	out := make([]store.PositionRow, len(rows))
	for i, r := range rows {
		r.MMSI = newMMSI
		out[i] = r
	}
	return out
}
