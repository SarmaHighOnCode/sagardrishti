"""Coordinate handling, CRS constants and geodesic helpers.

No GDAL, no shapely, no pyproj. Those live in the geo/micromamba
environment and belong to the packages that actually do geometry work
(sagar_sar, sagar_drift). What lives here is the small set of primitives
that every package — including the API, which runs in a different
environment entirely — needs to agree on: what a coordinate is, which
way round it goes, and how far apart two of them are.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from .units import METRES_PER_NAUTICAL_MILE

#: WGS84. Every coordinate in this system is EPSG:4326 unless a module
#: says otherwise in its own docstring, and none currently do.
CRS_WGS84 = "EPSG:4326"

#: Mean Earth radius (IUGG), metres. Used for haversine distance.
EARTH_RADIUS_M = 6_371_008.8


class LonLat(NamedTuple):
    """A WGS84 coordinate, longitude first.

    Longitude first because that is GeoJSON's order (RFC 7946 §3.1.1) and
    the API contract's stated convention, and being consistent with the
    wire format everywhere is worth more than matching the "lat, lon"
    order humans say out loud.

    A NamedTuple rather than a Pydantic model on purpose: these are
    constructed in tight loops (per-particle, per-AIS-ping) where model
    validation overhead is real. Validation happens at boundaries via
    `validate_lonlat`, not on every construction.
    """

    lon: float
    lat: float


def validate_lonlat(lon: float, lat: float) -> LonLat:
    """Range-check a coordinate and return it.

    Catches a swapped pair ONLY when the true longitude exceeds ±90, so
    the swapped value falls outside valid latitude range. Within our own
    Arabian Sea AOI (roughly 68–78°E, 8–15°N) both components are
    individually valid latitudes, so a swap there passes silently — this
    is a genuine, unavoidable gap in any pure range check, documented
    here and mirrored in services/api/app/schemas.py's LonLat. Use
    `in_bbox` against a known AOI when you need to catch that case.
    """
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"longitude out of range [-180, 180]: {lon}")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(
            f"latitude out of range [-90, 90]: {lat} — "
            "this usually means the pair was written [lat, lon] by mistake"
        )
    return LonLat(lon, lat)


class BBox(NamedTuple):
    """An axis-aligned bounding box, WGS84 degrees.

    Does not handle antimeridian crossing (min_lon > max_lon). Our AOIs
    are the Arabian Sea and Bay of Bengal, neither of which comes near
    180°, so supporting it would be untested code guarding against a case
    that cannot currently arise. `from_bounds` raises rather than silently
    producing a box that spans the wrong 340 degrees.
    """

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @classmethod
    def from_bounds(cls, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> BBox:
        if min_lon > max_lon:
            raise ValueError(
                f"min_lon {min_lon} > max_lon {max_lon}: antimeridian-crossing boxes "
                "are not supported (and no SAGARDRISHTI AOI needs one)"
            )
        if min_lat > max_lat:
            raise ValueError(f"min_lat {min_lat} > max_lat {max_lat}")
        validate_lonlat(min_lon, min_lat)
        validate_lonlat(max_lon, max_lat)
        return cls(min_lon, min_lat, max_lon, max_lat)

    @classmethod
    def parse(cls, text: str) -> BBox:
        """Parse the `?bbox=minlon,minlat,maxlon,maxlat` query form used
        by the API contract."""
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 4:
            raise ValueError(
                f"bbox must be 'minlon,minlat,maxlon,maxlat' (4 values), got {len(parts)}: {text!r}"
            )
        try:
            nums = [float(p) for p in parts]
        except ValueError as exc:
            raise ValueError(f"bbox components must be numbers: {text!r}") from exc
        return cls.from_bounds(*nums)


def in_bbox(point: LonLat, bbox: BBox) -> bool:
    return bbox.min_lon <= point.lon <= bbox.max_lon and bbox.min_lat <= point.lat <= bbox.max_lat


def haversine_m(a: LonLat, b: LonLat) -> float:
    """Great-circle distance in metres.

    Haversine on a spherical Earth: sub-0.5% error against the WGS84
    ellipsoid, which is far below the ~8 km resolution of the ocean
    current fields that dominate our error budget (docs/PRD.md §6.5). A
    geodesic solution would be more precise and would need pyproj, which
    this package deliberately does not depend on.
    """
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def haversine_nm(a: LonLat, b: LonLat) -> float:
    """Distance in nautical miles — the unit maritime work actually uses,
    and the one the AIS coverage threshold (~40–75 nm) is expressed in."""
    return haversine_m(a, b) / METRES_PER_NAUTICAL_MILE


def initial_bearing_deg(a: LonLat, b: LonLat) -> float:
    """Initial great-circle bearing from `a` to `b`, degrees in [0, 360).

    "Initial" matters: along a great circle the bearing changes
    continuously, so this is the heading at `a`, not an average. Over the
    short hops between consecutive AIS pings the difference is
    negligible; over a long track segment it is not.
    """
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlon = math.radians(b.lon - a.lon)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360.0


def implied_speed_knots(a: LonLat, b: LonLat, seconds: float) -> float:
    """Speed implied by moving from `a` to `b` in `seconds`.

    This is the backbone of the AIS "teleport" data-quality check
    (docs/SCORING_MODEL.md §2.1(a)): a vessel reporting positions 50 nm
    apart 30 seconds apart did not travel at 6000 knots, it emitted bad
    data, and that record must be marked unreliable rather than fed to
    the scoring model.

    Raises on non-positive elapsed time — two positions with the same
    timestamp imply an infinite speed, which is a data defect to surface,
    not a float('inf') to propagate into a suspicion score.
    """
    if seconds <= 0:
        raise ValueError(f"elapsed seconds must be positive, got {seconds}")
    return haversine_nm(a, b) / (seconds / 3600.0)
