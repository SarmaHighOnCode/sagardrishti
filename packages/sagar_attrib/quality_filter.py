"""Data-quality pre-filter for AIS records feeding the attribution model.

docs/SCORING_MODEL.md §2.1(a): records showing MMSI 0, position stuck at
(0,0), kinematically impossible implied speed, or garbled static data are
labelled unreliable and REMOVED from the evidence set — never converted
into negative evidence. A vessel must never become a suspect *because*
its transponder is broken; that would invert the entire logic of the
system.

This is a Python port of the same physical facts `packages/go/quality`
checks on the recording side (ADR 0005's boundary is the database, not
shared code — the two languages agree on what "bad data" means without
sharing a package).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sagar_core.geo import LonLat, implied_speed_knots
from sagar_core.types import DataQualitySummary

#: Mirrors packages/go/quality.MaxPlausibleKnots — same physical fact
#: (no ship on Earth outruns this), expressed on both sides of the
#: language boundary. Keep them equal if either changes.
MAX_PLAUSIBLE_KNOTS = 60.0


@dataclass(frozen=True)
class AisRecord:
    time: datetime
    lat: float
    lon: float
    mmsi: int
    sog_knots: float | None = None


def filter_reliable(records: list[AisRecord]) -> tuple[list[AisRecord], DataQualitySummary]:
    """Return (reliable records, a summary of what was excluded and why).

    Records are sorted by time first — the teleport check is inherently
    about consecutive positions, and a caller handing this an unsorted
    track should not get an answer that silently depends on input order.

    The implied-speed check compares each candidate against the last
    RELIABLE record seen so far, not the immediately preceding raw
    record. Comparing against a null-island glitch would make the very
    next good position look like a 6000-knot teleport and exclude it too
    — one bad ping would then wrongly cascade into excluding good data
    that follows it.
    """
    sorted_records = sorted(records, key=lambda r: r.time)
    reliable: list[AisRecord] = []
    reasons: dict[str, int] = {}
    last_reliable: AisRecord | None = None

    for r in sorted_records:
        reason = _independent_issue(r)
        if reason is None and last_reliable is not None:
            elapsed = (r.time - last_reliable.time).total_seconds()
            if elapsed > 0:
                implied = implied_speed_knots(
                    LonLat(last_reliable.lon, last_reliable.lat), LonLat(r.lon, r.lat), elapsed
                )
                if implied > MAX_PLAUSIBLE_KNOTS:
                    reason = "impossible_speed"
            # elapsed <= 0 (duplicate/out-of-order timestamp after sorting,
            # i.e. two records at the identical instant) is not a speed
            # question at all — nothing to divide by, and not itself
            # evidence of bad data, so it is silently allowed through.

        if reason is not None:
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            reliable.append(r)
            last_reliable = r

    summary = DataQualitySummary(
        records_used=len(reliable),
        records_excluded=len(sorted_records) - len(reliable),
        exclusion_reasons=reasons,
    )
    return reliable, summary


def _independent_issue(r: AisRecord) -> str | None:
    """Checks that need only this one record, not its neighbours."""
    if r.mmsi <= 0:
        return "mmsi_zero"
    if r.lat == 0 and r.lon == 0:
        return "null_island"
    if not (-90.0 <= r.lat <= 90.0) or not (-180.0 <= r.lon <= 180.0):
        return "out_of_range"
    return None
