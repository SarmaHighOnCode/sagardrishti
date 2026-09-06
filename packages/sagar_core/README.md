# `sagar_core`

Shared foundations. **Depends on nothing.** Everything depends on it.

## Responsibility

| Area | Contents |
|---|---|
| **Types** | Pydantic models crossing module boundaries — `Scene`, `SlickPolygon`, `SlickAttributes`, `DriftRun`, `Suspect`, `ProvenanceRecord` |
| **Config** | Layered settings — defaults, file, environment. Single source of truth for paths, thresholds, credentials |
| **Units** | Explicit unit handling. Metres, knots, m/s, degrees, dB |
| **Provenance** | Hashing, config snapshots, lineage record construction |
| **Geo** | CRS constants, coordinate formatting, geodesic helpers |
| **Logging** | Structured logging with job and stage context |

## Why units get their own module

Every mixed-unit codebase eventually confuses knots with m/s, or degrees with radians, in a way that produces plausible-looking wrong answers. In a drift model that silently corrupts the entire attribution chain, and the resulting bug is nearly invisible.

Values crossing a module boundary carry their unit in the field name (`speed_ms`, `bearing_deg`, `area_km2`, `damping_db`) and conversions go through this package.

## Uncertainty in the type system

Inferred quantities carry their uncertainty **in the same model**:

```
slick_age_hours: float
slick_age_ci: tuple[float, float]
```

Validation rejects one without the other. Product principle 2 is enforced by the schema rather than by discipline — see [`API_CONTRACT.md`](../../docs/api/API_CONTRACT.md).

## Status: implemented

All six areas above are built and tested (63 tests). Layout:

| File | Contains |
|---|---|
| `units.py` | Speed, angle, distance, area, dB, time conversions |
| `geo.py` | `LonLat`, `BBox`, haversine, bearings, `implied_speed_knots` |
| `types.py` | Domain models — `Scene`, `SlickPolygon`, `Suspect`, `DriftRun` … |
| `provenance.py` | `ProvenanceRecord`, `ProvenanceChain`, hashing |
| `config.py` | `Settings` (env-layered, secrets redacted) |
| `logs.py` | JSON logging, `job_context`, named stages |

Invariants enforced at construction, not by convention:

- `SlickAgeEstimate` / `ReleaseTimeEstimate` — value and interval both required
- `SlickPolygon` — a confidence drop with an empty penalty log is rejected
- `DriftRun` — a backward run with weathering enabled is rejected
- `ProvenanceChain.synthetic` — one synthetic stage marks the whole chain
- `Settings` — secrets excluded from `repr()` and from `snapshot()`

Run: `pytest packages/sagar_core -v`

## Rules

- **No I/O.** No network, no database, no file reads beyond config.
- **No sibling imports.** This package sits at the bottom of the graph.
- **Breaking changes ripple everywhere.** Discuss before changing a shared type after 15 October.
