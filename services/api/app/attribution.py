"""Wires packages/sagar_attrib's real scoring engine into
`GET /detections/{id}/suspects`.

`services/api` has never had a runtime dependency on anything under
`packages/` before this — `schemas.py`'s own module docstring explains why
the API keeps independent wire types rather than importing `sagar_core`'s
domain types directly. This module is the first real crossing of that
boundary, and it crosses it on purpose: the suspects endpoint should
return a REAL RANKING computed by real code, not an asserted one.

## What is real here

- The §2.1(a) AIS data-quality pre-filter (`sagar_attrib.quality_filter`),
  run against the actual points in `fixtures.AIS_TRACKS`.
- The vessel's own SOG/COG features, read from its track.
- The full nine-factor log-odds combination and sigmoid, exactly per
  `docs/SCORING_MODEL.md` (`sagar_attrib.model`).
- One concrete correction this surfaced: the old hardcoded fixture
  claimed `night_time_release=1.0` for a scene acquired at 06:40 UTC
  (~12:10 IST — plainly daytime). Real computation no longer asserts
  that contradiction.

## What is still a placeholder, named individually rather than hidden in
## one vague TODO — see docs/HANDOVER.md task H for the systems each one
## is waiting on

- `_PLACEHOLDER_DRIFT` — f1's `hit`/`coverage` need a real M5 OpenDrift
  ensemble solve, which does not exist (`packages/sagar_drift` is 0
  lines, blocked on WSL2). `sagar_attrib.factors.f1_drift_consistency`'s
  own docstring refuses to fabricate these — the placeholder lives HERE,
  in temporary fixture-backed glue code, not in the reusable scoring
  package. Every `drift_consistency` factor in the response carries a
  `note` saying so explicitly.
- `_PLACEHOLDER_CONTEXT` — off-lane distance needs a lane-KDE model,
  port/platform proximity needs a database, coast distance needs GEBCO
  bathymetry. None exist in Python yet (`sagar_ingest`, `sagar_sar` are
  both 0 lines).
- `_SLICK_ECCENTRICITY_PLACEHOLDER` — `SlickAttributes` (the frozen wire
  contract) has no eccentricity field yet; M3 doesn't exist to compute
  the real value either.
- `_RELEASE_WINDOW` — the demo AIS track has five points on a uniform
  40-minute cadence, too coarse to show a real slowdown or gap at a
  specific release instant. This fills in what a finer-grained query
  would show, without pretending the coarse public `/ais/tracks`
  fixture has resolution it doesn't have.
- `_CANDIDATE_MMSIS_BY_DETECTION` — WHICH vessels are candidates at all
  is properly the GATE/FILTER cascade's job (the 214→46→19→11→7 cascade
  in `docs/HANDOVER.md` task H), which is not built. The candidate list
  itself stays fixture-defined.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# See this module's own docstring: services/api has no other runtime
# dependency on packages/, so nothing else sets this up outside of
# pytest (conftest.py does the equivalent for tests only).
_PACKAGES_DIR = Path(__file__).resolve().parents[3] / "packages"
if str(_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_DIR))

from sagar_attrib.baseline import BaselineGapProfile as AttribBaselineGapProfile  # noqa: E402
from sagar_attrib.model import (  # noqa: E402
    DriftEvidence,
    ScoredCandidate,
    VesselFeatures,
    rank_candidates,
    score_candidate,
)
from sagar_attrib.quality_filter import AisRecord, filter_reliable  # noqa: E402

from . import fixtures  # noqa: E402
from .format import format_utc  # noqa: E402
from .schemas import DataQualitySummary, Suspect, SuspectFactor  # noqa: E402

_DRIFT_PLACEHOLDER_NOTE = (
    "hit/coverage are placeholder inputs standing in for a real M5 "
    "OpenDrift ensemble solve, which does not exist yet (packages/"
    "sagar_drift is 0 lines, blocked on WSL2 — see docs/ROADMAP.md "
    "Phase 1) — not a computed physical result."
)

#: Per-MMSI stand-in for an M5 ensemble solve's output. Chosen to be
#: broadly plausible (the stronger candidate has higher hit/coverage),
#: not fitted to anything real.
_PLACEHOLDER_DRIFT: dict[str, DriftEvidence] = {
    "419001234": DriftEvidence(
        hit=0.81,
        coverage=0.79,
        t_star_utc=datetime(2026, 5, 25, 6, 40, tzinfo=UTC),
        release_ci_minutes=50.0,
        age_hours=7.3,
        age_ci_hours=(5.9, 8.8),
    ),
    "563889000": DriftEvidence(
        hit=0.52,
        coverage=0.48,
        t_star_utc=datetime(2026, 5, 25, 5, 55, tzinfo=UTC),
        release_ci_minutes=70.0,
        age_hours=8.1,
        age_ci_hours=(6.2, 10.4),
    ),
}


@dataclass(frozen=True)
class _ContextPlaceholder:
    off_lane_distance_km: float
    distance_to_port_km: float
    distance_to_platform_km: float
    in_eco_zone: bool
    distance_to_coast_nm_at_release: float


_PLACEHOLDER_CONTEXT: dict[str, _ContextPlaceholder] = {
    "419001234": _ContextPlaceholder(
        off_lane_distance_km=6.0,
        distance_to_port_km=45.0,
        distance_to_platform_km=80.0,
        in_eco_zone=False,
        distance_to_coast_nm_at_release=18.0,
    ),
    "563889000": _ContextPlaceholder(
        off_lane_distance_km=1.5,
        distance_to_port_km=120.0,
        distance_to_platform_km=95.0,
        in_eco_zone=False,
        distance_to_coast_nm_at_release=22.0,
    ),
}

#: See module docstring — no eccentricity field in the wire contract yet.
_SLICK_ECCENTRICITY_PLACEHOLDER = 0.8


@dataclass(frozen=True)
class _ReleaseWindow:
    sog_at_release_knots: float
    gap_minutes_at_release: float
    course_change_deg: float
    is_night: bool


_RELEASE_WINDOW: dict[str, _ReleaseWindow] = {
    "419001234": _ReleaseWindow(
        # Slowed from its cruising 11.2kn (fixtures.AIS_TRACKS) — the
        # "reduced, steady speed" pattern docs/SCORING_MODEL.md f3 looks
        # for around a discharge.
        sog_at_release_knots=6.0,
        gap_minutes_at_release=40.0,
        course_change_deg=4.0,
        # Scene acquired 2026-05-25T06:40Z = ~12:10 IST — daytime.
        is_night=False,
    ),
    "563889000": _ReleaseWindow(
        sog_at_release_knots=14.8,  # unchanged from cruise — no anomaly
        gap_minutes_at_release=0.0,
        course_change_deg=1.0,
        is_night=False,
    ),
}

#: See module docstring — the GATE/FILTER cascade that would derive this
#: from a live query does not exist yet.
_CANDIDATE_MMSIS_BY_DETECTION: dict[str, list[str]] = {
    fixtures.DETECTION_OIL.id: ["419001234", "563889000"],
}


def _to_attrib_baseline(profile) -> AttribBaselineGapProfile:  # noqa: ANN001
    """Adapt `schemas.BaselineGapProfile` (wire) to
    `sagar_attrib.baseline.BaselineGapProfile` (domain) — the same facts,
    two independently-defined types either side of the API-contract
    boundary, same reason `fixtures.py`'s own docstring gives for keeping
    the console and API fixture sets in step by hand rather than sharing
    a type."""
    if profile is None:
        return AttribBaselineGapProfile(
            sample_count=0,
            median_gap_seconds=0.0,
            p95_gap_seconds=0.0,
            has_sufficient_history=False,
        )
    return AttribBaselineGapProfile(
        sample_count=profile.sample_count,
        median_gap_seconds=profile.median_gap_seconds,
        p95_gap_seconds=profile.p95_gap_seconds,
        has_sufficient_history=profile.has_sufficient_history,
    )


def _build_features(mmsi: str) -> VesselFeatures:
    vessel = fixtures.VESSELS.get(mmsi)
    track = fixtures.AIS_TRACKS[mmsi]
    window = _RELEASE_WINDOW[mmsi]
    context = _PLACEHOLDER_CONTEXT[mmsi]

    records = [
        AisRecord(
            time=datetime.fromisoformat(point.time_utc.replace("Z", "+00:00")),
            lat=point.lat,
            lon=point.lon,
            mmsi=int(mmsi),
            sog_knots=point.sog_knots,
        )
        for point in track.points
    ]
    # Real §2.1(a) pre-filter, run against the actual demo track — not
    # asserted numbers. `filter_reliable` already returns a
    # sagar_core.types.DataQualitySummary, the exact type VesselFeatures
    # wants, so no further adaptation is needed here.
    reliable, quality_summary = filter_reliable(records)

    sog_values = [r.sog_knots for r in reliable if r.sog_knots is not None]
    sog_median = sum(sog_values) / len(sog_values) if sog_values else window.sog_at_release_knots
    last_cog = next(
        (p.cog_degrees for p in reversed(track.points) if p.cog_degrees is not None), 0.0
    )

    return VesselFeatures(
        mmsi=mmsi,
        imo=vessel.imo if vessel else None,
        vessel_name=track.vessel_name or mmsi,
        vessel_type=vessel.vessel_type if vessel else None,
        course_over_ground_deg=last_cog,
        sog_at_release_knots=window.sog_at_release_knots,
        sog_median_knots=sog_median,
        course_change_deg=window.course_change_deg,
        is_night=window.is_night,
        off_lane_distance_km=context.off_lane_distance_km,
        distance_to_port_km=context.distance_to_port_km,
        distance_to_platform_km=context.distance_to_platform_km,
        in_eco_zone=context.in_eco_zone,
        gap_minutes_at_release=window.gap_minutes_at_release,
        baseline=_to_attrib_baseline(vessel.baseline_gap_profile if vessel else None),
        distance_to_coast_nm_at_release=context.distance_to_coast_nm_at_release,
        data_quality=quality_summary,
    )


def _to_wire_factor(factor) -> SuspectFactor:  # noqa: ANN001
    note = factor.note
    if factor.name == "drift_consistency":
        note = _DRIFT_PLACEHOLDER_NOTE
    return SuspectFactor(
        name=factor.name,
        value=factor.value,
        weight=factor.weight,
        contribution=factor.contribution,
        confidence=factor.confidence.value,
        note=note,
    )


def _to_wire_suspect(candidate) -> Suspect:  # noqa: ANN001
    return Suspect(
        rank=candidate.rank,
        mmsi=candidate.mmsi,
        imo=candidate.imo,
        vessel_name=candidate.vessel_name or candidate.mmsi,
        vessel_type=candidate.vessel_type or "unknown",
        posterior=candidate.posterior,
        calibrated=candidate.calibrated,
        inferred_release_utc=format_utc(candidate.release.at),
        inferred_release_ci_minutes=candidate.release.ci_minutes,
        slick_age_hours=candidate.slick_age.hours,
        slick_age_ci=(candidate.slick_age.ci.lo, candidate.slick_age.ci.hi),
        factors=[_to_wire_factor(f) for f in candidate.factors],
        data_quality=DataQualitySummary(
            records_used=candidate.data_quality.records_used,
            records_excluded=candidate.data_quality.records_excluded,
            exclusion_reasons=candidate.data_quality.exclusion_reasons,
        ),
    )


def score_suspects(detection_id: str) -> list[Suspect]:
    """Real replacement for the old `fixtures.SUSPECTS_BY_DETECTION`
    lookup. See this module's docstring for exactly what is real and
    what is still a placeholder."""
    detection = fixtures.DETECTIONS.get(detection_id)
    mmsi_list = _CANDIDATE_MMSIS_BY_DETECTION.get(detection_id, [])
    if detection is None or not mmsi_list:
        return []

    slick_bearing_deg = detection.attributes.major_axis_bearing_deg

    scored: list[ScoredCandidate] = [
        score_candidate(
            _build_features(mmsi),
            _PLACEHOLDER_DRIFT[mmsi],
            slick_bearing_deg,
            _SLICK_ECCENTRICITY_PLACEHOLDER,
        )
        for mmsi in mmsi_list
    ]
    ranked = rank_candidates(detection_id, scored)
    return [_to_wire_suspect(candidate) for candidate in ranked]
