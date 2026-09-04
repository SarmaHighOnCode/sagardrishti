# Python Domain Packages

The scientific core. One package per pipeline module, plus shared foundations.

## Design rules

**Packages are pure where possible.** They take typed inputs, return typed outputs, and **do not touch the database**. The worker orchestrates and persists. This matters because six people work in parallel: a package that reaches into PostGIS cannot be unit-tested without a database, and a module that cannot be tested in isolation becomes a module nobody dares change.

**Every module emits provenance.** Input hashes, versions, parameters, timestamps, into the job context as it runs. M7 assembles them into the dossier. Provenance cannot be reconstructed after the fact — see [`ARCHITECTURE.md`](../docs/ARCHITECTURE.md) section 4.3.

## Dependency graph — enforced by CI

```
sagar_core     <- everything          (depends on nothing)
sagar_ingest   <- sagar_sar, sagar_drift
sagar_sar      <- sagar_attrib
sagar_drift    <- sagar_attrib
sagar_attrib   <- sagar_evidence
```

No package imports a sibling except along these arrows. Circular imports here would make parallel development miserable.

## Packages

| Package | Module | Owner | Purpose |
|---|---|---|---|
| [`sagar_core`](sagar_core/) | — | Integration | Shared types, config, units, provenance, logging |
| [`sagar_ingest`](sagar_ingest/) | — | Data ops | Sentinel-1, NISAR, CMEMS, ERA5, GEBCO fetchers with caching |
| [`sagar_sar`](sagar_sar/) | M1–M4 | ML lead | Preprocess, detect, characterise, ship detection |
| [`sagar_drift`](sagar_drift/) | M5 | Ocean lead | OpenDrift wrappers, ensembles, probability fields |
| [`sagar_attrib`](sagar_attrib/) | M6 | AIS lead | Traffic gating, overlap scoring, log-odds model |
| [`sagar_evidence`](sagar_evidence/) | M7 | Integration | Provenance assembly, hashing, signed dossier |

## Environment

These live in the **`sagar-geo`** micromamba environment (conda-forge GDAL/PROJ/OpenDrift), not the `uv` API environment. See [`DEVELOPMENT.md`](../docs/DEVELOPMENT.md) section 2 for why the split exists.
