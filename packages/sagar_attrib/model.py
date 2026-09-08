"""docs/SCORING_MODEL.md §1, §3, §7: combine the nine factors into a
posterior, then rank a detection's candidates.

`calibrated` is always False here — no Platt/isotonic fitting has been
done (§4 step 4 is future work; this module implements step 1, the
hand-set priors, which "ship as defaults and work without any training
data"). A caller must not present `posterior` as a true probability
until real calibration exists.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from sagar_core.types import (
    DataQualitySummary,
    Interval,
    ReleaseTimeEstimate,
    ScoringFactor,
    SlickAgeEstimate,
    Suspect,
)

from . import factors as f
from .baseline import BaselineGapProfile
from .gap_anomaly import score_gap_anomaly

#: docs/SCORING_MODEL.md §3: "strongly negative on purpose... a model
#: that does not encode that will produce inflated posteriors for
#: everyone and the calibration will be worthless."
INTERCEPT_W0 = -4.0


@dataclass(frozen=True)
class DriftEvidence:
    """Output of an M5 OpenDrift ensemble solve for one (vessel, slick)
    pair — computed elsewhere, never by this package. See f1's own
    docstring in factors.py."""

    hit: float
    coverage: float
    t_star_utc: datetime
    release_ci_minutes: float
    age_hours: float
    age_ci_hours: tuple[float, float]


@dataclass(frozen=True)
class VesselFeatures:
    """Everything f2–f9 need about one candidate vessel, already extracted
    from its AIS track. Building this from a raw track (interpolation,
    lane-distance, coast-distance) is a separate concern from scoring it —
    see this package's tests for worked examples of the shape callers are
    expected to supply."""

    mmsi: str
    imo: str | None
    vessel_name: str | None
    vessel_type: str | None

    course_over_ground_deg: float
    sog_at_release_knots: float
    sog_median_knots: float
    course_change_deg: float
    is_night: bool
    off_lane_distance_km: float
    distance_to_port_km: float
    distance_to_platform_km: float
    in_eco_zone: bool

    gap_minutes_at_release: float
    baseline: BaselineGapProfile
    distance_to_coast_nm_at_release: float

    data_quality: DataQualitySummary


@dataclass(frozen=True)
class ScoredCandidate:
    """One candidate's result, before a detection_id and rank are known —
    see rank_candidates, which assigns both once the whole candidate list
    for a detection has been scored."""

    mmsi: str
    imo: str | None
    vessel_name: str | None
    vessel_type: str | None
    posterior: float
    release: ReleaseTimeEstimate
    slick_age: SlickAgeEstimate
    factors: list[ScoringFactor]
    data_quality: DataQualitySummary


def score_candidate(
    features: VesselFeatures,
    drift: DriftEvidence,
    slick_bearing_deg: float,
    slick_eccentricity: float,
) -> ScoredCandidate:
    """Score one vessel against one slick. f2 and f8 may be absent from
    the returned factor list entirely (dropped, not zeroed) per
    docs/SCORING_MODEL.md's guards — see factors.py."""
    computed: list[ScoringFactor] = [f.f1_drift_consistency(drift.hit, drift.coverage)]

    course_alignment = f.f2_course_alignment(
        slick_bearing_deg, features.course_over_ground_deg, slick_eccentricity
    )
    if course_alignment is not None:
        computed.append(course_alignment)

    computed.append(f.f3_speed_anomaly(features.sog_at_release_knots, features.sog_median_knots))

    computed.append(
        score_gap_anomaly(
            gap_minutes_at_release=features.gap_minutes_at_release,
            baseline=features.baseline,
            distance_to_coast_nm_at_release=features.distance_to_coast_nm_at_release,
        )
    )

    computed.append(f.f5_course_change(features.course_change_deg))
    computed.append(f.f6_night_time_release(features.is_night))
    computed.append(f.f7_off_lane_distance(features.off_lane_distance_km))

    vessel_type_prior = f.f8_vessel_type_prior(features.vessel_type)
    if vessel_type_prior is not None:
        computed.append(vessel_type_prior)

    computed.append(
        f.f9_contextual_proximity(
            features.distance_to_port_km, features.distance_to_platform_km, features.in_eco_zone
        )
    )

    logit = INTERCEPT_W0 + sum(factor.contribution for factor in computed)
    posterior = 1.0 / (1.0 + math.exp(-logit))

    age_lo, age_hi = drift.age_ci_hours
    return ScoredCandidate(
        mmsi=features.mmsi,
        imo=features.imo,
        vessel_name=features.vessel_name,
        vessel_type=features.vessel_type,
        posterior=posterior,
        release=ReleaseTimeEstimate(at=drift.t_star_utc, ci_minutes=drift.release_ci_minutes),
        slick_age=SlickAgeEstimate(hours=drift.age_hours, ci=Interval(lo=age_lo, hi=age_hi)),
        factors=computed,
        data_quality=features.data_quality,
    )


def rank_candidates(detection_id: str, scored: list[ScoredCandidate]) -> list[Suspect]:
    """Sort descending by posterior and assign rank 1..N. `calibrated`
    is always False — see this module's docstring."""
    ordered = sorted(scored, key=lambda c: c.posterior, reverse=True)
    return [
        Suspect(
            detection_id=detection_id,
            mmsi=c.mmsi,
            imo=c.imo,
            vessel_name=c.vessel_name,
            vessel_type=c.vessel_type,
            rank=rank,
            posterior=c.posterior,
            calibrated=False,
            release=c.release,
            slick_age=c.slick_age,
            factors=c.factors,
            data_quality=c.data_quality,
        )
        for rank, c in enumerate(ordered, start=1)
    ]
