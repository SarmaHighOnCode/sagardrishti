"""GET /ais/tracks, GET /ais/vessels/{mmsi}.

Fixture-backed for now. The eventual real implementation queries
ais_positions (db/schema/001_ais_positions.sql) directly — same columns
as AisTrackPoint below, which is deliberate: swapping the fixture for a
real query should be close to a drop-in replacement of this module's
body, not a schema redesign.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from .. import fixtures
from ..errors import not_found
from ..schemas import Page, VesselStatic

router = APIRouter(prefix="/api/v1/ais", tags=["ais"])


@router.get("/tracks", response_model=Page)
def list_tracks(
    bbox: str | None = Query(default=None, description="minlon,minlat,maxlon,maxlat"),
    start: str | None = None,
    end: str | None = None,
    mmsi: str | None = None,
    limit: int = Query(default=50, le=500),
) -> Page:
    tracks = list(fixtures.AIS_TRACKS.values())
    if mmsi is not None:
        tracks = [t for t in tracks if t.mmsi == mmsi]
    return Page(items=tracks[:limit], next_cursor=None)


@router.get("/vessels/{mmsi}", response_model=VesselStatic, responses={404: {}})
def get_vessel(mmsi: str):
    vessel = fixtures.VESSELS.get(mmsi)
    if vessel is None:
        return not_found(
            f"no static/voyage data recorded for MMSI {mmsi!r} — this is "
            "distinct from a vessel that exists but lacks a baseline gap "
            "profile, which is represented by baseline_gap_profile=null, "
            "not a 404"
        )
    return vessel
