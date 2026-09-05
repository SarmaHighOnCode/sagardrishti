"""RFC 7807 problem+json responses.

docs/api/API_CONTRACT.md: "Errors: RFC 7807 problem+json". FastAPI's
default error body (`{"detail": "..."}`) is not that shape, so every
non-2xx response in this service goes through `problem()` rather than a
bare `raise HTTPException`, which is what would silently reintroduce the
default shape and break this rule the first time someone forgets.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

from .schemas import ProblemDetail

PROBLEM_MEDIA_TYPE = "application/problem+json"


def problem(status: int, title: str, detail: str | None = None) -> JSONResponse:
    body = ProblemDetail(title=title, status=status, detail=detail)
    return JSONResponse(
        status_code=status,
        content=body.model_dump(exclude_none=True),
        media_type=PROBLEM_MEDIA_TYPE,
    )


def not_found(detail: str) -> JSONResponse:
    return problem(404, "Not Found", detail)


def not_implemented(detail: str) -> JSONResponse:
    """For contract endpoints whose backing pipeline does not exist yet
    (M1-M7, the raster tiler, the ARQ job queue). Returning a fake 202 or
    a fabricated result here would be worse than an honest 501 — nothing
    would ever process a job this API pretended to accept. See
    docs/ROADMAP.md for what each phase actually delivers."""
    return problem(501, "Not Implemented", detail)
