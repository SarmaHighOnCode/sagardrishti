# `tools`

Operational scripts that are not part of a service.

| Tool | Purpose |
|---|---|
| `warm_cache.py` | Populate the offline cache from every source |
| `ais_status.py` | Recorder health — rows in last 24h, gaps, reconnect counts |
| `quota_status.py` | CDSE Processing Unit usage |
| `build_demo_cache.py` | Freeze a demo scenario, including pre-computed ensembles |
| `check_offline.py` | Verify no outbound network calls on an internal-only network |
| `make_figures.py` | Regenerate every evaluation figure from results JSON |

## `ais_status.py` — run this often

Daily for the first week the recorder is up, weekly thereafter.

A recorder that silently stopped in October and is discovered in December is the worst available outcome — the data is unrecoverable, because AISStream has no replay.

## `make_figures.py` — never hand-draw a chart

Every figure in the deck is generated from `ml/evaluation/results/`. When a number changes the chart changes with it.

A hand-made chart drifts from the data it claims to show, and a jury that catches that has caught something serious.
