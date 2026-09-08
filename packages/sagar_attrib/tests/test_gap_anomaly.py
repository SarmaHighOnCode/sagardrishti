"""f4 is the most dangerous factor in the model (docs/SCORING_MODEL.md
§2.1) — these tests exist to prove the three safety properties the spec
demands, not just that the arithmetic runs."""

from __future__ import annotations

from sagar_attrib.baseline import NO_HISTORY, BaselineGapProfile
from sagar_attrib.gap_anomaly import W4, coverage_confidence, score_gap_anomaly
from sagar_core.types import FactorConfidence

RELIABLE_BASELINE = BaselineGapProfile(
    sample_count=200, median_gap_seconds=300, p95_gap_seconds=900, has_sufficient_history=True
)


def test_a_gap_within_the_vessels_own_normal_behaviour_scores_near_zero():
    """A vessel that routinely drops out scores LOW even with a gap near
    the spill — docs/SCORING_MODEL.md §2.1(b)'s central example."""
    factor = score_gap_anomaly(
        gap_minutes_at_release=RELIABLE_BASELINE.p95_gap_seconds / 60,  # exactly its own p95
        baseline=RELIABLE_BASELINE,
        distance_to_coast_nm_at_release=10,
    )
    assert factor.value == 0.0


def test_an_unusual_gap_for_a_normally_reliable_vessel_scores_high():
    """A vessel that reports like clockwork, then has one unusual gap at
    the release time and place, scores HIGH — the other half of that
    example."""
    reliable_vessel = BaselineGapProfile(
        sample_count=500, median_gap_seconds=60, p95_gap_seconds=120, has_sufficient_history=True
    )
    factor = score_gap_anomaly(
        gap_minutes_at_release=90,  # a full 90-minute gap vs a normal ~1-2 min cadence
        baseline=reliable_vessel,
        distance_to_coast_nm_at_release=5,  # near shore — coverage should not discount this
    )
    assert factor.value > 0.8
    assert factor.confidence == FactorConfidence.HIGH


def test_missing_baseline_is_marked_low_confidence_not_dropped():
    """docs/SCORING_MODEL.md §5: unlike f8, a missing baseline is NOT
    dropped — it falls back to a conservative fixed prior and is marked
    low-confidence, because dropping f4 for every newly-seen vessel would
    blind the model to exactly the vessels it most needs care with."""
    factor = score_gap_anomaly(
        gap_minutes_at_release=45, baseline=NO_HISTORY, distance_to_coast_nm_at_release=10
    )
    assert factor is not None
    assert factor.confidence == FactorConfidence.LOW
    assert "insufficient" in factor.note.lower()


def test_offshore_gap_is_discounted_relative_to_an_identical_coastal_gap():
    """docs/SCORING_MODEL.md §2.1(c): far offshore with no satellite AIS,
    a gap is expected regardless of intent."""
    reliable_vessel = BaselineGapProfile(
        sample_count=500, median_gap_seconds=60, p95_gap_seconds=120, has_sufficient_history=True
    )
    coastal = score_gap_anomaly(
        gap_minutes_at_release=90, baseline=reliable_vessel, distance_to_coast_nm_at_release=5
    )
    offshore = score_gap_anomaly(
        gap_minutes_at_release=90, baseline=reliable_vessel, distance_to_coast_nm_at_release=200
    )
    assert offshore.value < coastal.value


def test_coverage_confidence_is_bounded_and_monotonically_non_increasing():
    samples = [0, 10, 30, 57.5, 80, 150, 500]
    values = [coverage_confidence(d) for d in samples]
    for v in values:
        assert 0.0 <= v <= 1.0
    for a, b in zip(values, values[1:], strict=False):  # sliding pairwise, deliberately unequal
        assert a >= b - 1e-9  # non-increasing, allowing for float rounding


def test_weight_matches_the_documented_prior():
    assert W4 == 1.3


def test_value_is_always_between_zero_and_one():
    """docs/SCORING_MODEL.md f4: 'Range [0, 1]'."""
    for gap_minutes in (0, 5, 30, 60, 200, 1000):
        for baseline in (NO_HISTORY, RELIABLE_BASELINE):
            for distance in (0, 50, 60, 500):
                factor = score_gap_anomaly(
                    gap_minutes_at_release=gap_minutes,
                    baseline=baseline,
                    distance_to_coast_nm_at_release=distance,
                )
                assert 0.0 <= factor.value <= 1.0, (gap_minutes, baseline, distance, factor.value)


def test_no_gap_scores_zero_regardless_of_baseline_or_location():
    for baseline in (NO_HISTORY, RELIABLE_BASELINE):
        factor = score_gap_anomaly(
            gap_minutes_at_release=0, baseline=baseline, distance_to_coast_nm_at_release=5
        )
        assert factor.value == 0.0
