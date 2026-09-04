# `worker` — ARQ

Executes the pipeline. Where every long-running computation happens.

## Responsibility

Consume jobs from Redis, orchestrate M1–M7, persist results, emit progress. **The worker is the only component that both calls the science packages and touches the database** — packages stay pure so they remain testable.

## Stages

```
preprocessing -> detecting -> filtering -> hindcasting
  -> gating_traffic -> advecting -> scoring -> forecasting -> building_dossier
```

Each transition emits an event to the SSE stream.

## Provenance

The worker owns the job context that modules write `ProvenanceRecord`s into as they run. **Lineage cannot be reconstructed afterwards** — if the worker drops a record, M7 cannot produce a defensible dossier. See [`ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) section 4.3.

## Resources

| Stage | Bound by |
|---|---|
| Preprocessing | IO and CPU |
| Segmentation | **GPU** — seconds at 40 m/px |
| CFAR ships | CPU |
| **Drift ensembles** | **CPU, multi-core. The actual bottleneck** |

OpenDrift is NumPy and CPU-bound. Parallelise across cores; cache forcing aggressively. Demo scenarios are pre-computed — a live full ensemble costs eight minutes of a ten-minute slot.

## Environment

The **`sagar-geo`** micromamba environment, with GPU passthrough where available.
