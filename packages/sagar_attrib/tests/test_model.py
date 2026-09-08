from __future__ import annotations

from datetime import datetime

import pytest
from sagar_attrib.baseline import BaselineGapProfile
from sagar_attrib.model import DriftEvidence, VesselFeatures, rank_candidates, score_candidate
from sagar_core.types import DataQualitySummary

RELIABLE_BASELINE = BaselineGapProfile(
    sample_count=300, median_gap_seconds=180, p95_gap_seconds=420, has_sufficient_history=True
)

CLEAN_DATA_QUALITY = DataQualitySummary(records_used=412, records_excluded=7, exclusion_reasons={})


def _strong_evidence_features(**overrides) -> VesselFeatures:
    """A vessel that looks a lot like services/api/app/fixtures.py's
    SYNTHETIC VESSEL A: a tanker, on-course, slowed down, with an unusual
    gap right at the release window."""
    defaults = dict(
        mmsi="419001234",
        imo=None,
        vessel_name="SYNTHETIC VESSEL A",
        vessel_type="tanker",
        course_over_ground_deg=247.0,  # near the slick's own bearing (247.3)
        sog_at_release_knots=6.0,
        sog_median_knots=11.0,
        course_change_deg=5.0,
        is_night=True,
        off_lane_distance_km=8.0,
        distance_to_port_km=40.0,
        distance_to_platform_km=60.0,
        in_eco_zone=False,
        gap_minutes_at_release=40.0,
        baseline=RELIABLE_BASELINE,
        distance_to_coast_nm_at_release=15.0,
        data_quality=CLEAN_DATA_QUALITY,
    )
    defaults.update(overrides)
    return VesselFeatures(**defaults)


def _weak_evidence_features(**overrides) -> VesselFeatures:
    """An innocent-looking vessel: fast, off its own median in the wrong
    direction (irrelevant per f3's one-sidedness), no gap, daytime, well
    inside a busy lane."""
    defaults = dict(
        mmsi="563889000",
        imo=None,
        vessel_name="SYNTHETIC VESSEL B",
        vessel_type=None,  # static data missing — f8 should be dropped
        course_over_ground_deg=10.0,  # far from the slick bearing
        sog_at_release_knots=14.0,
        sog_median_knots=12.0,
        course_change_deg=0.0,
        is_night=False,
        off_lane_distance_km=0.5,
        distance_to_port_km=200.0,
        distance_to_platform_km=200.0,
        in_eco_zone=False,
        gap_minutes_at_release=0.0,
        baseline=RELIABLE_BASELINE,
        distance_to_coast_nm_at_release=15.0,
        data_quality=CLEAN_DATA_QUALITY,
    )
    defaults.update(overrides)
    return VesselFeatures(**defaults)


def _strong_drift() -> DriftEvidence:
    return DriftEvidence(
        hit=0.9,
        coverage=0.85,
        t_star_utc=datetime(2026, 5, 25, 6, 40),
        release_ci_minutes=50.0,
        age_hours=7.3,
        age_ci_hours=(5.9, 8.8),
    )


def _weak_drift() -> DriftEvidence:
    return DriftEvidence(
        hit=0.05,
        coverage=0.05,
        t_star_utc=datetime(2026, 5, 25, 4, 10),
        release_ci_minutes=90.0,
        age_hours=9.9,
        age_ci_hours=(7.0, 13.0),
    )


SLICK_BEARING_DEG = 247.3
SLICK_ECCENTRICITY = 0.82  # matches services/api/app/fixtures.py's shape roughly


class TestScoreCandidate:
    def test_strong_evidence_produces_a_high_posterior(self):
        scored = score_candidate(
            _strong_evidence_features(), _strong_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        assert scored.posterior > 0.5

    def test_weak_evidence_produces_a_low_posterior(self):
        scored = score_candidate(
            _weak_evidence_features(), _weak_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        assert scored.posterior < 0.2

    def test_a_strong_candidate_outranks_a_weak_one(self):
        strong = score_candidate(
            _strong_evidence_features(), _strong_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        weak = score_candidate(
            _weak_evidence_features(), _weak_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        assert strong.posterior > weak.posterior

    def test_posterior_is_always_a_valid_probability(self):
        for features, drift in [
            (_strong_evidence_features(), _strong_drift()),
            (_weak_evidence_features(), _weak_drift()),
        ]:
            scored = score_candidate(features, drift, SLICK_BEARING_DEG, SLICK_ECCENTRICITY)
            assert 0.0 <= scored.posterior <= 1.0

    def test_missing_vessel_type_drops_f8_entirely(self):
        scored = score_candidate(
            _weak_evidence_features(vessel_type=None),
            _weak_drift(),
            SLICK_BEARING_DEG,
            SLICK_ECCENTRICITY,
        )
        assert all(fac.name != "vessel_type_prior" for fac in scored.factors)

    def test_present_vessel_type_includes_f8(self):
        scored = score_candidate(
            _strong_evidence_features(), _strong_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        assert any(fac.name == "vessel_type_prior" for fac in scored.factors)

    def test_round_slick_drops_f2_entirely(self):
        scored = score_candidate(
            _strong_evidence_features(),
            _strong_drift(),
            SLICK_BEARING_DEG,
            slick_eccentricity=0.05,  # below the guard threshold
        )
        assert all(fac.name != "course_alignment" for fac in scored.factors)

    def test_negative_contributing_factors_are_never_filtered_out(self):
        """docs/SCORING_MODEL.md §7: exculpatory factors are first-class
        and must appear in the output."""
        scored = score_candidate(
            _weak_evidence_features(off_lane_distance_km=0.0),  # squarely in-lane -> negative f7
            _weak_drift(),
            SLICK_BEARING_DEG,
            SLICK_ECCENTRICITY,
        )
        off_lane = next(fac for fac in scored.factors if fac.name == "off_lane_distance")
        assert off_lane.contribution < 0
        assert off_lane in scored.factors  # present, not stripped for being negative

    def test_release_and_slick_age_pass_through_from_drift_evidence(self):
        drift = _strong_drift()
        scored = score_candidate(
            _strong_evidence_features(), drift, SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        assert scored.release.at == drift.t_star_utc
        assert scored.release.ci_minutes == drift.release_ci_minutes
        assert scored.slick_age.hours == drift.age_hours
        assert scored.slick_age.ci.lo == drift.age_ci_hours[0]
        assert scored.slick_age.ci.hi == drift.age_ci_hours[1]

    def test_data_quality_passes_through_unchanged(self):
        scored = score_candidate(
            _strong_evidence_features(), _strong_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        assert scored.data_quality == CLEAN_DATA_QUALITY


class TestRankCandidates:
    def test_assigns_rank_by_descending_posterior(self):
        strong = score_candidate(
            _strong_evidence_features(mmsi="1"),
            _strong_drift(),
            SLICK_BEARING_DEG,
            SLICK_ECCENTRICITY,
        )
        weak = score_candidate(
            _weak_evidence_features(mmsi="2"), _weak_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        ranked = rank_candidates("det_test_001", [weak, strong])  # deliberately out of order
        assert [s.mmsi for s in ranked] == ["1", "2"]
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_every_suspect_is_uncalibrated(self):
        """docs/SCORING_MODEL.md §4: only hand-set priors exist so far, no
        Platt/isotonic fitting — every Suspect this produces must say so."""
        strong = score_candidate(
            _strong_evidence_features(), _strong_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        ranked = rank_candidates("det_test_001", [strong])
        assert ranked[0].calibrated is False

    def test_empty_candidate_list_produces_no_suspects(self):
        assert rank_candidates("det_test_001", []) == []

    def test_suspect_validates_against_sagar_core_pydantic_model(self):
        """rank_candidates returns REAL sagar_core.types.Suspect instances
        — if this didn't validate, Pydantic would have raised already,
        but assert the round trip explicitly so a future refactor that
        swaps in a lookalike dict is caught here."""
        strong = score_candidate(
            _strong_evidence_features(), _strong_drift(), SLICK_BEARING_DEG, SLICK_ECCENTRICITY
        )
        ranked = rank_candidates("det_test_001", [strong])
        assert ranked[0].detection_id == "det_test_001"
        assert ranked[0].posterior == pytest.approx(strong.posterior)
        assert len(ranked[0].factors) == len(strong.factors)
