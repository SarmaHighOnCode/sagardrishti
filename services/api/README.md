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

## Uncertainty is enforced in the schema

Pydantic models reject an inferred value without its interval. `slick_age_hours` without `slick_age_ci` fails validation. Product principle 2 is structural, not a matter of discipline.

## Environment

The **`sagar-api`** uv environment (PyPI), not the geo environment. It must not import PyTorch or GDAL — those belong to the worker. See [`DEVELOPMENT.md`](../../docs/DEVELOPMENT.md) section 2.
