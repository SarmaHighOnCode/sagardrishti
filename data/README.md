# `data` — Local Data Lake

**Everything in here is git-ignored.** Nothing under `data/` is ever committed.

```
raw/         downloaded products, untouched
interim/     intermediate processing
processed/   COGs, tiles, derived rasters
cache/       forcing NetCDF, static layers  <- the offline backbone
demo/        frozen demo scenarios          <- the finale depends on this
```

## Why nothing is committed

Sentinel-1 scenes are gigabytes. Git is not a data store, and a repository with a multi-gigabyte history is painful for six people to clone and impossible to work with at a venue.

Use the shared external SSD. Provenance is tracked in the database and in dossiers, not in git.

## `cache/` — the offline backbone

Fetches are keyed by `(product, bbox, time_range, variables)`.

**In offline mode a cache miss raises. It does not fetch.** A silent network fallback is the bug that ends the demo — everything works in the lab, then hangs at the nodal centre. Fail loudly at setup.

```bash
make warm-cache     # populate, online, 30-60 min
```

## `demo/` — treat as production

```
demo/
  scenario_elsa3/       headline, MSC ELSA 3, known vessel
  scenario_darkvessel/  the 7:30 beat
  scenario_lookalike/   the 1:50 beat, rejection with reasons
  scenario_live/        small, genuinely computes in under 60 s
```

Each holds its scene, forcing subset, AIS dump, pre-computed drift ensembles and expected outputs.

**Every scenario must run with the network cable out.** Verified twice — once around 15 November to find gaps, once in the final week with the frozen configuration. See [`OFFLINE_MODE.md`](../docs/OFFLINE_MODE.md).

## Budget

Roughly 15–30 GB total. Dedicated external SSD, plus a second copy on the backup laptop.
