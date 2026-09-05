# `db` — Schema and Migrations

PostgreSQL 16 + PostGIS 3.4 + TimescaleDB.

```
schema/      table definitions, indexes, views
migrations/  ordered, forward-only
seeds/       reference data — coastline, eco-zones, ports
```

Image: `timescale/timescaledb-ha:pg16` (PostGIS included).

## Tables

| Table | Migration | Type | Notes |
|---|---|---|---|
| `scenes` | `002` | regular + PostGIS | Products, footprints, hashes |
| `detections` | `002` | regular + PostGIS | Slick polygons, confidence, **penalty log as JSONB** |
| `detection_attributes` | `002` | regular | M3 output, 1:1 with `detections` |
| `ship_detections` | `002` | regular + PostGIS | CFAR targets, dark-vessel flag, size bucket. `ais_match` is a bare MMSI, deliberately **not** a foreign key — see the file's own comment on why |
| **`ais_positions`** | `001` | **hypertable** | Millions of rows. **Written by Go, read by Python** |
| `ais_static` | `001` | regular | Type 5/24, latest-per-MMSI view |
| **`ais_baseline_profiles`** | `001` | regular | **Per-vessel gap behaviour, cached.** Backs the gap anomaly factor |
| `drift_runs` | `002` | regular | Config, forcing versions, ensemble parameters, as JSONB |
| `drift_particles` | *(not yet added)* | hypertable or Parquet | Large — this is an M5 implementation decision, not a schema decision to make before the ensemble code exists. Add it once M5 is being built and the real row-count shape is known |
| `suspects` | `002` | regular | `(detection_id, mmsi)` primary key. Ranked candidates, **factor contributions as JSONB, including negative ones** |
| `evidence_dossiers` | `002` | regular | Manifest, hashes, signature. Regenerable — `is_current` marks the active one per detection, superseded dossiers are kept, never overwritten |
| `jobs` | `002` | regular | ARQ state mirror for the UI. `stage` is a named stage, never a percentage |

**Identifiers are app-generated strings, not `SERIAL`/`UUID`** — `det_...`, `shp_...`, `job_...`, type-prefixed, matching the worked examples in `docs/api/API_CONTRACT.md` (`"det_01H..."`). `scenes.id` is the product's own identifier (e.g. `S1C_IW_GRDH_1SDV_20260525T064012`), already globally unique.

**Column names and JSONB shapes mirror `services/api/app/schemas.py` closely on purpose** — the API's fixtures are meant to become close to a drop-in read of these tables, not a redesign. If you rename a field on one side, rename it on the other, or they will quietly drift apart the same way `ais_baseline_profiles`' `median_gap_seconds`/`p95_gap_seconds` almost did against an API layer that had independently invented `typical_gap_minutes_p50/p95` — caught only because someone checked the merged schema before writing fixtures against it, not because anything would have failed loudly.

**Verification status of `002`, honestly:** parsed cleanly against PostgreSQL's actual grammar (`pglast`/`libpg_query`) — zero syntax errors across 22 statements — but that does not exercise PostGIS/TimescaleDB semantics (the `GEOMETRY` type, `create_hypertable()`) or prove the constraints are satisfiable. **Apply it to a live Postgres and confirm before relying on it**, the same way `001` was verified live in PR #1.

## Why TimescaleDB for AIS

Millions of time-ordered rows, queried almost exclusively as *"all positions in this bbox during this window."* That is precisely the hypertable case — automatic time partitioning, chunk exclusion, compression on older chunks.

Indexes on `(mmsi, time)` and a GIST spatial index on position.

## `ais_baseline_profiles`

Materialises each vessel's normal gap behaviour so the scoring model can ask *"is this gap unusual **for this vessel**?"* rather than *"is there a gap?"*

Without it, the gap factor measures transponder quality rather than behaviour, and systematically incriminates small craft with cheap equipment. See [`SCORING_MODEL.md`](../docs/SCORING_MODEL.md) section 2.1.

Refreshed on a schedule; stale profiles are marked low-confidence rather than silently used.

## Data quality flags

`ais_positions` carries a `data_quality` column. Records failing the pre-filter — MMSI 0, position at (0,0), impossible implied speed, garbled static — are marked `unreliable`.

**Marked, not deleted.** They stay auditable, and scoring queries exclude them explicitly. They must never influence a score in either direction.

## Migrations

Forward-only, ordered, checked into git. Schema changes after **15 October** need integration-lead sign-off, same as the API contract.
