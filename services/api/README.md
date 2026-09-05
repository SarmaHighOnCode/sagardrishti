# `api` — FastAPI

REST and SSE surface for the operator console.

## Responsibility

Read from PostGIS, enqueue jobs to Redis, stream job progress. **The API does no science.** Anything taking more than a second goes to the worker.

## Contract

[`docs/api/API_CONTRACT.md`](../../docs/api/API_CONTRACT.md). **FROZEN 15 October** — after that, breaking changes need the integration lead's sign-off.

Live OpenAPI docs at `/docs` — worth showing in the demo.

## Long jobs

```
POST /api/v1/scenes/{id}/analyse   -> 202 { job_id }
GET  /api/v1/jobs/{id}/events      -> SSE
```

Progress reports **named stages**, not percentages. *"Advecting 50 vessels x 96 release times"* tells an analyst what is happening; *"63%"* does not.

**Not built yet — both return `501` today.** No worker or ARQ queue exists to process a job, so accepting one and handing back a `job_id` nothing will ever advance would be a fabricated result. See `app/errors.py`'s `not_implemented()`.

## What's implemented today

Every endpoint in `docs/api/API_CONTRACT.md` exists and returns the documented shape — but the pipeline behind it doesn't yet, so responses fall into two categories:

| Category | Endpoints | Backed by |
|---|---|---|
| **Fixture-backed, fully real** | scenes, detections (+ suspects, audit), ais/tracks, ais/vessels, ships | `app/fixtures.py` — labelled `SYNTHETIC`, identifier-consistent with `web/src/lib/fixtures.ts` so the console's demo data doesn't change shape when it switches from local fixtures to this API |
| **Honestly `501`** | `analyse`, `hindcast`, `forecast`, `evidence`, `jobs/*` | Nothing — M1–M7, the raster tiler and the job queue don't exist yet. Each 501 names the missing piece and the roadmap phase that builds it |
| **Honestly `404`** | any unknown id, and every `jobs/{id}` lookup | `jobs/{id}` is a genuine 404, not a 501 — the endpoint works, its store is just permanently empty until `services/worker` exists |

All errors are RFC 7807 `application/problem+json` (`app/errors.py`), per the contract — never FastAPI's default `{"detail": "..."}` shape.

## Uncertainty is enforced in the schema

Pydantic models reject an inferred value without its interval. `slick_age_hours` without `slick_age_ci` fails validation — `app/schemas.py`'s `Suspect` model has no default for either field, so constructing one without both is a `ValidationError`, not a lint warning. Product principle 2 is structural, not a matter of discipline.

The same file also validates GeoJSON coordinate order (`LonLat`) and timestamp format (`UtcTimestamp`) at the schema boundary — see the module docstring for what each does and does not catch.

## Tests

```bash
cd services/api
uv venv --python 3.11 .venv && uv pip install -p .venv -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest tests/ -v      # or .venv/bin/python on Linux/macOS
```

`tests/test_schemas.py` exercises the contract rules directly against the Pydantic models (no HTTP layer). `tests/test_routes.py` hits every endpoint through a real `TestClient`, including the exact rejection-reasoning example from `API_CONTRACT.md` and the negative-contribution suspect factor.

## Environment

The **`sagar-api`** uv environment (PyPI), not the geo environment. It must not import PyTorch or GDAL — those belong to the worker. See [`DEVELOPMENT.md`](../../docs/DEVELOPMENT.md) section 2.
