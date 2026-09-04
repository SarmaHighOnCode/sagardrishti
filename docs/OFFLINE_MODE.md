# Offline Mode

**Assume the nodal centre network will fail.** Plan for it, build for it, and test it with the cable physically out.

This is risk #7 in the register, rated High probability / Fatal impact. It is also the cheapest catastrophic risk to eliminate: a few days of work in November against the possibility of losing the finale entirely.

---

## The requirement

By **15 November**, the entire system must run end to end with **zero network calls**, from a cold `docker compose up`, on a machine that has never had internet access.

Not "mostly works offline." Not "works if the cache is warm." **Zero network calls, verified.**

---

## What must be cached

| Asset | Location | Approx size | Owner |
|---|---|---|---|
| Preprocessed Sentinel-1 scenes (5–10) | `data/demo/*/scene/` | 2–5 GB | Data ops |
| Forcing subsets — currents, wind, waves, SST, chl-a | `data/cache/forcing/` | 1–3 GB | Ocean lead |
| GEBCO bathymetry subset, coastline | `data/cache/static/` | 500 MB | Ocean lead |
| AIS — real recorded + synthetic | PostGIS dump in `data/demo/*/ais.sql` | 200 MB – 2 GB | AIS lead |
| Model weights | `ml/weights/` | 200–500 MB | ML lead |
| Pre-computed drift ensembles | `data/demo/*/drift/` | 1–3 GB | Ocean lead |
| Basemap vector tiles | `web/public/tiles/` | 500 MB – 2 GB | Frontend |
| Docker images | Local registry or saved tarballs | 5–10 GB | Integration |
| Python wheels | `infra/wheels/` | 2–3 GB | Integration |
| Go module cache | vendored in `services/*/vendor/` | 50 MB | Integration |
| npm packages | `web/node_modules` committed or tarballed | 500 MB | Frontend |

**Total: roughly 15–30 GB.** Budget a dedicated external SSD and keep a second copy on the backup laptop.

---

## Design rules that make this possible

These must be honoured from the start. Retrofitting offline support in November is far harder than building for it in September.

### 1. Cache misses raise, they do not fetch

The drift engine and every ingest path read **only** from the local cache. A missing artefact raises a clear error naming what is absent.

```
CacheMissError: forcing product GLOBAL_ANALYSISFORECAST_PHY_001_024
  bbox=(68.0, 8.0, 78.0, 15.0) time=2026-05-25T00:00Z/2026-05-26T00:00Z
  not found in data/cache/forcing/. Run `make warm-cache` while online.
```

**A silent fallback to network fetch is the bug that ends the demo** — everything works in the lab, then hangs on stage.

### 2. No CDN references anywhere in the frontend

No Google Fonts link, no unpkg script, no remote tile server, no external icon set. Fonts are self-hosted in `web/public/fonts/`, basemap tiles are local MBTiles served by the tile container.

A single `<link>` to a font CDN produces a several-second render stall on a dead network, and it will look like the application is broken.

### 3. Basemap tiles are bundled

MapLibre with a local style JSON pointing at local MBTiles. **This is a chief reason we chose MapLibre over a hosted map provider** — no token, no remote style, works air-gapped.

### 4. All timestamps are internal

No NTP dependency, no external time API. Scene times come from product metadata.

### 5. The offline Compose override

```bash
docker compose -f docker-compose.yml -f docker-compose.offline.yml up
```

The override sets `SAGAR_OFFLINE=1`, which switches every fetcher into cache-only mode, points the frontend at local tiles, and disables telemetry and update checks.

---

## Warming the cache

```bash
make warm-cache          # everything below, online, ~30-60 min
```

| Step | Command | Notes |
|---|---|---|
| Fetch demo scenes | `make cache-scenes` | CDSE; check PU usage |
| Fetch forcing | `make cache-forcing` | CMEMS + ERA5, per scenario window |
| Fetch static layers | `make cache-static` | GEBCO, coastline. Once |
| Dump AIS | `make cache-ais` | PostGIS dump per scenario |
| Pre-compute drift | `make cache-drift` | **Slow — tens of minutes.** Run overnight |
| Build basemap tiles | `make cache-tiles` | Extract Indian EEZ region |
| Save Docker images | `make save-images` | `docker save` to tarballs |
| Vendor wheels | `make vendor-wheels` | `pip download` for every dependency |

Run the whole thing at least **twice before the finale** — once in early November to find gaps, once in the final week with the exact demo scenarios frozen.

---

## The verification test

**This is the part that actually matters.** Everything above is preparation; this is proof.

### Procedure

1. Take the demo machine to a room with no network
2. **Physically disconnect ethernet. Disable Wi-Fi in the OS. Turn off Bluetooth tethering.** Airplane mode is not sufficient — verify with `ip link` that nothing is up
3. Reboot, to clear any warm DNS or in-memory cache
4. `docker compose -f docker-compose.yml -f docker-compose.offline.yml up`
5. Run **every** demo scenario end to end, including the evidence PDF
6. Run the live-compute scenario
7. Note anything slow, anything that errors, anything that renders wrong

### Pass criteria

- [ ] Stack comes up cold in under 3 minutes
- [ ] All four demo scenarios run start to finish
- [ ] Basemap renders with correct fonts and no missing tiles
- [ ] Drift animation plays at full frame rate
- [ ] Evidence PDF generates with all provenance fields populated
- [ ] Live-compute scenario completes in under 60 seconds
- [ ] **Zero network errors in any container log**
- [ ] No visible loading stall longer than 2 seconds anywhere

### Do it twice

**Once around 15 November**, to find the gaps — and there will be gaps, in places nobody predicted. **Once in the final week**, with the exact frozen demo configuration, as the final sign-off.

The second test is not optional just because the first passed. Between them, dependencies will have been added.

---

## Detecting leaks

The most reliable way to catch an accidental network dependency is to make network access impossible rather than merely absent:

```bash
# Run the stack on an internal-only Docker network
docker network create --internal sagar-offline
```

Any container attempting an outbound connection fails immediately and loudly, with a stack trace naming the caller. This surfaces leaks that a simply-disconnected machine would hide behind a long timeout.

Add this as a CI job once the stack stabilises — a nightly build that runs the integration test on an internal-only network. A dependency added in December then fails in CI rather than on stage.

---

## Contingency ladder

If offline mode fails at the venue anyway:

1. **Backup laptop** with an identical, independently tested environment. Not a copy of the same disk — separately built and separately verified
2. **Recorded full-run video**, on the machine, in the deck, and on a USB stick
3. **Screenshot deck**, one slide per demo beat, capable of carrying the whole narrative
4. **Talk through the architecture** with the ADRs open. A team that can explain its design without a working demo still scores meaningfully; a team that cannot does not

Prepare all four. The first two take an afternoon each.
