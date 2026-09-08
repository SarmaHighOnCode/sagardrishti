"""Per-vessel baseline gap profile — docs/SCORING_MODEL.md §2.1(b).

"Suspicion is measured as deviation from THIS vessel's own normal
behaviour... without this, the factor measures transponder quality, not
behaviour."

This computes the same thing `db/schema/001_ais_positions.sql`'s
`ais_baseline_profiles` table is provisioned for ("Populated by a Python
job in Phase 1; the table exists from day one so aisd's schema and the
scoring model's schema never drift apart"). Operating on an in-memory,
already-quality-filtered record list rather than querying Postgres
directly is what makes this testable without a live database — the
eventual Phase 1 job is a thin wrapper reading rows in and writing this
function's result back out.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from .quality_filter import AisRecord

#: Mirrors services/api/app/schemas.py's own MIN_SAMPLES_FOR_BASELINE.
#: Kept equal deliberately — "enough history to trust" should mean the
#: same thing whether asked of the wire schema or the model producing it.
MIN_SAMPLES_FOR_BASELINE = 30


@dataclass(frozen=True)
class BaselineGapProfile:
    sample_count: int
    median_gap_seconds: float
    p95_gap_seconds: float
    has_sufficient_history: bool


NO_HISTORY = BaselineGapProfile(
    sample_count=0, median_gap_seconds=0.0, p95_gap_seconds=0.0, has_sufficient_history=False
)


def compute_baseline(reliable_records: list[AisRecord]) -> BaselineGapProfile:
    """`reliable_records` should already be quality-filtered (see
    quality_filter.filter_reliable) — a baseline built from unreliable
    positions would encode transponder defects as "normal behaviour"."""
    if len(reliable_records) < 2:
        return NO_HISTORY

    ordered = sorted(reliable_records, key=lambda r: r.time)
    # zip(ordered, ordered[1:]) is a sliding pairwise window — the two
    # sequences are ONE ELEMENT DIFFERENT IN LENGTH BY CONSTRUCTION, so
    # strict=True here would raise on every non-empty input. strict=True
    # is for "these two are supposed to be the same length"; this is not
    # that case.
    gaps = sorted(
        (b.time - a.time).total_seconds() for a, b in zip(ordered, ordered[1:], strict=False)
    )
    n = len(gaps)
    p95_index = min(n - 1, int(0.95 * n))

    return BaselineGapProfile(
        sample_count=n,
        median_gap_seconds=median(gaps),
        p95_gap_seconds=gaps[p95_index],
        has_sufficient_history=n >= MIN_SAMPLES_FOR_BASELINE,
    )
