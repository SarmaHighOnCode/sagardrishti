"""GET /scenes, GET /scenes/{id}, POST /scenes/{id}/analyse.

Fixture-backed: SCENE.acquired_utc is fine to be entirely
fixture-computed, but `analyse` is honestly 501 — no worker exists to
process a job. See services/api/app/errors.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from .. import fixtures
from ..errors import not_found, not_implemented, problem_responses
from ..schemas import Page, Scene

router = APIRouter(prefix="/api/v1/scenes", tags=["scenes"])


@router.get("", response_model=Page[Scene])
def list_scenes(
    bbox: str | None = Query(default=None, description="minlon,minlat,maxlon,maxlat"),
    start: str | None = None,
    end: str | None = None,
    sensor: str | None = None,
    limit: int = Query(default=50, le=500),
) -> Page:
    # Single fixture scene. bbox/start/end/sensor filters accepted (per the
    # contract's query params) but not yet meaningfully applied — there is
    # exactly one candidate to filter and it always matches.
    scenes = [fixtures.SCENE]
    if sensor and sensor.lower() not in fixtures.SCENE.sensor.lower():
        scenes = []
    return Page(items=scenes[:limit], next_cursor=None)


@router.get("/{scene_id}", response_model=Scene, responses=problem_responses(404))
def get_scene(scene_id: str):
    if scene_id != fixtures.SCENE.id:
        return not_found(f"no scene with id {scene_id!r}")
    return fixtures.SCENE


@router.post("/{scene_id}/analyse", responses=problem_responses(202, 404, 501))
def analyse_scene(scene_id: str):
    if scene_id != fixtures.SCENE.id:
        return not_found(f"no scene with id {scene_id!r}")
    return not_implemented(
        "M1-M7 pipeline and the ARQ job queue are not wired up yet — "
        "see docs/ROADMAP.md Phase 1. Accepting this request would create "
        "a job id nothing will ever process."
    )
