"""f1–f3, f5–f9 — docs/SCORING_MODEL.md §2.

f4 (AIS gap anomaly) lives in gap_anomaly.py: it is the safety-critical
one and gets its own module and its own test file.
"""

from __future__ import annotations

import math

from sagar_core.types import FactorConfidence, ScoringFactor
from sagar_core.units import bearing_difference_deg


def f1_drift_consistency(hit: float, coverage: float) -> ScoringFactor:
    """docs/SCORING_MODEL.md f1: the F-measure of a candidate release's
    forward-drifted plume against the observed slick, maximised over
    release time.

    `hit`/`coverage` come from an M5 OpenDrift ensemble solve — this
    function does NOT run any physics, and does not import sagar_drift.
    See this package's own __init__.py for why: OpenDrift needs WSL2,
    which is broken in the environment this module was built in. Callers
    without a real drift solve yet should not call this with invented
    numbers — that would fabricate the single highest-weighted factor in
    the model.
    """
    value = 0.0 if hit + coverage == 0 else 2 * hit * coverage / (hit + coverage)
    return ScoringFactor(
        name="drift_consistency",
        value=value,
        weight=2.5,
        contribution=2.5 * value,
        confidence=FactorConfidence.HIGH,
    )


def f2_course_alignment(
    slick_bearing_deg: float,
    vessel_cog_deg: float,
    slick_eccentricity: float,
    eccentricity_guard: float = 0.3,
) -> ScoringFactor | None:
    """Returns None — dropped, not scored as zero — when the slick is too
    round for a major-axis bearing to mean anything. docs/SCORING_MODEL.md
    f2: "feeding noise in as evidence is worse than omitting the term."
    `slick_eccentricity` is `SlickAttributes.eccentricity` from M3 (0 =
    circle, closer to 1 = elongated); the 0.3 default is a documented,
    adjustable judgement call, not a value derived from data we have.
    """
    if slick_eccentricity < eccentricity_guard:
        return None

    diff_deg = bearing_difference_deg(slick_bearing_deg, vessel_cog_deg)
    value = abs(math.cos(math.radians(diff_deg)))
    return ScoringFactor(
        name="course_alignment",
        value=value,
        weight=1.4,
        contribution=1.4 * value,
        confidence=FactorConfidence.MEDIUM,
    )


def f3_speed_anomaly(
    sog_at_release_knots: float, sog_median_knots: float, saturation_knots: float = 8.0
) -> ScoringFactor:
    """One-sided per docs/SCORING_MODEL.md f3: only SLOWER than the
    vessel's own median counts. Going faster than usual is not evidence
    of innocence, so this never contributes negatively — the deficit is
    clamped at 0, not allowed to go negative."""
    if sog_median_knots <= 0:
        value = 0.0
    else:
        deficit_knots = max(0.0, sog_median_knots - sog_at_release_knots)
        value = min(1.0, deficit_knots / saturation_knots)
    return ScoringFactor(
        name="speed_anomaly",
        value=value,
        weight=1.1,
        contribution=1.1 * value,
        confidence=FactorConfidence.MEDIUM,
    )


def f5_course_change(course_change_deg: float, saturation_deg: float = 90.0) -> ScoringFactor:
    """docs/SCORING_MODEL.md f5: weak evidence, included because it costs
    nothing, must never drive a ranking on its own — hence the lowish
    weight of 0.6 relative to the physical/behavioural factors above."""
    value = min(1.0, abs(course_change_deg) / saturation_deg)
    return ScoringFactor(
        name="course_change",
        value=value,
        weight=0.6,
        contribution=0.6 * value,
        confidence=FactorConfidence.LOW,
    )


def f6_night_time_release(is_night: bool) -> ScoringFactor:
    """docs/SCORING_MODEL.md f6: a base-rate factor, not an individuating
    one — roughly half of all vessel-hours are at night, which is why the
    weight (0.5) stays low even though the value is a clean 0/1."""
    value = 1.0 if is_night else 0.0
    return ScoringFactor(
        name="night_time_release",
        value=value,
        weight=0.5,
        contribution=0.5 * value,
        confidence=FactorConfidence.MEDIUM,
    )


def f7_off_lane_distance(off_lane_distance_km: float, saturation_km: float = 20.0) -> ScoringFactor:
    """Range [-0.5, 1] per docs/SCORING_MODEL.md f7 — NOT [0, 1] shifted
    down at the low end. A vessel squarely on the lane centreline (0 km
    off) is at the MOST exculpatory point, -0.5, not merely neutral;
    "off lane" then ramps linearly up through 0 (neutral) to +1.0
    (maximally notable) by saturation_km. A plain
    `distance / saturation_km` clamped at -0.5 can never actually reach
    -0.5 for any physically valid (non-negative) distance — caught by
    this factor's own test asserting distance=0 scores negative."""
    fraction = max(0.0, min(1.0, off_lane_distance_km / saturation_km))
    value = -0.5 + 1.5 * fraction
    return ScoringFactor(
        name="off_lane_distance",
        value=value,
        weight=0.8,
        contribution=0.8 * value,
        confidence=FactorConfidence.MEDIUM,
    )


#: docs/SCORING_MODEL.md f8: "tanker > bulk carrier > container > general
#: cargo > fishing > other". Ordinal priors, not fitted — see §4 step 1.
_TYPE_PRIORS: dict[str, float] = {
    "tanker": 1.0,
    "bulk_carrier": 0.75,
    "container": 0.55,
    "general_cargo": 0.4,
    "fishing": 0.2,
    "tug": 0.15,
    "other": 0.1,
}


def f8_vessel_type_prior(vessel_type: str | None) -> ScoringFactor | None:
    """Returns None — DROPPED, never defaulted — when static data is
    missing. docs/SCORING_MODEL.md f8: "Assuming a type we do not know is
    fabricating evidence." An unrecognised (but present) type string still
    scores via the "other" prior rather than being dropped — the guard is
    specifically for absent data, not for an unfamiliar value."""
    if not vessel_type:
        return None
    value = _TYPE_PRIORS.get(vessel_type.lower(), _TYPE_PRIORS["other"])
    return ScoringFactor(
        name="vessel_type_prior",
        value=value,
        weight=0.7,
        contribution=0.7 * value,
        confidence=FactorConfidence.LOW,
        note=f"prior for vessel_type={vessel_type!r}",
    )


def f9_contextual_proximity(
    distance_to_port_km: float,
    distance_to_platform_km: float,
    in_eco_zone: bool,
    saturation_km: float = 10.0,
) -> ScoringFactor:
    """docs/SCORING_MODEL.md f9: composite of port/platform/eco-zone
    proximity, taken as the max of the three components (not summed) —
    the three routes to a high score describe different, non-additive
    reasons a location might be contextually notable, not evidence that
    should compound."""
    port = max(0.0, 1.0 - distance_to_port_km / saturation_km)
    platform = max(0.0, 1.0 - distance_to_platform_km / saturation_km)
    eco = 1.0 if in_eco_zone else 0.0
    value = min(1.0, max(port, platform, eco))
    return ScoringFactor(
        name="contextual_proximity",
        value=value,
        weight=0.4,
        contribution=0.4 * value,
        confidence=FactorConfidence.LOW,
    )
