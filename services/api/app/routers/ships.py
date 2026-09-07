"""GET /ships, GET /ships/{id}.

Fixture-backed. size_bucket is always a soft flag here, never used to
filter a vessel out of the list — PRD §7.6. See fixtures.SHIPS for the
one dark, small (likely AIS-exempt) vessel in the demo data.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import fixtures
from ..errors import not_found, problem_responses
from ..schemas import Page, ShipDetection

router = APIRouter(prefix="/api/v1/ships", tags=["ships"])


@router.get("", response_model=Page[ShipDetection])
def list_ships(scene_id: str | None = None) -> Page[ShipDetection]:
    # scene_id accepted per the contract; the fixture set isn't
    # scene-partitioned yet, so it is currently a no-op filter.
    del scene_id
    return Page(items=list(fixtures.SHIPS.values()), next_cursor=None)


@router.get("/{ship_id}", response_model=ShipDetection, responses=problem_responses(404))
def get_ship(ship_id: str):
    ship = fixtures.SHIPS.get(ship_id)
    if ship is None:
        return not_found(f"no ship detection with id {ship_id!r}")
    return ship
