"""Pydantic models for docs/api/API_CONTRACT.md.

Status: DRAFT until 15 October 2026, then FROZEN (see the contract doc).
These models ARE the contract in enforceable form — if a shape here
diverges from the markdown, one of the two is wrong and it must be fixed
immediately, not "reconciled later". After the freeze date, changing a
field name or removing a field here is the kind of change the contract
says needs the integration lead's sign-off and a version bump.

Two rules from the contract are enforced structurally here, not left as
convention for callers to remember:

  1. "Any field representing an inferred quantity carries its uncertainty
     in the same object... a bare slick_age_hours with no interval is a
     schema violation, not a convenience." Fields that come in
     value/interval pairs (slick_age_hours + slick_age_ci,
     inferred_release_utc + inferred_release_ci_minutes) are both
     required, with no default — you cannot construct a Suspect that
     drops one but keeps the other.

  2. "Geometry: GeoJSON, WGS84, longitude first" and "Time: ISO 8601 UTC
     with explicit Z" are validated on every coordinate pair and every
     timestamp field via LonLat and UtcTimestamp below, not just
     documented. The lon/lat check in particular catches the single most
     common bug in geospatial code: a silently swapped [lat, lon] pair.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field

from .format import is_utc_z

# --------------------------------------------------------------------------
# Shared primitives
# --------------------------------------------------------------------------


def _check_utc_z(v: str) -> str:
    if not is_utc_z(v):
        raise ValueError(f"timestamp must be ISO 8601 UTC with an explicit trailing Z, got {v!r}")
    return v


UtcTimestamp = Annotated[str, AfterValidator(_check_utc_z)]
"""ISO 8601 UTC, e.g. "2026-05-25T06:40:00Z". See format.is_utc_z."""


def _check_lonlat(pair: tuple[float, float]) -> tuple[float, float]:
    lon, lat = pair
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"expected [lon, lat] with lon in [-180, 180], got lon={lon}")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(
            f"expected [lon, lat] with lat in [-90, 90], got lat={lat} — "
            "this usually means the pair was written [lat, lon] by mistake"
        )
    return pair


LonLat = Annotated[tuple[float, float], AfterValidator(_check_lonlat)]
"""A single [longitude, latitude] pair, WGS84. Never [lat, lon].

Known limitation, stated plainly rather than left for someone to discover
by surprise: this only catches a swap when the true longitude's absolute
value exceeds 90 (so the swapped value fails the latitude range check).
For coordinates entirely within +/-90 in both components — which includes
most of our own Arabian Sea AOI, e.g. (75.57, 9.75) swapped to (9.75,
75.57) — both components remain individually "valid" and the swap is
silently accepted. This is a real gap, not a hypothetical one, and no
cheap fix exists: distinguishing an in-range swap requires either a
plausibility check against a known AOI bounding box, or trusting the
caller. See test_schemas.py::TestLonLatOrdering for both the coverage
this provides and the specific case it does not catch, encoded as tests
so the gap stays visible rather than being quietly assumed closed."""


class GeoPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: LonLat


class GeoPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[LonLat]]


class ProblemDetail(BaseModel):
    """RFC 7807. Served with media type application/problem+json — see
    routers/errors.py, which is the only place that constructs these."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None


class Page(BaseModel):
    """Generic list envelope. `?limit=` and `?cursor=` per the contract;
    with the small fixture datasets currently backing every list endpoint
    there is never a second page, so next_cursor is always null — this
    will start being exercised once a real store replaces the fixtures."""

    items: list[Any]
    next_cursor: str | None = None


# --------------------------------------------------------------------------
# Scenes
# --------------------------------------------------------------------------


class Scene(BaseModel):
    """Not pinned by a literal example in the contract doc (only the
    endpoint list is). Kept intentionally small and aligned with the
    provenance fields the StatusStrip component and the evidence dossier
    both need — see docs/DESIGN_SYSTEM.md §6.5."""

    id: str
    sensor: str
    acquired_utc: UtcTimestamp
    footprint: GeoPolygon
    product_hash: str
    status: Literal["ingested", "preprocessing", "analysed"]


# --------------------------------------------------------------------------
# Detections
# --------------------------------------------------------------------------


class Penalty(BaseModel):
    check: str
    delta: float
    reason: str
    evidence: dict[str, Any] | None = None


class DetectionAttributes(BaseModel):
    area_km2: float
    major_axis_bearing_deg: float
    damping_ratio_db: float
    edge_sharpness: float
    # Provisional vocabulary — PRD §7.5 names "thin sheen / thick film" but
    # M3 hasn't shipped a formal thickness-class taxonomy yet. Narrow this
    # if/when M3 defines more classes; do not widen silently.
    thickness_class: Literal["sheen", "thick_film"]


class Detection(BaseModel):
    id: str
    scene_id: str
    geometry: GeoPolygon
    confidence: float
    confidence_raw: float
    classification: Literal["oil", "look_alike"]
    attributes: DetectionAttributes
    penalties: list[Penalty]


# --------------------------------------------------------------------------
# Suspects
# --------------------------------------------------------------------------


class SuspectFactor(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float
    confidence: Literal["high", "medium", "low"]
    # Present on factors whose raw value would be misleading without it —
    # e.g. ais_gap_anomaly needs to say what baseline it was measured
    # against. See docs/SCORING_MODEL.md §2.1.
    note: str | None = None


class DataQualitySummary(BaseModel):
    records_used: int
    records_excluded: int
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)


class Suspect(BaseModel):
    rank: int
    mmsi: str
    imo: str | None = None
    vessel_name: str
    vessel_type: str
    posterior: float
    calibrated: bool

    # Required together: the release-time estimate without its confidence
    # interval is exactly the "bare point estimate" the contract forbids.
    inferred_release_utc: UtcTimestamp
    inferred_release_ci_minutes: float

    # Required together, same reason. Age is INFERRED (see ADR 0001 / PRD
    # §2.5) — it is never valid to report it without the band that comes
    # from the drift ensemble spread.
    slick_age_hours: float
    slick_age_ci: tuple[float, float]

    # Every factor is always listed, including negative (exculpatory)
    # contributions — never filtered down to "the ones that look good".
    factors: list[SuspectFactor]
    data_quality: DataQualitySummary


# --------------------------------------------------------------------------
# AIS and ships
# --------------------------------------------------------------------------


class AisTrackPoint(BaseModel):
    time_utc: UtcTimestamp
    lat: float
    lon: float
    sog_knots: float | None = None
    cog_degrees: float | None = None
    # Mirrors ais_positions.data_quality / quality_reason (db/schema/
    # 001_ais_positions.sql) — marked, never dropped. See SCORING_MODEL §2.1(a).
    data_quality: Literal["ok", "unreliable"] = "ok"
    quality_reason: str | None = None


class AisTrack(BaseModel):
    mmsi: str
    vessel_name: str | None = None
    points: list[AisTrackPoint]


class BaselineGapProfile(BaseModel):
    """The per-vessel baseline that SCORING_MODEL §2.1(b) requires before
    a gap can be judged suspicious at all. `has_sufficient_history=False`
    is the signal the UI uses to mark the AIS-gap factor low-confidence —
    a vessel with no history is unknown, never silently treated as
    average. See docs/SCORING_MODEL.md §5."""

    computed_from_positions: int
    typical_gap_minutes_p50: float
    typical_gap_minutes_p95: float
    has_sufficient_history: bool


class VesselStatic(BaseModel):
    mmsi: str
    imo: str | None = None
    vessel_name: str | None = None
    vessel_type: str | None = None
    # None when the vessel has no recorded history — see BaselineGapProfile.
    baseline_gap_profile: BaselineGapProfile | None = None


class ShipDetection(BaseModel):
    id: str
    position: GeoPoint
    dark_vessel: bool
    # A soft flag for analyst context, never a filter — PRD §7.6. Many
    # small craft are legally exempt from carrying AIS; a dark small
    # vessel is not automatically an evader.
    size_bucket: Literal["small", "medium", "large"]
    size_note: str
    estimated_length_m: tuple[float, float]
    heading_deg: float | None = None
    ais_match: str | None = None  # MMSI, or null when unmatched (dark)
