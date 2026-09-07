"""GET /jobs/{id}, GET /jobs/{id}/events.

No job store exists yet — every endpoint that would create a job
(POST /scenes/{id}/analyse, POST /detections/{id}/evidence) currently
returns 501, so no job id has ever been issued. A lookup here is
therefore always a genuine 404, not a stand-in for "not implemented":
the endpoint IS implemented, its backing store is just permanently
empty until services/worker and Redis/ARQ are wired up.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..errors import not_found, problem_responses

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

_NO_JOB_STORE = (
    "no job store is wired up yet (services/worker + Redis/ARQ — see "
    "docs/ROADMAP.md Phase 1), so no job id has ever been issued"
)


@router.get("/{job_id}", responses=problem_responses(404))
def get_job(job_id: str):
    return not_found(f"job {job_id!r} not found: {_NO_JOB_STORE}")


@router.get("/{job_id}/events", responses=problem_responses(404))
def get_job_events(job_id: str):
    # A real implementation streams text/event-stream; there is nothing to
    # stream, so this is a plain problem+json response, not an opened and
    # immediately closed SSE connection.
    return not_found(f"job {job_id!r} not found: {_NO_JOB_STORE}")
