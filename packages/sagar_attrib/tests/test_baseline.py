from __future__ import annotations

from datetime import datetime, timedelta

from sagar_attrib.baseline import MIN_SAMPLES_FOR_BASELINE, compute_baseline
from sagar_attrib.quality_filter import AisRecord


def _track(start: datetime, gap_seconds: list[float], mmsi: int = 419001234) -> list[AisRecord]:
    """Build a track whose consecutive gaps are exactly `gap_seconds`."""
    t = start
    records = [AisRecord(time=t, lat=10.0, lon=75.0, mmsi=mmsi)]
    for g in gap_seconds:
        t = t + timedelta(seconds=g)
        records.append(AisRecord(time=t, lat=10.0, lon=75.0, mmsi=mmsi))
    return records


def test_fewer_than_two_records_has_no_history():
    profile = compute_baseline([])
    assert profile.sample_count == 0
    assert not profile.has_sufficient_history

    one = _track(datetime(2026, 1, 1), [])
    assert compute_baseline(one).sample_count == 0


def test_median_and_p95_on_a_known_distribution():
    # 39 gaps of 60s, then one outlier of 3600s: median should sit at 60,
    # p95 should pick up the outlier region.
    gaps = [60.0] * 39 + [3600.0]
    profile = compute_baseline(_track(datetime(2026, 1, 1), gaps))
    assert profile.sample_count == 40
    assert profile.median_gap_seconds == 60.0
    assert profile.p95_gap_seconds >= 60.0


def test_has_sufficient_history_threshold():
    just_under = compute_baseline(
        _track(datetime(2026, 1, 1), [60.0] * (MIN_SAMPLES_FOR_BASELINE - 1))
    )
    exactly_at = compute_baseline(_track(datetime(2026, 1, 1), [60.0] * MIN_SAMPLES_FOR_BASELINE))

    assert not just_under.has_sufficient_history
    assert exactly_at.has_sufficient_history


def test_gap_order_does_not_depend_on_input_order():
    """compute_baseline must sort by time itself — a caller handing it an
    out-of-order list should get the same answer as an ordered one."""
    ordered = _track(datetime(2026, 1, 1), [60.0, 120.0, 30.0])
    shuffled = [ordered[2], ordered[0], ordered[3], ordered[1]]

    a = compute_baseline(ordered)
    b = compute_baseline(shuffled)
    assert a.median_gap_seconds == b.median_gap_seconds
    assert a.sample_count == b.sample_count


def test_a_vessel_that_routinely_drops_out_for_hours_has_a_high_baseline():
    """This is the whole point of the baseline (docs/SCORING_MODEL.md
    §2.1b) — its median/p95 reflect THIS vessel's normal, however unusual
    that normal is."""
    gaps = [7200.0] * 40  # two-hour gaps, every time, for this vessel
    profile = compute_baseline(_track(datetime(2026, 1, 1), gaps))
    assert profile.median_gap_seconds == 7200.0
    assert profile.has_sufficient_history
