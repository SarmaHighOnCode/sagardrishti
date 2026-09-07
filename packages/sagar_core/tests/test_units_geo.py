"""Unit and geometry conversions.

These are boring functions guarding an unglamorous failure mode: a
constant-factor error that produces plausible numbers rather than a
crash. Worth pinning down precisely, because nothing downstream will
notice if one is wrong.
"""

from __future__ import annotations

import math

import pytest
from sagar_core.geo import (
    BBox,
    LonLat,
    haversine_m,
    haversine_nm,
    implied_speed_knots,
    in_bbox,
    initial_bearing_deg,
    validate_lonlat,
)
from sagar_core.units import (
    bearing_difference_deg,
    db_to_power_ratio,
    knots_to_ms,
    m2_to_km2,
    ms_to_knots,
    normalise_bearing_deg,
    power_ratio_to_db,
)


class TestSpeed:
    def test_one_knot_is_the_defined_value(self):
        # 1852 m / 3600 s, exactly, by definition of the nautical mile.
        assert knots_to_ms(1.0) == pytest.approx(0.5144444, abs=1e-6)

    def test_round_trip(self):
        assert ms_to_knots(knots_to_ms(12.5)) == pytest.approx(12.5)

    def test_typical_merchant_speed(self):
        # 12 kn is an unremarkable transit speed; ~6.2 m/s.
        assert knots_to_ms(12.0) == pytest.approx(6.173, abs=1e-3)


class TestBearings:
    def test_normalise_folds_negative(self):
        assert normalise_bearing_deg(-90.0) == 270.0

    def test_normalise_folds_over_360(self):
        assert normalise_bearing_deg(450.0) == 90.0

    def test_difference_across_north_is_small(self):
        # The case naive subtraction gets wrong: 355 vs 5 is 10 apart,
        # not 350. Course alignment scoring depends on this.
        assert bearing_difference_deg(355.0, 5.0) == pytest.approx(10.0)

    def test_difference_is_symmetric(self):
        assert bearing_difference_deg(30.0, 200.0) == pytest.approx(
            bearing_difference_deg(200.0, 30.0)
        )

    def test_difference_never_exceeds_180(self):
        for a in range(0, 360, 17):
            for b in range(0, 360, 23):
                assert 0.0 <= bearing_difference_deg(a, b) <= 180.0

    def test_opposite_headings(self):
        assert bearing_difference_deg(0.0, 180.0) == pytest.approx(180.0)


class TestDecibels:
    def test_power_ratio_uses_factor_ten_not_twenty(self):
        # 10*log10(100) = 20 dB. The amplitude form (20*log10) would give
        # 40 and would double every damping figure we report.
        assert power_ratio_to_db(100.0) == pytest.approx(20.0)

    def test_round_trip(self):
        assert db_to_power_ratio(power_ratio_to_db(8.5)) == pytest.approx(8.5)

    def test_unity_ratio_is_zero_db(self):
        assert power_ratio_to_db(1.0) == pytest.approx(0.0)

    def test_non_positive_ratio_raises_rather_than_returning_nan(self):
        with pytest.raises(ValueError):
            power_ratio_to_db(0.0)
        with pytest.raises(ValueError):
            power_ratio_to_db(-1.0)


class TestArea:
    def test_m2_to_km2_is_one_million_not_one_thousand(self):
        assert m2_to_km2(1_000_000.0) == pytest.approx(1.0)

    def test_realistic_slick(self):
        # 12.43 km^2, the headline fixture slick.
        assert m2_to_km2(12_430_000.0) == pytest.approx(12.43)


class TestCoordinateValidation:
    def test_accepts_a_real_arabian_sea_position(self):
        assert validate_lonlat(75.57, 9.75) == LonLat(75.57, 9.75)

    def test_rejects_out_of_range_latitude(self):
        with pytest.raises(ValueError, match="latitude"):
            validate_lonlat(75.0, 95.0)

    def test_rejects_out_of_range_longitude(self):
        with pytest.raises(ValueError, match="longitude"):
            validate_lonlat(200.0, 9.0)

    def test_documented_gap_in_aoi_swap_detection(self):
        # Mirrors the API-layer test: a swap inside our own AOI passes,
        # because both components are individually valid. Pinned so the
        # limitation stays visible rather than being assumed closed.
        assert validate_lonlat(9.75, 75.57) == LonLat(9.75, 75.57)


class TestDistance:
    def test_known_separation_one_degree_of_latitude(self):
        # One degree of latitude is ~60 nautical miles anywhere on Earth.
        d = haversine_nm(LonLat(75.0, 9.0), LonLat(75.0, 10.0))
        assert d == pytest.approx(60.0, rel=0.01)

    def test_zero_distance(self):
        p = LonLat(75.0, 9.0)
        assert haversine_m(p, p) == pytest.approx(0.0)

    def test_symmetry(self):
        a, b = LonLat(75.0, 9.0), LonLat(76.0, 10.0)
        assert haversine_m(a, b) == pytest.approx(haversine_m(b, a))


class TestBearingBetweenPoints:
    def test_due_north(self):
        assert initial_bearing_deg(LonLat(75.0, 9.0), LonLat(75.0, 10.0)) == pytest.approx(
            0.0, abs=1e-6
        )

    def test_due_east(self):
        # Near the equator, due east is ~90 degrees.
        b = initial_bearing_deg(LonLat(75.0, 0.0), LonLat(76.0, 0.0))
        assert b == pytest.approx(90.0, abs=1e-6)

    def test_always_in_range(self):
        b = initial_bearing_deg(LonLat(75.0, 10.0), LonLat(74.0, 9.0))
        assert 0.0 <= b < 360.0


class TestImpliedSpeed:
    def test_realistic_transit_is_plausible(self):
        # 6 nm in 30 minutes = 12 knots.
        a = LonLat(75.0, 9.0)
        b = LonLat(75.0, 9.1)  # ~6 nm north
        speed = implied_speed_knots(a, b, seconds=1800)
        assert speed == pytest.approx(12.0, rel=0.02)

    def test_teleport_is_detectable(self):
        """The data-quality case: 50 nm in 30 seconds is not a vessel."""
        a = LonLat(75.0, 9.0)
        b = LonLat(75.0, 9.833)  # ~50 nm north
        speed = implied_speed_knots(a, b, seconds=30)
        assert speed > 1000  # absurd, and must be flagged upstream

    def test_zero_elapsed_raises_rather_than_returning_inf(self):
        with pytest.raises(ValueError):
            implied_speed_knots(LonLat(75.0, 9.0), LonLat(75.1, 9.1), seconds=0)


class TestBBox:
    def test_parses_the_api_query_form(self):
        box = BBox.parse("68.0,8.0,78.0,15.0")
        assert box == BBox(68.0, 8.0, 78.0, 15.0)

    def test_rejects_wrong_component_count(self):
        with pytest.raises(ValueError, match="4 values"):
            BBox.parse("68.0,8.0,78.0")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError, match="numbers"):
            BBox.parse("68.0,8.0,78.0,north")

    def test_rejects_antimeridian_crossing_explicitly(self):
        with pytest.raises(ValueError, match="antimeridian"):
            BBox.from_bounds(179.0, 8.0, -179.0, 15.0)

    def test_containment(self):
        arabian_sea = BBox.parse("68.0,8.0,78.0,15.0")
        assert in_bbox(LonLat(75.57, 9.75), arabian_sea)
        assert not in_bbox(LonLat(88.0, 20.0), arabian_sea)  # Bay of Bengal

    def test_boundary_is_inclusive(self):
        box = BBox.parse("68.0,8.0,78.0,15.0")
        assert in_bbox(LonLat(68.0, 8.0), box)
        assert in_bbox(LonLat(78.0, 15.0), box)


def test_no_heavy_geospatial_imports():
    """sagar_core must stay importable from the API environment.

    If someone adds numpy/shapely/pyproj here, the API service silently
    acquires a dependency on the geospatial stack that
    docs/DEVELOPMENT.md §2 deliberately keeps separate — and it would
    surface as a confusing container build failure, not an obvious one.

    Runs in a SUBPROCESS for real isolation. Inspecting this process's
    own sys.modules would prove nothing: pytest and the sibling API
    tests have already imported plenty, so a forbidden module could be
    present (or absent) for reasons unrelated to sagar_core.
    """
    import subprocess
    import sys
    from pathlib import Path

    packages_dir = Path(__file__).resolve().parents[2]
    probe = (
        f"import sys; sys.path.insert(0, r'{packages_dir}');"
        "import sagar_core;"
        "print(','.join(sorted({m.split('.')[0] for m in sys.modules})))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"importing sagar_core failed:\n{result.stderr}"

    imported = set(result.stdout.strip().split(","))
    forbidden = {"numpy", "shapely", "pyproj", "rasterio", "xarray", "torch", "geopandas"}
    leaked = imported & forbidden
    assert not leaked, (
        f"sagar_core must stay dependency-light but pulled in: {sorted(leaked)}. "
        "Heavy geometry belongs in sagar_sar/sagar_drift, not the shared base."
    )


def test_earth_radius_is_sane():
    from sagar_core.geo import EARTH_RADIUS_M

    # Mean Earth radius, ~6371 km. Guards against a units slip in the
    # constant itself, which would scale every distance in the system.
    assert 6_300_000 < EARTH_RADIUS_M < 6_400_000
    assert math.isfinite(EARTH_RADIUS_M)
