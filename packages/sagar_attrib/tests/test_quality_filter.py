from __future__ import annotations

from datetime import datetime, timedelta

from sagar_attrib.quality_filter import AisRecord, filter_reliable


def test_clean_track_is_entirely_reliable():
    records = [
        AisRecord(time=datetime(2026, 1, 1, 0, 0), lat=10.0, lon=75.0, mmsi=419001234),
        AisRecord(time=datetime(2026, 1, 1, 0, 10), lat=10.02, lon=75.02, mmsi=419001234),
        AisRecord(time=datetime(2026, 1, 1, 0, 20), lat=10.04, lon=75.04, mmsi=419001234),
    ]
    reliable, summary = filter_reliable(records)
    assert len(reliable) == 3
    assert summary.records_used == 3
    assert summary.records_excluded == 0
    assert summary.exclusion_reasons == {}


def test_mmsi_zero_is_excluded():
    records = [AisRecord(time=datetime(2026, 1, 1), lat=10.0, lon=75.0, mmsi=0)]
    reliable, summary = filter_reliable(records)
    assert reliable == []
    assert summary.exclusion_reasons == {"mmsi_zero": 1}


def test_null_island_is_excluded():
    records = [AisRecord(time=datetime(2026, 1, 1), lat=0.0, lon=0.0, mmsi=419001234)]
    reliable, summary = filter_reliable(records)
    assert reliable == []
    assert summary.exclusion_reasons == {"null_island": 1}


def test_out_of_range_coordinates_are_excluded():
    records = [AisRecord(time=datetime(2026, 1, 1), lat=95.0, lon=75.0, mmsi=419001234)]
    reliable, summary = filter_reliable(records)
    assert reliable == []
    assert summary.exclusion_reasons == {"out_of_range": 1}


def test_impossible_speed_between_consecutive_positions_is_excluded():
    """50nm in 30 seconds is ~6000 knots — no merchant vessel does this."""
    base = datetime(2026, 1, 1)
    records = [
        AisRecord(time=base, lat=10.0, lon=75.0, mmsi=419001234),
        AisRecord(time=base + timedelta(seconds=30), lat=10.83, lon=75.0, mmsi=419001234),
    ]
    reliable, summary = filter_reliable(records)
    assert len(reliable) == 1  # the first position stands; the teleport is what's excluded
    assert summary.exclusion_reasons == {"impossible_speed": 1}


def test_a_bad_ping_does_not_cascade_into_excluding_the_next_good_one():
    """The teleport check must compare against the last RELIABLE record,
    not the immediately preceding raw one — otherwise a single null-island
    glitch would make every subsequent good position look like a
    multi-thousand-knot jump FROM (0,0), and wrongly exclude good data
    that follows a single bad ping."""
    base = datetime(2026, 1, 1)
    records = [
        AisRecord(time=base, lat=10.0, lon=75.0, mmsi=419001234),
        AisRecord(time=base + timedelta(minutes=1), lat=0.0, lon=0.0, mmsi=419001234),  # glitch
        AisRecord(time=base + timedelta(minutes=2), lat=10.02, lon=75.02, mmsi=419001234),  # fine
    ]
    reliable, summary = filter_reliable(records)
    assert len(reliable) == 2  # the first and third — the glitch alone is excluded
    assert summary.exclusion_reasons == {"null_island": 1}
    assert summary.records_used == 2


def test_unreliable_records_are_simply_absent_not_penalised():
    """docs/SCORING_MODEL.md §2.1(a): 'unreliable records neither boost
    nor penalise a vessel's score.' There is no field on AisRecord or in
    the summary that flags a record as 'bad but scored anyway' — it is
    just not in the reliable list, full stop."""
    records = [
        AisRecord(time=datetime(2026, 1, 1), lat=10.0, lon=75.0, mmsi=419001234),
        AisRecord(time=datetime(2026, 1, 1, 0, 5), lat=0.0, lon=0.0, mmsi=419001234),
    ]
    reliable, _ = filter_reliable(records)
    assert all(r.lat != 0.0 or r.lon != 0.0 for r in reliable)


def test_records_out_of_time_order_are_sorted_before_filtering():
    base = datetime(2026, 1, 1)
    records = [
        AisRecord(time=base + timedelta(minutes=10), lat=10.02, lon=75.02, mmsi=419001234),
        AisRecord(time=base, lat=10.0, lon=75.0, mmsi=419001234),
    ]
    reliable, summary = filter_reliable(records)
    assert len(reliable) == 2
    assert reliable[0].time < reliable[1].time
    assert summary.exclusion_reasons == {}


def test_zero_or_negative_elapsed_time_is_not_treated_as_a_speed_violation():
    """Two records at the identical instant imply a division by zero, not
    evidence of anything — must not raise and must not be excluded on a
    speed basis."""
    same_time = datetime(2026, 1, 1)
    records = [
        AisRecord(time=same_time, lat=10.0, lon=75.0, mmsi=419001234),
        AisRecord(time=same_time, lat=10.0, lon=75.01, mmsi=419001234),
    ]
    reliable, summary = filter_reliable(records)
    assert len(reliable) == 2
    assert "impossible_speed" not in summary.exclusion_reasons


def test_multiple_exclusion_reasons_are_all_counted():
    records = [
        AisRecord(time=datetime(2026, 1, 1), lat=10.0, lon=75.0, mmsi=419001234),
        AisRecord(time=datetime(2026, 1, 1, 0, 1), lat=0.0, lon=0.0, mmsi=419001234),
        AisRecord(time=datetime(2026, 1, 1, 0, 2), lat=0.0, lon=0.0, mmsi=0),
    ]
    reliable, summary = filter_reliable(records)
    # mmsi_zero is checked before null_island for the third record — only
    # one reason is ever attributed per record, and mmsi is the more
    # fundamental defect of the two.
    assert summary.exclusion_reasons.get("null_island") == 1
    assert summary.exclusion_reasons.get("mmsi_zero") == 1
    assert len(reliable) == 1
