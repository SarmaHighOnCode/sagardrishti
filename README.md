<div align="center">

# सागरदृष्टि · SAGARDRISHTI

**Automated oil-spill detection, drift hindcasting, and vessel attribution for Indian waters.**

*From satellite pixel to named vessel — with an error bar on every number.*

[![Problem Statement](https://img.shields.io/badge/SIH_2026-PS_26143-2d72d2?style=flat-square)](https://sih.gov.in)
[![Organisation](https://img.shields.io/badge/NTRO-Disaster_Management-1c2127?style=flat-square)](https://ntro.gov.in)
[![Python](https://img.shields.io/badge/Python-3.11-238551?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-c87619?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![React](https://img.shields.io/badge/React-19-2d72d2?style=flat-square&logo=react&logoColor=white)](https://react.dev)
[![License](https://img.shields.io/badge/license-Apache_2.0-5f6b7c?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/status-pre--alpha-935610?style=flat-square)](docs/ROADMAP.md)

</div>

---

## The gap this closes

Most oil entering the sea from ships does not come from headline disasters. It comes from **routine, deliberate, operational discharge** — tank washings, oily bilge, sludge — released at night, far from shore, by vessels that are long gone by the time anyone looks.

India already has two of the three capabilities needed to stop it:

| Capability | Who has it | Status |
|---|---|---|
| Forward drift prediction | **INCOIS** — OOSA v5.0, SARAT | Operational |
| Response authority | **Indian Coast Guard** under NOSDCP | Operational |
| **Automated attribution** — *who did it* | — | **Missing** |

Today, attribution in Indian waters is manual, slow, and in practice almost never happens. A slick is found, an advisory is issued, the oil disperses, and no one is held responsible.

**SAGARDRISHTI closes that third gap.** It ingests Sentinel-1 SAR, detects and characterises slicks, reconstructs *where and when* the oil entered the water as a probability field, and ranks the vessels that could have put it there — producing an auditable evidence dossier an ICG investigator can act on.

> **We rank. We never accuse.** The system outputs calibrated probabilities with per-factor explanations, not verdicts. That is both scientifically correct and legally survivable.

---

## What makes this different

The obvious approach is: *segment the slick, find the nearest ship, declare it guilty.* That breaks under a single question — **"the image is six hours old; the responsible vessel is 80 nautical miles away by now."**

SAGARDRISHTI inverts the problem.

```
              ┌─── NAIVE ─────────────────────────────────┐
              │  slick → nearest AIS contact → suspect     │   ✗ ignores drift
              └───────────────────────────────────────────┘

┌─── SAGARDRISHTI ────────────────────────────────────────────────────────────┐
│  Assume EVERY vessel MIGHT have discharged at EVERY moment along its        │
│  track. Simulate all of it forward to the SAR acquisition time.             │
│  Whoever's simulated plume lands on the observed slick is the suspect —     │
│  and the release time that fits IS the slick's age.                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

This one architectural decision buys three things at once:

1. **Drift-correct attribution** — the vessel is matched where it *was*, not where the slick is now.
2. **Slick age for free** — age is not measured from pixels (it cannot be); it falls out of the attribution solve with an uncertainty band.
3. **A defensible negative** — vessels are *excluded* on physics, not on distance, and every exclusion is logged with its reason.

Four further things a baseline does not do:

- **Physics gates the ML.** The network proposes; wind speed, chlorophyll-a, SST, bathymetry, precipitation and detection history dispose. Every confidence penalty is surfaced to the analyst with its cause.
- **Ensembles, not point estimates.** 100+ member drift ensembles produce origin *probability fields*. A single deterministic run is not an answer.
- **Dark vessels.** SAR ship detections with no AIS correlate are flagged — precisely the case EMSA's CleanSeaNet cannot solve.
- **Chain of custody.** Every dossier carries source product IDs, SHA-256 hashes, model weight hashes, forcing dataset versions and a full config snapshot.

---

## System architecture

```
╭─ INGEST ─────────────────────────────────────────────────────────────────────╮
│  Sentinel-1 (CDSE Sentinel Hub · STAC)   Environment (CMEMS · ERA5 · GEBCO)   │
│  AIS (AISStream live · synthetic generator · NOAA MarineCadastre validation)  │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
╭─ M1  PREPROCESS ─────────────────────────────────────────────────────────────╮
│  border + thermal noise → σ⁰ calibrate → dB → resample to FIXED 40 m/px →     │
│  land mask → normalise → tile 512² → Cloud-Optimised GeoTIFF + STAC item      │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
╭─ M2  DETECT ─────────────────────────────────────────────────────────────────╮
│  A · dark-formation proposals (fast, high recall)                            │
│  B · semantic segmentation — SegFormer-B2, DeepLabv3+ baseline               │
│  C · physics & context look-alike filter        ← the differentiator         │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
╭─ M3  CHARACTERISE ───────────────────────────────────────────────────────────╮
│  area · perimeter · complexity · elongation · major-axis bearing · centroid   │
│  damping ratio (dB) · relative thickness class · inferred age (back from M6)  │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
╭─ M4  SHIP DETECT ────────────────────────────────────────────────────────────╮
│  CFAR point targets → wake heading → AIS cross-match → ⚑ DARK VESSEL          │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
╭─ M5  DRIFT ENGINE   (OpenDrift / OpenOil) ───────────────────────────────────╮
│  ← backward ensemble   → origin probability field   (weathering OFF)         │
│  → forward ensemble    → 24/48/72 h forecast + shoreline impact              │
│  ⇉ per-vessel forward  → attribution evidence  (ONE staggered-seed run)      │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
╭─ M6  ATTRIBUTION ────────────────────────────────────────────────────────────╮
│  AIS reconstruct → reachability gate (214 → 7) → per-vessel drift overlap →   │
│  9-factor log-odds scoring → Platt calibration → ranked, explained suspects   │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
╭─ M7  EVIDENCE ───────────────────────────────────────────────────────────────╮
│  provenance hashes · config snapshot · model lineage · signed PDF dossier     │
╰──────────────────────────────────────┬───────────────────────────────────────╯
                                       ▼
      FastAPI  ·  PostGIS + TimescaleDB  ·  Redis/ARQ  ·  TiTiler
                                       ▼
      React 19 · MapLibre GL · deck.gl · Palantir-grade dark operator console
```

Full detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Repository map

| Path | Contains |
|---|---|
| [`docs/`](docs/) | **Start here.** PRD, architecture, design system, data strategy, scoring model, evaluation plan, viva defence |
| [`packages/`](packages/) | Python domain libraries — one per pipeline module (`sagar_sar`, `sagar_drift`, `sagar_attrib` …) |
| [`services/`](services/) | Deployable processes — FastAPI, ARQ worker, TiTiler |
| [`ml/`](ml/) | Training configs, dataset adapters, evaluation harness, model cards, weights |
| [`web/`](web/) | React operator console — the Palantir-style interface |
| [`db/`](db/) | PostGIS + TimescaleDB schema and migrations |
| [`infra/`](infra/) | Docker, Compose stacks, operational scripts |
| [`data/`](data/) | Local data lake — **git-ignored**, see [`data/README.md`](data/README.md) |

---

## Quickstart

> **Prerequisite: WSL2 (Ubuntu 22.04).** The geospatial stack — GDAL, PROJ, OpenDrift — is painful on native Windows. This is not optional. See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

```bash
git clone https://github.com/<org>/sagardrishti.git && cd sagardrishti
cp .env.example .env          # add CDSE, CMEMS and AISStream credentials
make setup                    # micromamba geo env + uv api env + web deps
make up                       # postgis · redis · api · worker · tiler · web
make demo                     # load the cached MSC ELSA 3 scenario
```

Console at `http://localhost:5173`, API docs at `http://localhost:8000/docs`.

Full instructions: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) · Offline/finale mode: [`docs/OFFLINE_MODE.md`](docs/OFFLINE_MODE.md)

---

## Honest limits

We publish these before a jury has to find them. Each is a physics or data constraint, not an engineering failure.

| Limit | Reality | What we do about it |
|---|---|---|
| **Current resolution vs slick scale** | Best free currents are 1/12° (~8 km). Slicks are shaped by sub-kilometre eddies that are entirely unresolved. | The dominant term in our error budget. We quantify it: 100+ member ensembles, probability fields, never point estimates. Ingesting INCOIS high-resolution regional currents is the first operational upgrade. |
| **Cross-domain generalisation** | Models trained on Mediterranean SAR degrade sharply on other basins — a documented drop from roughly 68% to 52% mIoU moving to Peruvian waters. | We measure and report our own drop rather than quoting a single flattering number. |
| **Historical AIS for Indian waters** | Not publicly available in bulk. Free APIs are live-only and terrestrial-only; commercial providers consolidated further through 2026. | Method validated on real NOAA US AIS; Indian demonstration uses a synthetic generator calibrated to lane geometry recorded live from AISStream. The data gap is itself part of the capability gap this PS exists to close. |
| **Slick age** | Not recoverable from a single SAR scene. Contrast correlates with age but is confounded by wind, incidence angle, oil type and volume. | Reframed as an inference, not a measurement — see the attribution solve above. |
| **Oil type and volume** | Not retrievable from C-band SAR alone. | Explicitly out of scope. We report *relative* thickness classes only. |

We also deliberately **do not** apply super-resolution to SAR before detection. SR generates pixels; it does not add information. Introducing synthesised texture into a physics-based measurement used as evidence would break the chain of custody. See [`docs/adr/0004-no-super-resolution.md`](docs/adr/0004-no-super-resolution.md).

---

## Documentation

| Document | Purpose |
|---|---|
| [PRD](docs/PRD.md) | Product requirements — scope, modules, principles, roadmap |
| [Architecture](docs/ARCHITECTURE.md) | System design, data flow, module contracts |
| [Design System](docs/DESIGN_SYSTEM.md) | The Palantir-grade interface language — tokens, density, patterns |
| [Domain Primer](docs/DOMAIN_PRIMER.md) | The SAR and ocean physics you must know to defend this |
| [Data Sources](docs/DATA_SOURCES.md) | Every dataset, its licence, access route and fallback |
| [Scoring Model](docs/SCORING_MODEL.md) | The nine attribution factors and why each weight is what it is |
| [Evaluation](docs/EVALUATION.md) | Metrics, targets, ablations, honest accuracy claims |
| [Viva Defence](docs/VIVA_DEFENCE.md) | Anticipated jury questions and rigorous answers |
| [Demo Script](docs/DEMO_SCRIPT.md) | The ten-minute run of show |
| [Roadmap](docs/ROADMAP.md) | Phases, milestones, team ownership |
| [ADRs](docs/adr/) | Architecture decision records — what we chose, and what we rejected |

---

## Acknowledgements

Built on open science: Copernicus Sentinel-1, Copernicus Marine Service, ECMWF ERA5, GEBCO, [OpenDrift/OpenOil](https://opendrift.github.io/) (MET Norway), and the openly published SAR oil-spill datasets credited in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). Interface language derived from [Blueprint](https://blueprintjs.com), Palantir's open-source design system.

Developed for **Smart India Hackathon 2026**, Problem Statement **26143**, for the **National Technical Research Organisation**.

## License

Apache 2.0 — see [LICENSE](LICENSE).
