"""Unit tests for the two contract rules enforced structurally in
app/schemas.py: uncertainty-must-be-paired and lon/lat-not-lat/lon.

These do not need the app or a client — they test the Pydantic models
directly, which is the level the enforcement actually lives at.
"""

from __future__ import annotations

import pytest
from app.schemas import DataQualitySummary, GeoPoint, GeoPolygon, Suspect, SuspectFactor
from pydantic import ValidationError


def _minimal_suspect(**overrides: object) -> dict:
    base = dict(
        rank=1,
        mmsi="419001234",
        vessel_name="TEST VESSEL",
        vessel_type="tanker",
        posterior=0.71,
        calibrated=True,
        inferred_release_utc="2026-05-25T06:40:00Z",
        inferred_release_ci_minutes=50,
        slick_age_hours=7.3,
        slick_age_ci=(5.9, 8.8),
        factors=[
            SuspectFactor(
                name="drift_consistency",
                value=0.81,
                weight=2.5,
                contribution=2.14,
                confidence="high",
            )
        ],
        data_quality=DataQualitySummary(records_used=10, records_excluded=0),
    )
    base.update(overrides)
    return base


class TestUncertaintyMustBePaired:
    """API_CONTRACT.md: "a bare slick_age_hours with no interval is a
    schema violation, not a convenience." """

    def test_valid_suspect_constructs(self):
        Suspect(**_minimal_suspect())  # must not raise

    def test_slick_age_hours_without_ci_is_rejected(self):
        payload = _minimal_suspect()
        del payload["slick_age_ci"]
        with pytest.raises(ValidationError):
            Suspect(**payload)

    def test_slick_age_ci_without_hours_is_rejected(self):
        payload = _minimal_suspect()
        del payload["slick_age_hours"]
        with pytest.raises(ValidationError):
            Suspect(**payload)

    def test_inferred_release_utc_without_ci_minutes_is_rejected(self):
        payload = _minimal_suspect()
        del payload["inferred_release_ci_minutes"]
        with pytest.raises(ValidationError):
            Suspect(**payload)

    def test_exculpatory_negative_contribution_is_not_special_cased(self):
        # A negative contribution is ordinary data, not a validation error -
        # SCORING_MODEL.md is explicit that exculpatory factors are never
        # hidden, so the schema must not reject or silently drop them.
        factor = SuspectFactor(
            name="off_lane_distance", value=-0.17, weight=0.8, contribution=-0.22, confidence="high"
        )
        assert factor.contribution == -0.22


class TestTimestampMustBeUtcZ:
    def test_offset_notation_is_rejected(self):
        payload = _minimal_suspect(inferred_release_utc="2026-05-25T06:40:00+00:00")
        with pytest.raises(ValidationError):
            Suspect(**payload)

    def test_missing_time_component_is_rejected(self):
        payload = _minimal_suspect(inferred_release_utc="2026-05-25Z")
        with pytest.raises(ValidationError):
            Suspect(**payload)

    def test_bare_z_suffix_with_t_is_accepted(self):
        Suspect(**_minimal_suspect(inferred_release_utc="2026-05-25T06:40:00Z"))


class TestLonLatOrdering:
    """API_CONTRACT.md: "Geometry: GeoJSON, WGS84, longitude first."
    A silently swapped [lat, lon] pair is the single most common bug in
    geospatial code. The validator catches SOME instances of it, not all
    — see the limitation documented on schemas.LonLat. Both the coverage
    and the gap are pinned down here as tests, not left implicit."""

    def test_valid_point_in_the_arabian_sea(self):
        # Kochi is roughly 76 E, 10 N - a real [lon, lat] pair.
        GeoPoint(coordinates=(76.0, 10.0))

    def test_swap_is_caught_when_the_true_longitude_exceeds_90(self):
        # True coordinates: lon=110.0, lat=9.0 (east of our AOI, but a
        # realistic "somewhere in Asia" pair). Written backwards as
        # (lat, lon) = (9.0, 110.0), the second component is 110 - not a
        # valid latitude - so this swap IS caught.
        with pytest.raises(ValidationError):
            GeoPoint(coordinates=(9.0, 110.0))

    def test_swap_within_our_own_aoi_is_not_caught(self):
        # The documented gap, made concrete: true coordinates near Kochi
        # are lon=75.57, lat=9.75. Swapped to (9.75, 75.57), both
        # components independently pass the +/-90 range check (75.57 is a
        # "valid" latitude), so this incorrectly-ordered pair is accepted.
        # This test exists so a future change to the validator that
        # silently narrows or widens this behaviour gets noticed, not so
        # that the behaviour itself is considered acceptable.
        GeoPoint(coordinates=(9.75, 75.57))  # must NOT raise - this is the gap

    def test_polygon_validates_every_ring_point(self):
        with pytest.raises(ValidationError):
            GeoPolygon(
                coordinates=[
                    [(75.0, 9.0), (75.0, 95.0), (76.0, 9.0)]  # 95 is not a valid latitude
                ]
            )

    def test_out_of_range_longitude_is_rejected(self):
        with pytest.raises(ValidationError):
            GeoPoint(coordinates=(200.0, 10.0))
