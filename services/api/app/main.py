"""SAGARDRISHTI API - hello-world slice.

The real surface is docs/api/API_CONTRACT.md (frozen 15 October). This is
deliberately just enough to prove the compose stack - db, redis, api - is
wired correctly end to end: see roadmap Week 1, "Compose stack up: PostGIS
+ Redis + a hello-world API".

The API does no science. Anything taking more than a second belongs in
services/worker, not here.
"""

from __future__ import annotations

import os

import psycopg
import redis
from fastapi import FastAPI

from .routers import ais, detections, jobs, scenes, ships

app = FastAPI(
    title="SAGARDRISHTI API",
    version="0.1.0",
    docs_url="/docs",
)

# docs/api/API_CONTRACT.md — DRAFT until 15 October 2026, then FROZEN.
# See each router module's docstring for what is fixture-backed today
# versus honestly 501 pending a pipeline that doesn't exist yet.
app.include_router(scenes.router)
app.include_router(detections.router)
app.include_router(ais.router)
app.include_router(ships.router)
app.include_router(jobs.router)


@app.get("/api/v1/")
def root() -> dict:
    return {"service": "sagardrishti-api", "status": "ok"}


@app.get("/health")
def health() -> dict:
    """Not part of the frozen contract - an ops endpoint, checked by the
    compose healthcheck and by anyone debugging `make up`."""
    checks: dict[str, str] = {}

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        checks["database"] = "DATABASE_URL not set"
    else:
        try:
            with psycopg.connect(database_url, connect_timeout=3) as conn:
                conn.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - a health check reports, never raises
            checks["database"] = f"error: {exc}"

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        checks["redis"] = "REDIS_URL not set"
    else:
        try:
            redis.from_url(redis_url, socket_connect_timeout=3).ping()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}
