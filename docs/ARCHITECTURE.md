# Architecture

How SAGARDRISHTI is put together, what each module owns, and where the seams are.

Read [`PRD.md`](PRD.md) first for *why*. This document is *how*.

---

## 1. Shape of the system

One monorepo, one Compose stack, two runtimes, seven pipeline modules.

```
                       ┌──────────────────────────────────────┐
                       │        OPERATOR CONSOLE              │
                       │  React 19 · MapLibre · deck.gl       │
                       └───────────────┬──────────────────────┘
                                       │ REST + SSE
                       ┌───────────────▼──────────────────────┐
                       │        API   (FastAPI)               │
                       │  scenes · detections · drift ·       │
                       │  suspects · evidence · jobs          │
                       └───┬───────────────────────┬──────────┘
                           │ enqueue               │ read
                  ┌────────▼────────┐     ┌────────▼──────────────────┐
                  │  Redis  (ARQ)   │     │  PostgreSQL 16            │
                  └────────┬────────┘     │  + PostGIS  + TimescaleDB │
                           │              └────────▲──────────────────┘
                  ┌────────▼────────┐              │
                  │  WORKER         │              │  batch COPY
                  │  M1 … M7        │              │
                  │  (Python)       │      ┌───────┴───────────────────┐
                  └────────┬────────┘      │  aisd   (Go)              │
                           │               │  live AIS recorder        │
                  ┌────────▼────────┐      │  ── 24/7, 3 months ──     │
                  │  Object store   │      └───────▲───────────────────┘
                  │  COG · NetCDF   │              │ wss
                  └────────┬────────┘      ┌───────┴───────────────────┐
                           │               │  AISStream.io             │
                  ┌────────▼────────┐      └───────────────────────────┘
                  │  TiTiler        │
                  │  COG → XYZ      │      ┌───────────────────────────┐
                  └─────────────────┘      │  aisgen (Go)  synthetic   │
                                           └───────────────────────────┘
```

### The two-runtime boundary

**Go owns the AIS data plane. Python owns the science. The boundary is the database.**

No RPC crosses it. `aisd` and `aisgen` write AIS rows into TimescaleDB; the Python worker reads them. Neither runtime can destabilise the other, and either can be restarted independently. Rationale in [ADR 0005](adr/0005-go-for-the-ais-data-plane.md).

---

## 2. Pipeline modules

Each module is a Python package under `packages/`, with one exception noted. Modules are pure where possible: they take typed inputs, return typed outputs, and do not reach into the database themselves — the worker orchestrates and persists. This keeps every module independently testable, which matters because six people are working in parallel.

| Module | Package | Owns | Input | Output |
|---|---|---|---|---|
| **M1** Preprocess | `sagar_sar.preprocess` | Calibration, noise removal, fixed 40 m/px resample, land mask, tiling | S1 GRD product | COG + STAC item + tiles |
| **M2** Detect | `sagar_sar.detect` | Three-stage detection (proposals → segmentation → physics filter) | Tiles + env context | Slick polygons + confidence + penalty log |
| **M3** Characterise | `sagar_sar.characterise` | Geometry, damping ratio, edge sharpness, thickness class | Slick polygon + σ⁰ raster | Attribute record |
| **M4** Ship detect | `sagar_sar.ships` | CFAR point targets, wake heading, AIS cross-match | Scene + AIS at T_sar | Ship detections + dark-vessel flags |
| **M5** Drift | `sagar_drift` | OpenDrift wrappers — backward, forward, per-vessel; ensembles | Slick / vessel seeds + forcing | Particle trajectories + probability fields |
| **M6** Attribution | `sagar_attrib` | **AIS data quality pre-filter**, **per-vessel baseline gap profiles**, reachability gate, overlap scoring, log-odds model, calibration | Slick + AIS + drift | Ranked suspects + per-factor explanations |
| **M7** Evidence | `sagar_evidence` | Provenance capture, hashing, config snapshot, signed PDF | Everything above | Dossier PDF + manifest |
| — Ingest | `sagar_ingest` | S1 fetch (CDSE), env fetch (CMEMS/ERA5/GEBCO), NISAR fetch | Query | Local cached artefacts |
| — Core | `sagar_core` | Shared types, config, units, provenance primitives, logging | — | — |
| — AIS plane | `services/aisd`, `services/aisgen`, `packages/go/aiscodec` | **Go.** Live recording, synthetic generation, AIVDM codec | WebSocket / config | Rows in TimescaleDB |

### Dependency rule

```
sagar_core  ←  everything
sagar_ingest ← sagar_sar, sagar_drift
sagar_sar   ←  sagar_attrib
sagar_drift ←  sagar_attrib
sagar_attrib ← sagar_evidence
```

**`sagar_core` depends on nothing.** No module imports a sibling except along the arrows above. Circular imports here would make parallel development miserable; CI enforces the graph.

---

## 3. Data flow — one scene, end to end

```
 1  INGEST      CDSE STAC query → S1 GRD for AOI/time
                CMEMS + ERA5 + GEBCO subsets for the same window
                AIS from TimescaleDB (recorded by aisd, or synthetic from aisgen)

 2  M1          calibrate → 40 m/px → dB → land mask → tile → COG + STAC

 3  M2  A       dark-formation proposals over the scene           (seconds, CPU)
        B       SegFormer-B2 on proposal tiles only               (seconds, GPU)
        C       physics/context filter — wind, chl-a, SST,
                bathymetry, precip, recurrence, edge sharpness
                → confidence with an itemised penalty log

 4  M3          per-slick geometry, damping ratio, bearing, thickness class

 5  M4          CFAR ships → cross-match AIS at T_sar → dark vessel flags

 6  M5(a)       backward ensemble, weathering OFF → reachability region R
                                                  → origin probability field

 7  M6  pre     AIS DATA QUALITY FILTER — before any scoring
                drop/label MMSI 0, position (0,0), kinematically impossible
                implied speed, garbled static. Labelled `unreliable` and
                EXCLUDED from the evidence set — never negative evidence.
                Load per-vessel baseline gap profiles (cached).
        gate    gate AIS tracks against R          214 → 46 → 19 → 11 → 7
        seed    seed all survivors, all release times, ONE staggered run
 8  M5(c)       advect forward to T_sar, ensembled

 9  M6          overlap score per (vessel, release time)
                → drift_score, t*, slick age
                → 9-factor log-odds → Platt calibration → ranked suspects

10  M5(b)       forward forecast 24/48/72 h, weathering ON
                → shoreline impact probability, eco-zone intersection

11  M7          hash everything, snapshot config, render signed dossier
```

**Steps 6–9 are the product.** Steps 1–5 are table stakes that most teams will also build.

---

## 4. Critical implementation notes

These three points are where the architecture succeeds or fails. Each is easy to get wrong and expensive to fix late.

### 4.1 One drift run, not thousands

The per-vessel attribution is naively O(vessels × release times × ensemble members). At 50 vessels × 96 release times × 100 members that is 480,000 simulations. Impossible.

**Particles are independent, and OpenDrift supports staggered seed times.** So every particle from every vessel at every release time goes into **one** simulation, each tagged with its `(vessel_id, release_time, ensemble_member)` origin. Scoring is a group-by on the tags afterwards.

This is exact, not an approximation. It is the single implementation detail that makes the whole approach viable. See [ADR 0001](adr/0001-forward-drift-attribution.md).

### 4.2 Forcing data is cached aggressively, always

CMEMS and ERA5 fetches are slow and rate-limited, and drift ensembles read the same fields hundreds of times. Every fetch writes a local NetCDF keyed by `(product, bbox, time_range, variables)`. The drift engine reads **only** from local cache — a cache miss raises rather than silently fetching, so an offline run fails loudly at setup instead of hanging mid-demo.

This is also what makes offline mode work at all. See [`OFFLINE_MODE.md`](OFFLINE_MODE.md).

### 4.3 Provenance is captured as the pipeline runs, not reconstructed

M7 cannot rebuild lineage after the fact. Every module emits a `ProvenanceRecord` — input hashes, versions, parameters, timestamps — into the job context as it executes. M7 assembles them. A module that does not emit provenance is a module whose output cannot go in a dossier, and CI treats that as a failure.

---

## 5. Storage

### PostgreSQL 16 + PostGIS 3.4 + TimescaleDB

| Table | Type | Notes |
|---|---|---|
| `scenes` | regular | S1/NISAR products, footprint geometry, acquisition time, hashes |
| `detections` | regular + PostGIS | Slick polygons, confidence, penalty log as JSONB |
| `detection_attributes` | regular | M3 output, one row per detection |
| `ship_detections` | regular + PostGIS | CFAR targets, dark-vessel flag, AIS match |
| **`ais_positions`** | **hypertable** | Time-ordered, millions of rows. Partitioned by time, indexed on `(mmsi, time)` and a spatial index on position. **Written by Go, read by Python** |
| `ais_static` | regular | Type 5/24 static and voyage data, latest-per-MMSI view |
| `drift_runs` | regular | Run config, forcing versions, ensemble parameters |
| `drift_particles` | hypertable or Parquet | Large. Parquet on the object store if row counts get uncomfortable |
| `suspects` | regular | Ranked candidates, per-factor contributions as JSONB |
| `evidence_dossiers` | regular | Manifest, hashes, signature, PDF pointer |
| `jobs` | regular | ARQ job state mirror for the UI |

**Why TimescaleDB for AIS:** millions of time-ordered rows, queried almost exclusively as "all positions in this bbox during this window." That is precisely the hypertable use case — automatic time partitioning, chunk exclusion, and compression on older chunks.

### Object store

MinIO or a plain local volume. COGs, NetCDF forcing cache, model weights, generated dossiers, demo cache. A local volume is entirely adequate and simpler; MinIO only if we want the S3 API for a deployment story.

---

## 6. Job orchestration

Drift ensembles take minutes. The API must never block.

```
POST /api/v1/scenes/{id}/analyse  →  202 + job_id
GET  /api/v1/jobs/{job_id}        →  status, stage, progress
GET  /api/v1/jobs/{job_id}/events →  SSE stream of stage transitions
```

**Redis + ARQ.** Not Celery (heavier, more configuration), not Kafka (an event-streaming platform where we need a work queue — a jury reads that as resume padding).

Jobs report **named stages**, not a percentage: `preprocessing`, `detecting`, `filtering`, `hindcasting`, `gating_traffic`, `advecting`, `scoring`, `forecasting`, `building_dossier`. The UI shows the stage name. "Advecting 50 vessels × 96 release times" is informative; "63%" is not.

---

## 7. API surface

Contract in [`api/API_CONTRACT.md`](api/API_CONTRACT.md). **Frozen 15 October** — frontend and backend cannot both be moving in November.

```
GET    /api/v1/scenes                     list, filter by bbox/time/sensor
GET    /api/v1/scenes/{id}
POST   /api/v1/scenes/{id}/analyse        → job
GET    /api/v1/detections/{id}            polygon, attributes, penalty log
GET    /api/v1/detections/{id}/suspects   ranked, with per-factor contributions
GET    /api/v1/detections/{id}/hindcast   origin probability field
GET    /api/v1/detections/{id}/forecast   24/48/72 h + shoreline impact
GET    /api/v1/detections/{id}/audit      the full filter cascade with drop reasons
GET    /api/v1/ais/tracks                 bbox + time window
GET    /api/v1/ships                      SAR detections, dark-vessel flag
POST   /api/v1/evidence/{detection_id}    → signed dossier
GET    /api/v1/jobs/{id}                  status
GET    /api/v1/jobs/{id}/events           SSE
```

Geometry is GeoJSON. Times are ISO 8601 UTC with an explicit `Z`. Probability fields are served as COG via TiTiler, not as JSON — a raster in JSON is a mistake we should not have to make twice.

---

## 8. Frontend

Full specification in [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md).

```
web/src/
  app/          shell, routing, layout, keyboard shortcuts
  components/   Panel · ConfidenceBar · FactorBars · MetricRow ·
                Timeline · LayerLegend · StatusStrip
  features/     detection/ · drift/ · attribution/ · darkvessel/ · evidence/
  lib/          api client · deck.gl layer factories · MapLibre style · formatters
  styles/       tokens.css (the single source of colour) · tailwind theme
```

State: TanStack Query for server state, Zustand for map/timeline UI state. No Redux — there is not enough client state to justify it.

**The timeline is global.** One clock drives every layer. Layers that cannot honour the current time are visibly marked stale rather than silently showing the wrong moment.

---

## 9. Deployment

```
docker compose up
```

| Service | Image | Notes |
|---|---|---|
| `db` | `timescale/timescaledb-ha:pg16` | PostGIS included |
| `redis` | `redis:7-alpine` | |
| `api` | local build | FastAPI + Uvicorn |
| `worker` | local build | Python + micromamba geo env; GPU passthrough where available |
| `tiler` | `ghcr.io/developmentseed/titiler` | |
| `aisd` | local build, `scratch` base | **Go static binary.** Also runs standalone outside Compose — that is the point |
| `web` | local build | Vite dev server, or nginx in production mode |

`docker-compose.offline.yml` overrides every network-dependent setting to read from the local cache. See [`OFFLINE_MODE.md`](OFFLINE_MODE.md).

**`aisd` deliberately has no dependency on the rest of the stack** beyond the database connection string. It must be deployable on a spare laptop or VPS on day one and left running for three months, entirely independently of whether anything else works.

---

## 10. Testing

| Level | Scope | Runs |
|---|---|---|
| Unit | Pure functions — geometry, scoring, codec, formatters | Every push |
| Contract | Pydantic schemas at every module boundary | Every push |
| Golden-file | M1 output on a fixture scene, byte-comparable | Every push |
| Integration | Full pipeline on a small cached scene | Every PR |
| Go | `aiscodec` round-trip: encode → decode → compare | Every push |
| Smoke | `docker compose up` and hit every endpoint | Nightly + pre-demo |

**The `aiscodec` round-trip test carries unusual weight.** It is what makes the claim "synthetic and real AIS use the same ingest path" verifiable rather than aspirational, and PRD §6.4 depends on it.

---

## 11. What we deliberately did not build

| Not built | Why |
|---|---|
| Kubernetes | One box. Compose. |
| Kafka | We need a work queue, not an event-streaming platform. |
| Microservices | Six people, four months. A monolith with clean module boundaries is faster and easier to demo. |
| GraphQL | REST plus SSE covers every access pattern here. |
| A custom tile server | TiTiler exists. |
| An ORM-heavy data layer | Raw SQL with PostGIS functions is clearer for spatial work, and the queries are the interesting part. |
| Server-side rendering | It is an operator console behind a login, not a public site. |
