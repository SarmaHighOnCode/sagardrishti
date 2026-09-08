"""GET /detections, GET /detections/{id}, /suspects, /hindcast, /forecast,
/audit, POST /detections/{id}/evidence.

/suspects is now genuinely scored by packages/sagar_attrib
(see ../attribution.py for exactly what that means and does not mean —
several of its inputs are still fixture placeholders, named individually
there, standing in for M5/lane-KDE/etc). /audit remains fully
fixture-backed — the 214→7 cascade itself is not built yet (docs/
HANDOVER.md task H). Both exercise the two contract rules that matter
most here: every Suspect carries its uncertainty pair, and every
excluded/negative-evidence path is visible rather than hidden
(docs/SCORING_MODEL.md §7).

/hindcast and /forecast return 501 — there is no drift engine (M5) or
raster tiler yet, and the contract is explicit that rasters are served
as COG via TiTiler, never as JSON arrays. Faking either here would mean
inventing a probability field, which is worse than not answering.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from .. import attribution, fixtures
from ..errors import not_found, not_implemented, problem_responses
from ..schemas import AuditTrail, Detection, Page, Suspect

router = APIRouter(prefix="/api/v1/detections", tags=["detections"])


@router.get("", response_model=Page[Detection])
def list_detections(
    scene_id: str | None = None,
    min_confidence: float | None = None,
    limit: int = Query(default=50, le=500),
) -> Page:
    items = list(fixtures.DETECTIONS.values())
    if scene_id is not None:
        items = [d for d in items if d.scene_id == scene_id]
    if min_confidence is not None:
        items = [d for d in items if d.confidence >= min_confidence]
    return Page(items=items[:limit], next_cursor=None)


@router.get("/{detection_id}", response_model=Detection, responses=problem_responses(404))
def get_detection(detection_id: str):
    detection = fixtures.DETECTIONS.get(detection_id)
    if detection is None:
        return not_found(f"no detection with id {detection_id!r}")
    return detection


@router.get(
    "/{detection_id}/suspects", response_model=list[Suspect], responses=problem_responses(404)
)
def get_suspects(detection_id: str):
    if detection_id not in fixtures.DETECTIONS:
        return not_found(f"no detection with id {detection_id!r}")
    return attribution.score_suspects(detection_id)


@router.get("/{detection_id}/hindcast", responses=problem_responses(404, 501))
def get_hindcast(detection_id: str):
    if detection_id not in fixtures.DETECTIONS:
        return not_found(f"no detection with id {detection_id!r}")
    return not_implemented(
        "M5 backward drift ensemble and the COG tile server are not built "
        "yet — see docs/ROADMAP.md Phase 1-2. The eventual response is a "
        "COG URL for the origin probability field, never a JSON array of "
        "raster values."
    )


@router.get("/{detection_id}/forecast", responses=problem_responses(404, 501))
def get_forecast(detection_id: str, hours: int = 48):
    if detection_id not in fixtures.DETECTIONS:
        return not_found(f"no detection with id {detection_id!r}")
    return not_implemented(
        "M5 forward drift ensemble is not built yet — see docs/ROADMAP.md Phase 2."
    )


@router.get("/{detection_id}/audit", response_model=AuditTrail, responses=problem_responses(404))
def get_audit(detection_id: str):
    if detection_id not in fixtures.DETECTIONS:
        return not_found(f"no detection with id {detection_id!r}")
    if fixtures.AUDIT_TRAIL["detection_id"] != detection_id:
        # Only the headline detection has a worked audit trail fixture.
        return {
            "detection_id": detection_id,
            "stages": [],
            "final_candidate_count": 0,
        }
    return fixtures.AUDIT_TRAIL


@router.post("/{detection_id}/evidence", responses=problem_responses(202, 404, 501))
def request_evidence(detection_id: str):
    if detection_id not in fixtures.DETECTIONS:
        return not_found(f"no detection with id {detection_id!r}")
    return not_implemented(
        "M7 evidence dossier generation and the ARQ job queue are not "
        "wired up yet — see docs/ROADMAP.md Phase 2."
    )
