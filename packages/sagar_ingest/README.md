# `sagar_ingest`

Fetchers for every external data source, with mandatory local caching.

## Sources

| Source | Product | Client |
|---|---|---|
| **CDSE Sentinel Hub** | Sentinel-1 IW GRD, calibrated, noise-removed | `sentinelhub-py` |
| **CDSE STAC / OData** | Scene discovery, raw product download | `pystac-client` |
| **ASF DAAC** | Sentinel-1 mirror, **NISAR L-band** | `asf_search` |
| **Copernicus Marine** | Currents, waves/Stokes, wind, SST, chlorophyll | `copernicusmarine` |
| **ECMWF CDS** | ERA5 wind and precipitation | `cdsapi` |
| **GEBCO** | Bathymetry | Direct download, cached once |

## Why we skip SNAP

The Sentinel Hub Process API returns GRD **already calibrated and thermal-noise-removed** as GeoTIFF, in one HTTP request. Installing ESA SNAP and wiring `snappy` on Windows costs roughly a week and still produces JVM bridge failures. SNAP survives only as a Dockerised `gpt` CLI fallback for offline reproducibility — **never `snappy`**. PRD section 6.1.

## The caching contract — this is the important part

Every fetch writes local NetCDF or GeoTIFF keyed by `(product, bbox, time_range, variables)`.

**In offline mode, a cache miss raises. It does not fetch.**

```
CacheMissError: forcing product GLOBAL_ANALYSISFORECAST_PHY_001_024
  bbox=(68.0, 8.0, 78.0, 15.0) time=2026-05-25T00:00Z/2026-05-26T00:00Z
  not found in data/cache/forcing/. Run `make warm-cache` while online.
```

A silent network fallback is **the bug that ends the demo** — everything works in the lab, then hangs on stage at the nodal centre. Fail loudly at setup instead. See [`OFFLINE_MODE.md`](../../docs/OFFLINE_MODE.md).

## Quota

CDSE free tier is 10,000 Processing Units per month per account; a typical AOI request costs tens of PUs. Ample, but log usage — `make quota-status`.

## NISAR

L-band public since 20 July 2026 via ASF DAAC. **Scoped to an ingest and preprocessing path only** — not a trained L-band detector. Phase 2 stretch, first thing cut. PRD section 6.2.
