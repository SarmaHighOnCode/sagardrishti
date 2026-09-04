# `sagar_drift` — M5

OpenDrift and OpenOil wrappers. **Owner: Ocean/drift lead.**

## Three run modes

| Mode | Direction | Weathering | Produces |
|---|---|---|---|
| **(a) Hindcast** | Backward | **OFF** | Origin probability field, reachability region |
| **(b) Forecast** | Forward | ON | 24/48/72 h extent, shoreline impact |
| **(c) Per-vessel** | Forward | ON | Attribution evidence — the core of M6 |

## Weathering is disabled in backward runs

Evaporation and emulsification are **irreversible**. Running them backwards is physically meaningless — you would be un-evaporating oil.

Getting this wrong produces plausible-looking, entirely invalid output, and it is a good viva question. Backward runs are advection only.

## One simulation, not thousands

Mode (c) is naively O(vessels x release times x ensemble members) — 50 x 96 x 100 is 480,000 simulations. Impossible.

**Particles are independent and OpenDrift supports staggered seed times.** So every particle from every vessel at every release time goes into **one** run, each tagged `(vessel_id, release_time, ensemble_member)`. Scoring is a group-by on the tags.

This is exact, not an approximation, and it is **the implementation detail that makes the whole approach viable**. [ADR 0001](../../docs/adr/0001-forward-drift-attribution.md).

## Ensembles are mandatory

A single deterministic run is worthless — it frequently misses the true origin entirely. At least 100 members, perturbing:

| Parameter | Range | Why |
|---|---|---|
| Wind drift factor | uniform [0.02, 0.04] | The genuine physical range. Picking one value fabricates precision |
| Current magnitude | ±10–20% + small rotation | Forcing error |
| Current product | 1/12 model vs 1/4 observational | Structural uncertainty |
| Horizontal diffusivity | sampled | Unresolved sub-grid mixing |
| Stokes drift | on/off | Often neglected; it should not be |

**The ensemble spread is the uncertainty estimate.** Output is a probability field. Never a point.

## The dominant error term

```
slick as SAR sees it       ~40 m
sub-mesoscale eddies       100 m - 10 km   <- shapes the slick
best free currents         ~8 km           <- cannot see any of it
```

We advect a metre-scale feature with a field that cannot resolve anything smaller than a city. **This is a physics and data-availability limit, not an engineering failure**, and stating it clearly is worth more than hiding it.

## Performance

**CPU-bound, not GPU.** OpenDrift is NumPy. This is the actual bottleneck in the system.

- Parallelise across cores with `multiprocessing`
- Cache forcing fields aggressively as local NetCDF
- **Pre-compute demo scenarios.** Live-computing a full ensemble on stage costs eight minutes of a ten-minute slot

## Validation

Ennore 2017, against the published INCOIS trajectory-vs-Sentinel-1A comparison. Published OpenOil skill scores are 0.89–0.98 in favourable conditions — a benchmark, not a promise.
