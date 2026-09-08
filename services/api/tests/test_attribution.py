"""app/attribution.py wires packages/sagar_attrib's real scoring engine
into GET /detections/{id}/suspects. These tests check the adapter layer
itself (type conversion, wiring) — the scoring math is already covered
by packages/sagar_attrib's own 66 tests; duplicating that here would
just be testing the same arithmetic twice.
"""

from __future__ import annotations

from app import attribution, fixtures


def test_score_suspects_returns_wire_suspect_objects():
    suspects = attribution.score_suspects(fixtures.DETECTION_OIL.id)
    assert len(suspects) == 2
    assert {s.mmsi for s in suspects} == {"419001234", "563889000"}


def test_ranked_by_posterior_descending():
    suspects = attribution.score_suspects(fixtures.DETECTION_OIL.id)
    assert suspects[0].rank == 1
    assert suspects[1].rank == 2
    assert suspects[0].posterior >= suspects[1].posterior


def test_every_suspect_is_uncalibrated():
    """No Platt/isotonic fitting exists yet — see sagar_attrib.model's
    own docstring. A suspect claiming calibrated=True here would assert
    a property nothing has actually verified."""
    suspects = attribution.score_suspects(fixtures.DETECTION_OIL.id)
    assert all(s.calibrated is False for s in suspects)


def test_negative_contributions_survive_the_wire_conversion():
    """docs/SCORING_MODEL.md §7 — exculpatory factors must never be
    filtered, including across the domain-to-wire adapter boundary."""
    suspects = attribution.score_suspects(fixtures.DETECTION_OIL.id)
    assert any(f.contribution < 0 for s in suspects for f in s.factors)


def test_drift_consistency_factor_carries_the_placeholder_note():
    """f1's hit/coverage are a documented placeholder pending M5 — every
    drift_consistency factor in the API response must say so, not just
    the module docstring nobody reading the JSON will see."""
    suspects = attribution.score_suspects(fixtures.DETECTION_OIL.id)
    for s in suspects:
        drift_factor = next(f for f in s.factors if f.name == "drift_consistency")
        assert drift_factor.note == attribution._DRIFT_PLACEHOLDER_NOTE
        assert "M5" in drift_factor.note


def test_unknown_detection_returns_empty_list():
    assert attribution.score_suspects("does-not-exist") == []


def test_lookalike_detection_has_no_suspects():
    """A rejected look-alike was already killed by Stage C — it never
    reaches candidate scoring at all."""
    assert attribution.score_suspects(fixtures.DETECTION_LOOKALIKE.id) == []


def test_release_and_slick_age_are_present_with_their_intervals():
    """The uncertainty-pairing rule (schemas.Suspect) applies just as
    much to a computed value as a hardcoded one."""
    suspects = attribution.score_suspects(fixtures.DETECTION_OIL.id)
    for s in suspects:
        assert s.inferred_release_utc.endswith("Z")
        assert s.inferred_release_ci_minutes > 0
        assert s.slick_age_ci[0] <= s.slick_age_hours <= s.slick_age_ci[1]


def test_data_quality_reflects_the_actual_demo_track_not_an_invented_number():
    """The old hardcoded fixture claimed 412 records used for a vessel
    whose demo track has five points. Real computation must report what
    the actual fixture data contains."""
    suspects = attribution.score_suspects(fixtures.DETECTION_OIL.id)
    vessel_a = next(s for s in suspects if s.mmsi == "419001234")
    assert vessel_a.data_quality.records_used == len(fixtures.AIS_TRACKS["419001234"].points)


def test_build_features_uses_the_vessels_own_long_term_baseline():
    """The baseline must come from fixtures.VESSELS' long-term profile,
    not be recomputed from the short demo track (5 points is nowhere
    near MIN_SAMPLES_FOR_BASELINE) — recomputing it from the demo track
    would wrongly mark every vessel as having insufficient history."""
    features = attribution._build_features("419001234")
    assert features.baseline.has_sufficient_history is True
    assert features.baseline.sample_count == (
        fixtures.VESSELS["419001234"].baseline_gap_profile.sample_count
    )


def test_missing_baseline_profile_falls_back_to_no_history_not_a_crash():
    """A candidate with no VesselStatic.baseline_gap_profile at all (a
    vessel seen for the first time, in real terms) must adapt to "no
    history", not raise or silently fabricate one."""
    profile = attribution._to_attrib_baseline(None)
    assert profile.has_sufficient_history is False
    assert profile.sample_count == 0
