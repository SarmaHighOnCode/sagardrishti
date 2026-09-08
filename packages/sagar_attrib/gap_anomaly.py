"""f4 — AIS gap anomaly at inferred release. docs/SCORING_MODEL.md §2.1/f4.

The most dangerous factor in the model — the one most likely to harm an
innocent operator if built naively — so it gets its own module and its
own test file rather than living inline in factors.py with everything
else.

"Not the presence of a gap. How far this gap deviates from THIS vessel's
own baseline gap behaviour, discounted by expected AIS coverage at that
location." Both corrections are implemented here: baseline deviation
(§2.1b, via baseline.BaselineGapProfile) and the coverage proxy (§2.1c).
The third correction — the data-quality pre-filter — happens upstream,
in quality_filter.py, before a record ever reaches this module: an
unreliable record is never in the history compute_baseline() saw.
"""

from __future__ import annotations

from sagar_core.types import FactorConfidence, ScoringFactor

from .baseline import MIN_SAMPLES_FOR_BASELINE, BaselineGapProfile

#: docs/SCORING_MODEL.md §2.1(c): "distance-to-coast against a
#: terrestrial-range threshold (~40-75 nm)". Midpoint chosen as a single
#: number — a radio-propagation model would be more precise and is
#: explicitly not worth building (same section).
COVERAGE_THRESHOLD_NM = 57.5

#: Width of the region the coverage ramp softens across, centred on the
#: threshold above. A hard step would flip a vessel from "fully
#: suspicious" to "fully excused" one nautical mile either side of an
#: arbitrary line, which is a worse model of a real, fuzzy propagation
#: boundary than a short ramp is.
_RAMP_WIDTH_NM = 20.0

#: Floor coverage confidence far offshore. Not zero: even well beyond
#: reliable terrestrial range, a vessel that reports fairly consistently
#: there still gives a gap SOME weight — coverage is expected to be poor,
#: not certainly absent.
_OFFSHORE_FLOOR = 0.15

W4 = 1.3

#: docs/SCORING_MODEL.md f4: "saturating at roughly 60 minutes of
#: anomalous gap".
SATURATION_MINUTES = 60.0

#: Fallback baseline used only when a vessel has no sufficient history —
#: see the note below on why this exists and why it is conservative
#: rather than silently borrowed from the fleet average.
_FALLBACK_P95_SECONDS = 3600.0


def coverage_confidence(distance_to_coast_nm: float) -> float:
    """How much a gap AT this location should count as evidence, from 1.0
    (near shore, a gap is meaningful) down to a floor far offshore (a gap
    is expected regardless of intent)."""
    if distance_to_coast_nm <= 0:
        return 1.0

    lo = COVERAGE_THRESHOLD_NM - _RAMP_WIDTH_NM / 2
    hi = COVERAGE_THRESHOLD_NM + _RAMP_WIDTH_NM / 2

    if distance_to_coast_nm <= lo:
        return 1.0
    if distance_to_coast_nm >= hi:
        return _OFFSHORE_FLOOR

    frac = (distance_to_coast_nm - lo) / (hi - lo)
    return 1.0 - (1.0 - _OFFSHORE_FLOOR) * frac


def score_gap_anomaly(
    *,
    gap_minutes_at_release: float,
    baseline: BaselineGapProfile,
    distance_to_coast_nm_at_release: float,
) -> ScoringFactor:
    """`gap_minutes_at_release` is the length of whatever AIS gap, if any,
    overlaps the inferred release window — 0 if the vessel reported
    normally through it. Always returns a factor (never None): unlike f8
    (vessel type, where an unknown value must not be guessed at all),
    docs/SCORING_MODEL.md §5 says a missing baseline should fall back to
    a conservative prior and be marked low-confidence in the UI, not be
    dropped outright — dropping f4 for every newly-seen vessel would
    blind the model to exactly the vessels it most needs to reason about
    carefully.
    """
    if baseline.has_sufficient_history:
        reference_p95_seconds = baseline.p95_gap_seconds
        confidence = FactorConfidence.HIGH
        note = (
            f"{gap_minutes_at_release:.0f} min gap vs this vessel's own baseline "
            f"(median {baseline.median_gap_seconds / 60:.0f} min, "
            f"p95 {baseline.p95_gap_seconds / 60:.0f} min over "
            f"{baseline.sample_count} samples), "
            f"{distance_to_coast_nm_at_release:.0f}nm from shore"
        )
    else:
        # docs/SCORING_MODEL.md §5: "A vessel first seen near the spill
        # has no baseline to compare against... never substitute the
        # fleet average silently — an unknown vessel is unknown, not
        # average." The fallback below is a fixed, documented constant,
        # not a computed fleet statistic, specifically so it cannot be
        # mistaken for "we know how this vessel normally behaves".
        reference_p95_seconds = _FALLBACK_P95_SECONDS
        confidence = FactorConfidence.LOW
        note = (
            f"insufficient AIS history ({baseline.sample_count} samples, need "
            f"{MIN_SAMPLES_FOR_BASELINE}) — scored against a conservative fixed "
            "fallback, not this vessel's own behaviour. Treat with caution."
        )

    gap_seconds = gap_minutes_at_release * 60.0
    excess_seconds = max(0.0, gap_seconds - reference_p95_seconds)
    deviation = min(1.0, excess_seconds / (SATURATION_MINUTES * 60.0))

    coverage = coverage_confidence(distance_to_coast_nm_at_release)
    value = deviation * coverage

    return ScoringFactor(
        name="ais_gap_anomaly",
        value=value,
        weight=W4,
        contribution=W4 * value,
        confidence=confidence,
        note=note,
    )
