# `db` — Schema and Migrations

PostgreSQL 16 + PostGIS 3.4 + TimescaleDB.

```
schema/      table definitions, indexes, views
migrations/  ordered, forward-only
seeds/       reference data — coastline, eco-zones, ports
```

Image: `timescale/timescaledb-ha:pg16` (PostGIS included).

## Tables

| Table | Type | Notes |
|---|---|---|
| `scenes` | regular + PostGIS | Products, footprints, hashes |
| `detections` | regular + PostGIS | Slick polygons, confidence, **penalty log as JSONB** |
| `detection_attributes` | regular | M3 output |
| `ship_detections` | regular + PostGIS | CFAR targets, dark-vessel flag, size bucket |
| **`ais_positions`** | **hypertable** | Millions of rows. **Written by Go, read by Python** |
| `ais_static` | regular | Type 5/24, latest-per-MMSI view |
| **`ais_baseline_profiles`** | regular | **Per-vessel gap behaviour, cached.** Backs the gap anomaly factor |
| `drift_runs` | regular | Config, forcing versions, ensemble parameters |
| `drift_particles` | hypertable or Parquet | Large — Parquet on object store if rows get uncomfortable |
| `suspects` | regular | Ranked candidates, **factor contributions as JSONB** |
| `evidence_dossiers` | regular | Manifest, hashes, signature |
| `jobs` | regular | ARQ state mirror for the UI |

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
