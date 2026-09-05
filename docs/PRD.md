# PRD — SAGARDRISHTI

**Automated Oil Spill Detection, Hindcasting & Vessel Attribution**

| | |
|---|---|
| **Version** | 2.0 |
| **Date** | 3 September 2026 |
| **Problem Statement** | SIH 2026 · PS 26143 |
| **Organisation** | National Technical Research Organisation (NTRO) |
| **Theme / Category** | Disaster Management · Software |
| **Owner** | Team Strawhats |
| **Supersedes** | v1.0 (3 Sept 2026) |

---

## Changelog — what v2.0 changes

v1.0 was structurally sound. This revision corrects facts that moved, adds two capabilities that materially strengthen the NTRO pitch, and replaces the frontend direction wholesale.

| # | Change | Why it matters |
|---|---|---|
| 1 | **NISAR added as a first-class data source** (§6.2) | NISAR L-band data went public **20 July 2026** via ASF DAAC. It is a NASA–ISRO joint mission — India co-owns it. For an NTRO pitch this converts "we depend on European satellites" into "we have a sovereign-adjacent path." This is the single biggest addition in v2.0. |
| 2 | **INCOIS status corrected** (§3) | OOSA is now **v5.0** with advanced GIS and predictive capability; INCOIS also runs **SARAT**, activated for MSC ELSA 3. v1.0 described a stale version. Quoting the old one in a viva would be an unforced error. |
| 3 | **Frontend direction replaced** (§9, `DESIGN_SYSTEM.md`) | Target is now an explicit **Palantir-grade operator console**, anchored on Blueprint — Palantir's own open-source design system — with exact tokens. v1.0's "Tailwind + shadcn, looks professional" was not a design direction. |
| 4 | **Wan Hai 503 added** to reference incidents (§6.6) | Second Kerala incident, June 2025. Kerala High Court proceedings against **both** MSC ELSA 3 and Wan Hai 503 owners give the evidence-dossier deliverable a live legal context. |
| 5 | **Detection SOTA refreshed** (§6.3, §7.3) | 2025–26 literature reports substantially higher numbers than v1.0's targets and converges on one finding we can exploit cheaply: **edge/boundary prominence is a primary discriminator** between oil and look-alikes. |
| 6 | **Constellation facts confirmed** (§6.1) | Sentinel-1A operations terminated **29 June 2026**; final configuration is **S1C + S1D**. v1.0 was correct; now verified against ESA and CDSE sources. |
| 7 | **Prior-art section expanded** (§3) | Adds SeaVision, DarkVesselNet and related 2025–26 dark-vessel work, so the differentiation claim survives a well-read jury. |
| 8 | **AIS gap factor redefined; data quality pre-filter added** (§8.5, §8.6, §7.6) | **The most important correctness fix in v2.0.** The naive f₄ — *"a gap exists near the spill, therefore suspicious"* — produces false accusations, because gaps are overwhelmingly caused by cheap transponders, out-of-coverage operation and bad data. Redefined as deviation from the vessel's *own* baseline, discounted by coverage, behind a data quality pre-filter. Dark vessels get a coarse size bucket so AIS-exempt small craft are not flagged as evaders. |

---

## 0. Reality check

**This is one of the hardest problem statements in the SIH 2026 set.** It is not one project — it is four, integrated:

1. A SAR computer-vision system (remote sensing + deep learning)
2. A Lagrangian ocean transport model (physical oceanography + numerical modelling)
3. A spatio-temporal fusion and forensic scoring engine (AIS + geospatial data engineering)
4. A production-grade web GIS with time-series playback

Any one is a respectable final-year project. NTRO has asked for all four, with an interface.

**Honest assessment:** buildable to a convincing prototype by December; **not** buildable to operational accuracy. The gap between "prototype that wins SIH" and "system NTRO would deploy" is roughly two years of work and access to data we do not have. That is fine — judges reward a working, well-understood prototype with an honest error budget over a polished demo that overclaims. But we must know which one we are building, and say so on stage.

### What will go wrong if we do not plan for it

| Risk | Why it bites |
|---|---|
| Training on Mediterranean data, testing on the Arabian Sea | Documented degradation from ~67.8% to ~51.8% mIoU when Mediterranean-pretrained models move to Peruvian waters. Domain shift in SAR is brutal. Expect the same or worse. |
| No real historical AIS for Indian waters | MarineCadastre is US-only. AISStream and AISHub are live-only, terrestrial-only, **and AISStream offers no SLA and no durable replay** — messages not persisted are gone. Kpler/Spire are paid. **The PS explicitly permits synthetic AIS. Plan for it from day one.** |
| SNAP/snappy install kills a week | ESA SNAP + snappy on Windows is a known time sink. There is a route around it (§6.1). Take it. |
| OpenDrift on Windows | Conda dependency hell. WSL2 + Docker from the start. |
| Ocean currents too coarse to backtrack | Best free global product is 1/12° (~8 km). Slicks are shaped by sub-kilometre eddies. The backtrack cone widens fast. **A physics limit, not a bug — quantify it, do not hide it.** |
| Six people, one repo, no CI | Integration is the actual failure mode of SIH teams, not algorithms. |

**Team-specific note:** the person who owns SAR segmentation must be the strongest PyTorch person, and must not also own backend integration. Six roles, six people — §12.

---

## 1. What NTRO is actually asking for

NTRO is a technical intelligence agency. Read the PS as an intelligence requirement, not an environmental one:

> *Given a satellite radar image of the sea, tell me (a) whether there is illegal oil in it, (b) where and when it came from, and (c) which ship put it there — with enough rigour that I can act on it.*

| PS clause | Operational meaning | Difficulty |
|---|---|---|
| (a) Detect and characterise the spill, geometric properties, **age if feasible** | Segment the slick; compute area, perimeter, orientation, thickness proxy. "Age if feasible" is the PS authors signalling they know this is hard. | Medium |
| (b) Trace the slick backward to origin point and time; predict forward flow | Hindcast + forecast with ocean/met forcing. The **backward** direction is the hard, novel half. | Hard |
| (c) Reconstruct vessel traffic, filter irrelevant traffic, score suspects on proximity, trajectory, behavioural anomalies | The forensic core. This is what makes the system *intelligence* rather than *monitoring*. | Hard — **and where we win** |

**Where the marks are.** Most teams taking this PS will do: U-Net on a public dataset → polygon on Leaflet → nearest AIS ship → guilty. That is a demo, not a solution, and a competent jury breaks it with one question: *"The image is six hours old. The ship that did it is 80 nautical miles away. Your 'nearest ship' is an innocent bystander."*

Our differentiation is (b) and (c) done properly — §4, §8, §9.

---

## 2. Domain primer — the physics

Condensed here; the full treatment is in [`DOMAIN_PRIMER.md`](DOMAIN_PRIMER.md). **NTRO juries include remote-sensing people.** If the presenter cannot explain why oil is dark in SAR, the F1 score is irrelevant.

### 2.1 Why oil is visible

SAR measures **backscatter** (σ⁰). Over water the dominant mechanism is **Bragg scattering** — radar pulses resonate with capillary and short gravity waves whose wavelength is comparable to the radar wavelength (C-band ≈ 5.6 cm) travelling along the range direction. Wind creates those waves.

Oil films lower surface tension and dampen those gravity–capillary waves (Marangoni damping). Fewer Bragg scatterers → less returned energy → **dark patch**. That is the entire physical basis of the field.

### 2.2 The wind window — the key operational constraint

- **Below ~2–3 m/s:** the sea is glassy, backscatter approaches the noise floor, and the slick has nothing to contrast against. Everything looks like oil.
- **Above ~7–12 m/s:** waves overwhelm the damping, the slick breaks up and mixes down, and the signature vanishes.

**Design consequence:** ingest wind speed with every scene and use it as a gate. A detection at 1.5 m/s or 14 m/s must be automatically down-weighted and flagged. This alone puts us ahead of most teams and is cheap to implement.

### 2.3 Look-alikes — the actual problem

Low-wind zones, biogenic films, internal waves, atmospheric gravity waves, upwelling, rain cells, eddies, land-breeze fronts, ship wakes and RFI all produce dark patches. Full signature table in [`DOMAIN_PRIMER.md`](DOMAIN_PRIMER.md).

**Design consequence:** a pure pixel classifier will never solve this, because the discriminating information is not in the pixels — it is in the **auxiliary context**: wind, SST, chlorophyll, bathymetry, distance to coast, recurrence at that location, and proximity to a plausible source. Hence the two-stage design: **CNN proposes, physics disposes** (§7.4).

**New in v2.0:** 2025–26 literature converges on **edge/boundary prominence** as a primary oil-vs-look-alike discriminator — mineral oil slicks have sharper boundaries than biogenic films or wind shadows. This is cheap to exploit two ways: a boundary-gradient term in the segmentation loss, and an explicit edge-sharpness feature in the Stage C filter. Do both.

### 2.4 Polarisation

Sentinel-1 IW gives **VV + VH** dual-pol over most seas. VV (co-pol) has much higher backscatter and is the workhorse. VH (cross-pol) sits near the noise floor over calm water, so it is noisy — but the fact that VH is nearly noise-limited *inside* a slick is itself a weak discriminator. Use both channels; do not expect much from VH.

### 2.5 Slick age — the honest answer

**Age cannot be measured from a single SAR scene.** Oil evaporates, emulsifies, disperses and thins; weathered films damp less, so contrast *correlates* with age — but is confounded by wind speed, incidence angle, oil type and volume, none of which we know.

**The reframing, and it is a strong one:**

> Age is not measured from the image. Age is *inferred* as the release time that makes the observed slick geometry consistent with the drift field. It falls out of the attribution solve as a by-product.

This is how operational European polluter-identification works. Saying exactly this turns "age if feasible" from a weakness into a designed output with an uncertainty band.

---

## 3. Prior art — and the gap we fill

| System | What it does | Gap |
|---|---|---|
| **EMSA CleanSeaNet** (EU, operational since 2007) | SAR oil detection across European waters; alerts coastal states; correlates with AIS where a ship is adjacent | Human analyst in the loop; **fails on "orphan" spills** with no ship attached; does not cover Indian waters |
| **INCOIS OOSA v5.0** + **SARAT** | Operational Indian services. OOSA runs trajectory modelling forced by Indian regional ocean products, upgraded in 2025 with advanced GIS and predictive capability; SARAT computes probable drift paths and was activated for MSC ELSA 3 and Wan Hai 503 | **Forward-only**, and a human must *tell it where the spill is*. No detection. No attribution. |
| **SeaVision** (US, 100+ countries) | Maritime domain awareness platform; renders AIS-broadcasting vessels and uncorrelated SAR detections (dark vessels) | Vessel-presence focused; no oil-spill detection, no drift-based attribution |
| **Commercial MDA suites** (Kongsberg and peers) | SAR detection + AIS cross-reference + replay | Closed, foreign, expensive; operator-driven; no automated scoring |
| **Forward-drift-from-all-vessels polluter ID** (published operational concept, Northern Europe) | Simulate a spill from *every* vessel track, see whose plume matches the observed slick | The correct method — and almost nobody outside Northern Europe implements it. **Our architectural anchor.** |
| **DarkVesselNet and 2025–26 dark-vessel literature** | Multi-modal SAR + trajectory reasoning for non-cooperative vessels | Detects dark vessels; does not connect them to a pollution event |

**The Indian gap, in one sentence for the slide:**

> India has an operational forward trajectory model (INCOIS OOSA v5.0) and an operational response authority (ICG under NOSDCP), but no automated pipeline closing the loop from *satellite pixel → slick → origin → named vessel*. Every attribution today is manual, slow, and usually never happens.

**Indian regulatory frame** — learn these names, they earn credibility:

- **NOSDCP** — National Oil Spill Disaster Contingency Plan; ICG is the central coordinating authority; Tier 1/2/3 escalation.
- **MARPOL Annex I** — makes operational discharge illegal. *Verify exact thresholds against the IMO text before quoting numbers on stage.*
- **INCOIS** — data and modelling arm; the natural interoperability target.
- **Kerala High Court proceedings (2025)** against the owners of MSC ELSA 3 and Wan Hai 503 — live evidence that Indian courts are actively pursuing vessel accountability for marine pollution. This is the real-world justification for the evidence-dossier deliverable (M7). **Use it.**

---

## 4. Product definition

### 4.1 One line

SAGARDRISHTI ingests Sentinel-1 SAR scenes over Indian waters, automatically detects and characterises oil slicks, reconstructs where and when the oil entered the water with a quantified uncertainty envelope, and ranks the vessels that could have put it there — producing an auditable evidence dossier for the Indian Coast Guard.

### 4.2 Users

| User | Need | What they get |
|---|---|---|
| **ICG Maritime Operations Centre watchkeeper** | "Is there a spill in my AOR right now?" | Automated alert queue, map, confidence score |
| **ICG / NTRO analyst** | "Who did it, and can I defend that conclusion?" | Ranked suspects with per-factor explanations, drift animation, evidence pack |
| **Pollution response planner** | "Where will it be in 24 hours? What coast is at risk?" | Forward forecast, shoreline impact probability, eco-sensitive zone overlay |
| **Legal / enforcement** | "Will this survive challenge?" | Signed, hash-provenanced dossier with full model and data lineage |

### 4.3 Product principles — non-negotiable

1. **Rank, never accuse.** Output is a ranked probability list with explicit uncertainty. The system never says "Vessel X is guilty." It says "Vessel X is the most drift-consistent candidate, at 0.71 posterior, driven by these five factors." Scientifically correct, legally survivable, and juries reward it.
2. **Every number has an error bar.** No point estimates for origin. Ever. Probability fields.
3. **Explainable over accurate.** An intelligence user must be able to audit the reasoning. A black-box neural attribution score is worthless to NTRO. Transparent documented weights beat an under-trained learned model at our data volumes.
4. **Physics gates the ML.** The network proposes candidates; environmental context confirms or rejects them.
5. **Degrade gracefully.** No AIS → still produce origin plus dark-vessel candidates from SAR ship detection. No currents → wind-only drift with a wider cone and a visible warning. The system must never simply fail.
6. **The interface is evidence, not decoration.** *(new in v2.0)* Every visual element must carry information an analyst can act on. Uncertainty is always rendered, never flattened into a single confident marker.

### 4.4 Scope — explicitly IN

- Sentinel-1 IW GRD, VV+VH, Indian EEZ focus
- Slick segmentation, look-alike rejection, geometric characterisation
- Backward hindcast (probabilistic origin field) and forward forecast
- AIS ingestion (real where available; synthetic generator for Indian waters)
- Forward-drift-from-every-vessel attribution and multi-factor suspect scoring
- SAR ship detection with AIS cross-matching → dark vessel flagging
- Web GIS operator console with time playback
- Signed evidence dossier export
- **NISAR L-band ingest as a demonstrated second sensor path** *(new in v2.0 — stretch goal, see §6.2)*

### 4.5 Scope — explicitly OUT

State this on stage; scoping discipline scores points.

- Real-time tasking of satellites
- Optical/EO fusion beyond a Sentinel-2 quicklook overlay (nice-to-have, cut first)
- Oil *type* classification from SAR — not reliably possible; needs hyperspectral or fluorosensor
- Volume estimation in tonnes — thickness retrieval from C-band SAR is unsolved; relative thickness classes at most
- Anything requiring classified or paid data
- Mobile app
- **Super-resolution of SAR prior to detection** — see [`adr/0004-no-super-resolution.md`](adr/0004-no-super-resolution.md)

---

## 5. Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full treatment and module contracts. Summary in the [root README](../README.md).

Seven modules: **M1** preprocess → **M2** detect (3 stages) → **M3** characterise → **M4** ship detect → **M5** drift engine → **M6** attribution → **M7** evidence. Served by FastAPI over PostGIS + TimescaleDB with a Redis/ARQ queue and TiTiler for raster tiles, to a React operator console.

---

## 6. Data strategy — the biggest risk, solved

Full detail with licences and fallbacks: [`DATA_SOURCES.md`](DATA_SOURCES.md).

### 6.1 Sentinel-1 imagery: skip SNAP

**The trap:** every tutorial says install ESA SNAP and use `snappy` for orbit → border noise → thermal noise → calibration → speckle → terrain correction. On Windows this costs a week and still hits JVM/Python bridge issues.

**The route around it:** the **Copernicus Data Space Ecosystem (CDSE) Sentinel Hub Processing API** returns Sentinel-1 GRD **already calibrated and thermal-noise-removed**, optionally speckle-filtered and orthorectified, as a GeoTIFF for a given AOI and time window, in one HTTP request. Free tier is **10,000 Processing Units per month** per account; openEO adds another 10,000 credits. A typical AOI request costs tens of PUs. We will not run out.

**Access ladder:**

1. **CDSE Sentinel Hub Process API** — primary. `sentinelhub-py`.
2. **CDSE STAC / OData catalogue** — discovery and raw product download when full-scene metadata is needed.
3. **openEO on CDSE** — batch processing in the cloud rather than on our GPUs.
4. **ASF DAAC** — NASA mirror for raw GRD download; **also the NISAR distribution point** (§6.2).
5. **Google Earth Engine `COPERNICUS/S1_GRD`** — rapid exploration only. Not the production path: it is terrain-corrected for land use, and it is a foreign commercial dependency NTRO will ask about.
6. **SNAP GPT via Docker** — reproducible offline fallback for the finale. Use the `gpt` CLI with an XML graph, never `snappy`.

**Constellation status, verified September 2026:** Sentinel-1A operations terminated **29 June 2026**. The final configuration is **Sentinel-1C + Sentinel-1D**, 6-day repeat between them, following an orbital reconfiguration in June 2026. Effective revisit over the Indian EEZ combining ascending and descending passes is roughly **1–3 days**.

> Quote this correctly. Teams saying "Sentinel-1A/1B, 6 days" are quoting 2021 and will be marked down.

### 6.2 NISAR — the sovereign angle *(new in v2.0)*

**NISAR (NASA–ISRO Synthetic Aperture Radar) L-band data became publicly available on 20 July 2026** through ASF DAAC and NASA Earthdata, covering acquisitions from 17 June 2026, with the full science record expected by end-2026. It carries **L-band (24 cm)** and **S-band (9.4 cm)** SARs; the S-band exists specifically to serve Indian science priorities including coastal applications.

**Why this matters more than its technical contribution:**

- It is a mission **India co-owns**. For NTRO, "our pipeline ingests NISAR" reframes the entire data-sovereignty question that would otherwise be the hardest one asked.
- L-band behaves differently from C-band for slick damping. We are not claiming a validated L-band oil detector — that is a research problem. We are claiming a **sensor-agnostic ingest path**, demonstrated on real NISAR data.
- The mission is new enough that no other team will have touched it.

**Scope discipline:** NISAR is a **stretch goal, Phase 2 at the earliest.** The commitment is a working ingest and preprocessing path plus a qualitative comparison over a common AOI — *not* a trained L-band detector. If Phase 1 slips, cut this first and say so. Do not let it compromise the Sentinel-1 spine.

### 6.3 Training data for detection

| Dataset | Contents | Access | Verdict |
|---|---|---|---|
| **Trujillo-Acatitla et al. Sentinel-1 SAR Oil Spill dataset** — Zenodo DOIs `10.5281/zenodo.8346860` (Part I), `8253899` (Part II), `13761290` (Part III) | 2048×2048×2 (VV, VH) σ⁰ dB GeoTIFF, **georeferenced**; 1200 oil + 685 no-oil train/val; 150/150/150 test | Open | **Primary.** The dataset the PS itself links. Georeferenced dual-pol dB is exactly our production format. |
| **Yang & Singha (DLR) Eastern Mediterranean dataset** — PANGAEA `10.1594/PANGAEA.980773`, ESSD 17, 6807–6837 (2025) | 1365 patches / 3225 **object-level** annotations + 2290 no-oil patches, K-means clustered **by look-alike type**; 640×640, VV | Open, CC-BY | **Best-in-class for Stage A detection and look-alike ablation.** The clustered no-oil set lets us report *which kind* of look-alike we fail on. Nobody else at SIH will do this. |
| **Refined Deep-SAR Oil Spill (SOS)** — Zenodo `10.5281/zenodo.15298010` | ALOS PALSAR (Gulf of Mexico) + Sentinel-1 (Persian Gulf), 256×256, ~8k images; ~38% of train masks manually corrected | Open | **Use the refined version.** The Persian Gulf split is climatically closer to Indian waters than the Mediterranean — our best proxy for domain transfer. |
| **Krestenitis / MKLab "OSD"** | ~1002 train / 110 test, 5 classes (oil, look-alike, land, ship, sea); sourced from EMSA CleanSeaNet | **Request required** | Submit on day 1 — it is the standard benchmark, so having it makes our numbers comparable to published work. **Do not block on it.** |
| **SSDD / HRSID / LS-SSDD-v1.0** | SAR ship detection | Open | For M4. |

**Realistic accuracy targets.**

2025–26 papers report high numbers — FCS-Net at 87.8–89.6% mIoU, ensemble methods claiming higher still. Treat these with care: they are often single-dataset, single-basin, and not directly comparable across splits. **We target defensible numbers on stated splits and report our cross-domain drop.**

| Dataset | Published range | Our target | What we claim |
|---|---|---|---|
| Krestenitis/M4D (5-class) | oil IoU ~54–64%, mIoU ~65–78% | mIoU 70–76% | "Comparable to published baselines" |
| SOS (binary) | mIoU 80–89% | mIoU 82–86% | Fine to state |
| Zenodo/Trujillo | Varies | oil IoU 60–70% | Fine to state |
| **Cross-domain (Med → Gulf/Indian)** | **~68% → ~52% mIoU documented** | **Expect a 10–20 point drop** | **Report it explicitly. A credibility move, not a weakness.** |

### 6.4 The AIS problem — and the answer

**There is no free source of bulk historical AIS for Indian waters.** Face this now.

| Source | Gives | Usable? |
|---|---|---|
| **NOAA MarineCadastre** (the PS's own link) | Excellent, free, bulk historical CSV — **US waters only** | **Yes — for format definition and method validation.** Build and validate the entire attribution engine on real US tracks, then apply to Indian synthetic data. |
| **AISStream.io** | Free WebSocket, live, bounding-box subscribe, terrestrial only. **No SLA, no durable replay** — unpersisted messages are lost | **Yes — start recording the Arabian Sea and Bay of Bengal today.** By December that is three months of *real Indian AIS*. **The single highest-leverage action in this document.** Write to disk on receipt; reconnect with backoff. |
| **AISHub** | Free but requires contributing a receiver feed | Impractical |
| Kpler / Spire / Datalastic | Full satellite + terrestrial historical | Paid, out of scope. Note the 2026 market consolidation on the slide — it strengthens the case for indigenous capability |
| **Global Fishing Watch API** | Free for research; AIS-derived presence and events | Worth a look for fishing-traffic context |
| **Synthetic generator (ours)** | Physically plausible tracks in our AOI | **Required. Build it properly.** |

**Synthetic AIS generator — build to a real standard, not as a toy.** Explicitly permitted by the PS, and done well it is a deliverable in its own right:

1. Extract real lane geometry from the AISStream recordings we start collecting now (KDE of positions → lane centrelines → widths).
2. Sample vessel types from realistic Indian-waters distributions (tanker / container / bulker / fishing / tug).
3. Generate tracks along lanes with realistic per-type SOG distributions, COG jitter, and reporting intervals (Class A: 2–10 s underway, 3 min at anchor — decimated to reflect terrestrial receiver gaps).
4. Emit valid **AIS message types 1/2/3, 5, 18/19, 24** with correct field encoding, so the ingest path is identical for real and synthetic data.
5. Inject labelled ground-truth discharge events with known vessel, time, location and rate — **our only source of attribution ground truth, and therefore our only way to compute attribution accuracy.**
6. Inject realistic confounders: AIS gaps, MMSI spoofing and duplication, position jumps, innocent vessels passing near the slick.

**Framing for the viva:**

> *We validate the attribution engine against real AIS on the NOAA US dataset, where independent tracks exist. We demonstrate on Indian waters using a synthetic generator calibrated to lane geometry we recorded live from AISStream, because bulk historical Indian AIS is not publicly available — which is itself part of the capability gap this PS exists to close.*

### 6.5 Ocean and meteorological forcing

All free via the `copernicusmarine` toolbox:

| Variable | Product | Resolution |
|---|---|---|
| Surface currents (analysis + forecast) | `GLOBAL_ANALYSISFORECAST_PHY_001_024` | 1/12° (~8 km), hourly |
| Surface currents (obs-based, geostrophic + Ekman) | `MULTIOBS_GLO_PHY_MYNRT_015_003` | 1/4°, hourly, 0 m and 15 m |
| Waves + **Stokes drift** | `GLOBAL_ANALYSISFORECAST_WAV_001_027` | 3-hourly |
| Sea surface wind (L4) | `WIND_GLO_PHY_L4_*` | 0.125°, hourly |
| SST, chlorophyll-a (look-alike discrimination) | CMEMS SST and OC products | Daily |
| Wind (reanalysis alternative) | ECMWF **ERA5** via CDS | 0.25°, hourly |
| Bathymetry (internal-wave context) | **GEBCO** 15 arcsec | ~450 m |

**Put the resolution mismatch on a slide.** SAR resolves the slick at 10–40 m; the best free currents are ~8 km. We are advecting a metre-scale feature with a field that cannot see anything smaller than a city. Sub-mesoscale eddies (100 m – 10 km), which visibly control slick shape, are entirely unresolved.

**This is the dominant term in the error budget. It is a physics limit, not an engineering failure, and stating it clearly is worth more than hiding it.** Mitigation: ensembles with stochastic diffusion (§7.7), plus the observation that INCOIS's higher-resolution regional setup measurably outperforms the global product for the Indian west coast — a natural operational-integration slide.

### 6.6 Reference incidents for demo

| Incident | Date | Why it is good |
|---|---|---|
| **MSC ELSA 3** | 25 May 2025, off Kochi | Recent, Indian, high-profile. Known vessel; ICG confirmed slick within hours; INCOIS activated SARAT and its oil/nurdle trajectory system; real AIS track exists. **Ground-truth polluter is known.** Best headline demo. |
| **Wan Hai 503** | June 2025, off Kerala | *(new in v2.0)* Fire and hazardous cargo loss weeks after ELSA 3. Together these triggered a Kerala state contingency overhaul and **High Court proceedings against both owners** — the live legal context for our evidence dossier. |
| **Ennore collision** | 28 Jan 2017 | ~196 t heavy furnace oil. **INCOIS published a trajectory-vs-Sentinel-1A validation of this exact case** — lets us benchmark our drift model against a peer-reviewed Indian result. |
| **MV Rak Carrier** | Aug 2011, off Mumbai | Covered in INCOIS drift-model literature |
| **Deepwater Horizon** | 2010 | Pre-Sentinel-1; training data only (present in the SOS dataset) |

### 6.7 Offline contingency — non-negotiable for the finale

**Assume nodal-centre Wi-Fi fails.** By 15 November everything must run from local cache: 5–10 preprocessed S1 scenes, corresponding forcing subsets as local NetCDF, corresponding AIS as a PostGIS dump, model weights, Docker images, and all Python wheels vendored — reachable via `docker compose up` with zero network calls.

**Test by physically disconnecting the machine. Twice.** See [`OFFLINE_MODE.md`](OFFLINE_MODE.md).

---

## 7. Module specifications

Contracts and I/O schemas: [`ARCHITECTURE.md`](ARCHITECTURE.md). Each package carries its own README.

### 7.1 M1 — SAR preprocessing

```
GRD product
 → apply orbit (bundled restituted orbits are fine for GRD)
 → GRD border noise removal
 → thermal noise removal
 → radiometric calibration → σ⁰
 → multilook / resample to FIXED 40 m/px          ← see note
 → convert to dB
 → land mask (GSHHG or OSM coastline, buffered 500 m)
 → per-scene normalisation
 → tile 512×512 with 64 px overlap
 → Cloud-Optimised GeoTIFF + STAC item
```

**The fixed-resolution note is the most important line in this section.** Public oil-spill datasets were built at *different* effective ground resolutions. Train on patches at ~80 m/px and infer on tiles at 10 m/px and the model sees slicks at the wrong scale and fails silently — the loss curve looks fine, field performance is garbage.

> **Resample every training patch and every inference tile to the same ground sample distance (40 m/px) and log it in the model card.** Most teams miss this. Raise it in the viva.

40 m/px also collapses a full IW GRD scene from ~420 Mpx to ~26 Mpx, cutting inference from minutes to seconds. Slicks are hundreds of metres across; nothing is lost.

**Normalisation:** sigmoid stretch with β = scene median and α = 3σ, or clip to [median − 3σ, median + 3σ] then min-max. Pick one, apply identically at train and inference, log it.

### 7.2 M2 Stage A — dark formation proposals

Cheap, fast, high recall, low precision. Purpose: avoid running a heavy network over 100% ocean.

- Adaptive thresholding on σ⁰ dB (local median − k·MAD), or a small object detector trained on the Yang/Singha bbox set (YOLO-family or Faster R-CNN, 640×640).
- Morphological cleanup, connected components, area filter (drop < ~0.1 km²).
- Output: candidate boxes → only these go to Stage B.

Mirrors the two-step approach used in near-real-time operational systems; defensible on efficiency grounds.

### 7.3 M2 Stage B — semantic segmentation

**Primary: SegFormer-B2** (HuggingFace `transformers`). **Baseline: DeepLabv3+ / ResNet-50** (`segmentation_models_pytorch`).

Justification:

- Transformer baselines consistently top pixel-level IoU tables on these datasets.
- SegFormer-B2 fits comfortably in 12 GB with AMP at 512², batch 8–16.
- `smp` DeepLabv3+ is ~20 lines and gives weaker team members a working baseline in an afternoon.
- **Do not chase Mamba/SAM2-based SOTA** (OSDMamba, OilSAM2, FCS-Net). They consume the timeline for a few IoU points no jury will ask about.

**Classes:** `sea` / `oil` / `look-alike` / `land` / `ship` — 5-class, matching M4D so numbers are comparable. Fall back to binary plus a separate look-alike head if 5-class training proves unstable.

**Loss:** class imbalance is severe (oil is often <1% of pixels). **Focal + Dice/Jaccard**, plus a **boundary-gradient term** — *elevated from "optional ablation" in v1.0 to recommended in v2.0*, since 2025–26 work identifies edge prominence as a primary oil-vs-look-alike discriminator.

**Augmentation:** flips, 90° rotations, multiplicative speckle (gamma noise), σ⁰ level shift (±2 dB, simulating different wind), incidence-angle-like linear gradient. **Never** colour jitter or elastic deformation — physically meaningless for SAR.

**Training start point:** AdamW, lr 6e-5 (SegFormer) / 1e-3 (CNN), cosine schedule, 100 epochs, batch 8 @ 512², AMP, gradient accumulation ×2 on the 8 GB card.

### 7.4 M2 Stage C — physics and context filter *(the differentiator)*

Every Stage B detection is scored against auxiliary evidence before promotion to a confirmed slick:

| Check | Data | Effect |
|---|---|---|
| Wind speed at centroid within 2–12 m/s | CMEMS / ERA5 | Outside → heavy penalty, reason logged |
| Chlorophyll-a anomaly high | CMEMS OC | Biogenic film likely → penalty |
| SST cold anomaly | CMEMS SST | Upwelling likely → penalty |
| Steep bathymetric gradient + banded morphology | GEBCO + shape | Internal wave likely → penalty |
| Recurring dark formations at this location | Our own detection archive | Persistent look-alike → heavy penalty |
| Precipitation at location | ERA5 total precipitation | Rain cell likely → penalty |
| Damping ratio (σ⁰ background / σ⁰ slick, dB) | Computed | Higher → more likely mineral oil |
| **Edge sharpness / boundary gradient** | Computed | *(new in v2.0)* Sharp boundary → more likely mineral oil |
| Shape complexity P²/4πA, elongation | Computed | Elongated + sharp + complex → likely discharge trail |
| Proximity to vessel or platform | AIS + platform layers | Boosts confidence, gives an immediate candidate |

Combine into a transparent confidence score. **Report every applied penalty in the UI** — *"confidence reduced 0.62 → 0.19: wind speed 1.6 m/s below detection window"*. This turns a hidden failure into visible competence, and it is the single best moment in the demo.

### 7.5 M3 — characterisation

Per slick: area (km²), perimeter, centroid (WGS84), **major-axis bearing** (critical — a discharge trail aligns with the ship's course), minor axis, eccentricity, complexity index, convex-hull deficiency, mean/std σ⁰ inside and in a background annulus, damping ratio (dB), edge-sharpness metric, relative thickness class, and the **inferred age with uncertainty** (written back by M6).

### 7.6 M4 — SAR ship detection and dark-vessel flagging

Ships are bright point targets against dark water — far easier than oil.

- **Two-parameter CFAR** on σ⁰ with guard cells (classical, explainable, no training data needed), or a small YOLO trained on SSDD / HRSID / LS-SSDD-v1.0.
- Estimate heading from wake orientation where present (Radon/Hough on the wake region).
- Cross-match each SAR detection against AIS interpolated to the exact acquisition timestamp, with matching radius scaled by reporting gap and vessel speed.
- **Unmatched SAR detection = dark vessel.** Flag prominently.

**Size bucket — a soft flag, not a rule.** Estimate a coarse size class from the radar cross-section of the blob: `small` / `medium` / `large`. A small radar return is likely a small craft, and **many small vessels are legally exempt from carrying AIS at all** — a fishing boat below the carriage threshold is not an evader, it is a boat.

Without this, every small unidentified vessel gets flagged as suspicious and the dark-vessel list fills with legitimate traffic, which destroys its usefulness. With it, the analyst sees "small craft, likely AIS-exempt" and can deprioritise accordingly.

Keep it coarse deliberately: we have no training data for precise vessel classification, and three buckets is all the evidence supports. Claiming vessel *type* from a radar blob would be overreach. The bucket is displayed to the analyst as context; it never hard-filters a detection out of the list.

High value for NTRO specifically, comparatively cheap. **Do not cut it.**

### 7.7 M5 — drift engine

**OpenDrift + OpenOil** — open source, Python, actively maintained, peer-reviewed (Dagestad et al. 2018, GMD; Röhrs et al. 2018, Ocean Science). Runs backwards with a negative timestep. NOAA GNOME is the alternative and what INCOIS uses operationally, but OpenDrift's Python API is far easier to embed.

**Three run modes:**

**(a) Backward hindcast → origin probability field.** Seed N particles uniformly across the observed slick polygon at acquisition time; run backwards. **Disable weathering** — evaporation and emulsification are irreversible and running them backwards is physically meaningless. Output: for each hour back, a 2D probability density of possible origin. Not a point. A cone that widens with time.

**(b) Forward forecast.** Seed the slick, run forward 24/48/72 h with full weathering (evaporation, emulsification, vertical mixing, film-thickness update). Output: predicted extent, shoreline impact probability, eco-sensitive zone intersection.

**(c) Per-vessel forward drift.** §8 — the attribution core.

**Ensemble for uncertainty.** A single deterministic run is worthless. Run ≥100 members perturbing:

- wind drift factor — uniform in [0.02, 0.04] (the physical range)
- current field — ±10–20% magnitude and small rotation, or swap between the 1/12° model and 1/4° observational products
- horizontal diffusivity — sampled across a plausible range
- Stokes drift on/off

**The spread of the ensemble is the uncertainty estimate.** Render it as a heatmap.

*Validation reference:* published OpenOil case studies report centroid skill scores of 0.89–0.98 under favourable conditions. That is our benchmark, not our promise.

---

## 8. M6 — Attribution (the part that wins)

Full weight justification: [`SCORING_MODEL.md`](SCORING_MODEL.md).

### 8.1 Why naive backtracking is the wrong primary method

Backtracking requires knowing **when** the oil was released, to know how far back to run. We don't. Run back 6 hours, get one origin; 18 hours, a completely different one. Backtracking alone yields a family of answers with no way to choose among them.

### 8.2 The correct method — forward drift from every candidate vessel

> **Assume every vessel might have discharged at every moment along its track. Simulate all of it forward to the SAR acquisition time. Whoever's simulated plume lands on the observed slick is the suspect — and the release time that fits tells you the age.**

Elegant, correct, and it solves the age problem for free.

```
Given:  S     = observed slick polygon, at time T_sar
        A     = AIS tracks in the region
        T_max = maximum plausible slick age (start 24 h, tune)

1. SPATIO-TEMPORAL GATE   (the PS explicitly asks for this)
   Run the backward ensemble T_max hours to get reachability region R.
   Keep only vessels whose track intersects R within [T_sar - T_max, T_sar].
   Typically cuts hundreds of vessels to tens.

2. SEED
   For each surviving vessel v:
     Interpolate its track to 15-minute steps (great-circle + SOG/COG,
     never naive linear interpolation across long gaps).
     For each step t_i, seed K particles at that position, tagged (v, t_i).

   >>> KEY IMPLEMENTATION POINT <<<
   All particles from all vessels and all release times go into ONE
   OpenDrift run. Particles are independent and OpenDrift supports
   staggered seed times. This turns O(vessels x times) simulations into
   a single simulation. Without this, attribution is too slow to demo live.

3. ADVECT
   Run forward to T_sar, ensembled over the §7.7 perturbations.

4. SCORE OVERLAP   (per vessel, per release time)
   hit(v, t_i)      = fraction of (v,t_i) particles landing inside S
   coverage(v, t_i) = fraction of S covered by the KDE of (v,t_i)
                      particles above a density threshold
   drift_score(v)   = max over t_i of  2·hit·coverage / (hit + coverage)
   t*(v)            = argmax t_i
   AGE ESTIMATE     = T_sar - t*(v), with a band from ensemble spread

   Why the harmonic mean: `hit` alone rewards a vessel whose plume is a
   tiny dot inside a huge slick; `coverage` alone rewards a vessel that
   smears everywhere. The F-measure penalises both failure modes.
```

**Backtracking is still built** — it produces the origin probability field for the map, it handles the **dark-vessel case** where there is no AIS track to drift forward from, and it is what the PS literally asks for. But it is the secondary product. Saying this on stage demonstrates understanding of the problem rather than of the tutorial.

### 8.3 The suspect scoring model

`drift_score` is necessary but not sufficient — in a busy lane several vessels will be drift-consistent. Combine evidence in **log-odds**: transparent, additive, auditable.

```
logit(P_suspect) = w0
                 + w1 · f_drift       drift consistency (§8.2)
                 + w2 · f_alignment   |cos(slick major-axis bearing − vessel COG at t*)|
                 + w3 · f_speed       SOG at t* vs that vessel's own median SOG
                                      (operational discharge is typically done at
                                       reduced, steady speed)
                 + w4 · f_gap         AIS GAP ANOMALY — deviation from THIS vessel's
                                      own baseline gap behaviour, discounted by
                                      expected coverage. NOT "a gap exists". See §8.5
                 + w5 · f_course      course-change magnitude near t*
                 + w6 · f_night       local solar elevation < 0 at t*
                 + w7 · f_offlane     distance from the traffic-lane KDE ridge
                 + w8 · f_type        vessel-type prior (tanker > bulk > container > fishing)
                 + w9 · f_context     distance to port / platform; proximity to protected area
```

**Do not train this end-to-end with a neural network.** We will have on the order of tens of labelled attribution events. That is not enough to learn ten weights reliably, and a black box is worthless to an intelligence user.

Instead:

1. Hand-set defensible initial weights, each justified in writing in [`SCORING_MODEL.md`](SCORING_MODEL.md).
2. Fit a **logistic regression** on synthetic labelled events to refine them.
3. **Calibrate** with Platt scaling or isotonic regression so that "0.7" means close to "70% of the time this is the right vessel."
4. Render **per-factor contribution bars** in the UI for every suspect. This is the explainability story and it takes an afternoon.

Report **top-1 and top-3 accuracy** plus **mean reciprocal rank**. Top-3 is the honest operational metric: an ICG analyst investigating three vessels instead of two hundred is an enormous win, and framing it that way is far more persuasive than claiming 95% top-1.

### 8.4 Filtering irrelevant traffic — explicit PS requirement

Cascade, cheapest filter first:

1. **Reachability gate** (§8.2 step 1) — geometric, kills the majority
2. **Timing gate** — vessel must be present during a plausible release window
3. **Kinematic plausibility** — a vessel at 22 kn crossing perpendicular to the slick's long axis is a poor fit
4. **Drift-score floor** — below threshold, drop
5. **Type prior** — never a hard filter (small vessels do discharge), only a weight

**Log every drop reason.** *"Filtered 214 vessels → 7 candidates"* with an expandable audit trail is a genuinely impressive UI moment and directly answers the PS.

### 8.5 AIS data quality and the gap factor *(new in v2.0)*

> **The naive version of f₄ — "a gap exists near the spill, therefore suspicious" — is wrong, and it produces false accusations.** It is the most dangerous single component in this system, because its errors fall hardest on the operators least able to contest them: small and older fishing vessels with cheap transponders, and any vessel legitimately working offshore.

AIS gaps have at least four causes and only one of them is evidence.

| Cause | Frequency | Evidence? |
|---|---|---|
| Cheap, old or misconfigured transponder dropping out | Very common, especially small craft | **No** — it happens everywhere, always, not just near this spill |
| Vessel beyond terrestrial receiver range (~40–75 nm) | Very common offshore | **No** — that is radio physics |
| Bad data: MMSI 0, reused MMSI, GPS stuck at (0,0), impossible speed jumps, blank static fields | Common, well documented | **No** — that is a data quality defect |
| Deliberate shutdown at an unusual time and place, by a vessel that otherwise reports reliably, in good coverage | Rare | **Yes** — this is the signal |

Four corrections, **all required**. Full specification and weight justification in [`SCORING_MODEL.md`](SCORING_MODEL.md) §2.1.

**(a) Data quality pre-filter — a pipeline step, before any scoring.** Records are labelled `data_quality: unreliable` and excluded from the confident evidence set when they show MMSI 0 or structurally invalid, position stuck at (0,0), implied speed between consecutive fixes that is kinematically impossible for the vessel type (a merchant vessel does not travel at 45 knots), or blank/garbled static voyage data.

> **Excluded records neither boost nor penalise a score.** They are removed from the evidence set, never converted into negative evidence. A vessel must never become a suspect *because* its transponder is broken — that inverts the logic of the entire system.

**(b) Per-vessel baseline gap profile** — computed once per MMSI from prior weeks, cached in `ais_baseline_profiles`. Suspicion is measured as deviation from **that vessel's own normal behaviour**. A vessel that routinely drops out for hours scores low even with a gap near the spill; a vessel that has reported like clockwork for months and then has one gap at the inferred release time scores high. Without this, f₄ measures transponder quality rather than behaviour.

**(c) Coarse coverage proxy** — distance-to-coast against a terrestrial-AIS threshold (~40–75 nm), discounting offshore gaps. **Deliberately simple: not a radio propagation model.** The extra accuracy is not worth the time and is harder to defend in a viva.

**(d) f₄ is never a standalone trigger.** It is one of nine weighted inputs. Drift consistency (w₁ = 2.5) dominates by design against an intercept of w₀ = −4.0, so f₄ at maximum contributes 1.3 — nowhere near enough to produce a suspect alone. **A vessel that could not physically have put oil where the oil is does not become a suspect because its transponder was quiet.**

### 8.6 The asymmetry that governs this module

**A wrongful accusation against an innocent vessel operator is a far worse outcome than a missed detection.**

This is a decision-support tool for human investigators, not an automated accusation system. Wherever a design choice trades false positives against false negatives, we take fewer flags with better evidence. That principle produces concrete rules, not just sentiment:

- Unreliable records are **excluded**, never converted into negative evidence
- A missing factor is **dropped**, never imputed — imputing fabricates evidence
- Vessel type is a weight, never a hard filter (small vessels do discharge)
- No single factor can independently produce a suspect
- Dark vessels are scored on their own scale, never ranked against AIS-scored vessels
- A vessel with no baseline history has f₄ marked **low-confidence in the UI**, never silently defaulted to the fleet average

The system's credibility rests on defensible, explainable, low-false-positive reasoning — not on raw detection rate. A system that flags fifty vessels to catch one is unusable by an ICG watchkeeper; a system that flags the wrong operator once is not trusted again.

---

## 9. Technology stack

| Layer | Choice | Why this, not the alternative |
|---|---|---|
| **Language — science & pipeline** | Python 3.11 | Non-negotiable — the geospatial, ML and ocean-modelling ecosystem is Python. PyTorch, rasterio, xarray, GeoPandas and OpenDrift have no Go equivalents |
| **Language — AIS data plane** | **Go 1.23** | *(new in v2.0)* The AIS recorder must run unattended for three months against a feed with **no SLA and no replay** — every dropped message is permanently lost. That is a long-running, IO-bound, reliability-critical network daemon, which is exactly what Go is for: goroutines for concurrent bounded-buffer writes, a ~12 MB static binary that deploys anywhere without a Python environment, and flat memory under sustained load. See [`adr/0005-go-for-the-ais-data-plane.md`](adr/0005-go-for-the-ais-data-plane.md) |
| **DL** | PyTorch 2.x + `segmentation_models_pytorch` + HF `transformers` | `smp` gets a baseline running in an afternoon; `transformers` gives SegFormer. **Not MMSegmentation** — its config system eats two days |
| **SAR I/O** | `rasterio`, `rioxarray`, `xarray`, `numpy`, GDAL | Standard |
| **SAR fetch** | `sentinelhub-py` (CDSE), `pystac-client` | Avoids SNAP entirely (§6.1) |
| **Drift** | **OpenDrift / OpenOil** | Python API, native backward runs, peer-reviewed. GNOME is INCOIS's choice but harder to embed |
| **Ocean/met** | `copernicusmarine`, `cdsapi` | Official clients |
| **Geospatial** | `geopandas`, `shapely` 2.x, `pyproj`, `scikit-image`, `opencv` | Standard |
| **AIS decode** | `pyais` | Handles NMEA/AIVDM types 1/2/3/5/18/19/24 properly |
| **API** | **FastAPI** + Pydantic v2 + Uvicorn | Async, auto OpenAPI docs — worth a slide |
| **DB** | **PostgreSQL 16 + PostGIS 3.4 + TimescaleDB** | PostGIS for polygons and spatial joins; TimescaleDB hypertables for AIS pings (millions of time-ordered rows — exactly its use case) |
| **Queue** | **Redis + ARQ** | Drift ensembles take minutes; the API must not block. **Not Kafka** — overkill, and a jury reads it as resume padding |
| **Object store** | MinIO or a local volume | COGs and NetCDF; a local volume is fine and simpler |
| **Tile serving** | `titiler` | Serves COGs as XYZ tiles. Saves writing a tile server |
| **Frontend** | **React 19 + Vite + TypeScript** | Standard |
| **Map** | **MapLibre GL JS 6 + deck.gl 9** | MapLibre for the basemap (open, no token, works offline with local tiles); deck.gl for GPU-rendered particle clouds and AIS tracks. **Not Leaflet** — it will not render 100k drifting particles smoothly, and that animation is the demo's best moment |
| **UI system** | **Blueprint 6 tokens + Radix/shadcn primitives + Tailwind** | *(rewritten in v2.0)* Blueprint is **Palantir's own open-source design system**, purpose-built for data-dense operator interfaces. We adopt its exact tokens, density and dark palette; we use Radix/shadcn primitives underneath for modern DX and use `@blueprintjs/table` where a virtualised operator-grade grid is genuinely needed. Full specification in [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) |
| **Charts** | visx or Recharts | Score breakdown bars, timelines |
| **Packaging** | **Docker + Docker Compose** | One-command bring-up. **Not Kubernetes** |
| **Dev env** | **WSL2 (Ubuntu 22.04)** | Non-negotiable. OpenDrift, GDAL and the conda geospatial stack are painful on native Windows. Week 1 |
| **Env mgmt** | `micromamba` (geo/OpenDrift), `uv` (pure-Python API) | conda-forge has the GDAL/PROJ builds we need; `uv` is dramatically faster for everything else |
| **Repo** | Monorepo, Conventional Commits, branch protection, Actions running `ruff` + `pytest` on every PR | Integration failure is risk #1. CI from day 1 |
| **Docs** | MkDocs Material | Judges ask for documentation. Having it live is a differentiator |

### 9.1 Hardware plan — RTX 4060 8 GB + RTX 4070 12 GB

| Task | Machine | Notes |
|---|---|---|
| Segmentation training | **4070 (12 GB)** | SegFormer-B2 @ 512², batch 8–16 with AMP fits comfortably. Full run on the Zenodo dataset: hours, not days |
| Segmentation inference | Either | At 40 m/px a full IW scene is ~26 Mpx ≈ 100–150 tiles → **a few seconds**. Not a bottleneck |
| Ship detection (CFAR) | CPU | Classical, no GPU needed |
| **Drift ensembles** | **CPU, multi-core — not GPU** | OpenDrift is NumPy/CPU-bound. **This is the actual bottleneck.** Parallelise across cores; cache forcing fields aggressively as local NetCDF; pre-compute demo scenarios |
| Dev / integration / UI | 4060 machine | Keep the 4070 free for training |

**Budget the drift ensemble carefully.** 100 members × 50 vessels × 96 release times × 100 particles = 48 million particle-timesteps — minutes to tens of minutes on CPU.

> **For the live demo: pre-compute and cache, and stream results back with a realistic progress indicator.** Live-computing a full ensemble on stage is how you lose eight minutes of a ten-minute slot. Keep a "compute live" button for one small scenario to prove it is real.

### 9.2 The Go / Python boundary *(new in v2.0)*

Two languages, one rule: **Go owns the data plane, Python owns the science.** The boundary is the database — Go writes AIS to TimescaleDB, Python reads it. There is no RPC between them, no shared runtime, and no ambiguity about ownership.

| Component | Language | Why |
|---|---|---|
| `aisd` — live AIS recorder | **Go** | Runs 24/7 for three months against a feed with no replay. Supervised reconnect with exponential backoff, bounded write-behind buffer, batch upsert into Timescale. Static binary — deployable on a spare laptop, a Pi, or a free-tier VPS with no runtime to install. Decodes AISStream's own JSON envelope directly — AISStream sends pre-decoded JSON, not AIVDM, so there is no separate wire codec |
| `aisgen` — synthetic AIS generator | **Go** | Shares `aisd`'s database writer (`internal/store`), so synthetic messages are inserted by the *same* code that writes real ones. This is the guarantee that the ingest path is identical for real and synthetic data — a claim §6.4 depends on — implemented at the database row, not at a wire format |
| Everything scientific — SAR, drift, attribution, API | **Python** | PyTorch, rasterio, xarray, GeoPandas, OpenDrift. Rewriting any of this in Go would be actively negligent |

**Where Go was considered and rejected:**

- **The main API.** It must call PyTorch and OpenDrift in-process. FastAPI stays.
- **The tile server.** TiTiler already exists and works. Writing a Go replacement is pure ego.
- **The reachability gate.** Tempting for raw speed, but it is a PostGIS spatial query. The database is already the right engine.

**If a jury asks "why two languages?"** — *"Because the AIS recorder is a data-loss-critical daemon with a three-month uptime requirement and no upstream replay, and the science pipeline is a GPU-bound research stack. Those are different engineering problems. We used the right tool for each and kept the boundary at the database so neither can destabilise the other."*

That answer is a strength. "We used Go because it's fast" is not — do not say it.

---

## 10. Evaluation plan

Full protocol: [`EVALUATION.md`](EVALUATION.md).

| Component | Metric | Dataset | Honest target |
|---|---|---|---|
| Segmentation | mIoU, oil IoU, F1, P/R | Zenodo test split (150/150/150); M4D if granted | mIoU 70–78%, oil IoU 60–70% |
| Look-alike rejection | **FPR on the no-oil set**, broken down by Yang/Singha look-alike cluster | Yang/Singha no-oil set | FPR < 15%; report per cluster |
| Cross-domain robustness | mIoU drop, Mediterranean-trained → Persian Gulf tested | SOS test | **Report the drop. Expect 10–20 points.** |
| Ship detection | P/R vs AIS ground truth | Scene with concurrent AIS | P/R > 0.85 for vessels > 50 m |
| Dark-vessel flagging | Precision (synthetic: vessels whose AIS we deliberately suppressed) | Synthetic | Precision > 0.8 |
| Drift model | Centroid displacement error and success rate vs an observed slick at t+24 h | Ennore 2017; any two-pass S1 slick | Report km error honestly. Published OpenOil skill scores 0.89–0.98 in favourable conditions |
| **Attribution** | **Top-1 / Top-3 accuracy, MRR** | Held-out synthetic scenarios with known culprits | **Top-3 > 80% is a strong, defensible claim** |
| End-to-end | Wall clock: scene ingest → ranked suspects | Cached demo | < 5 min |

**Ablations — these separate a project from a submission:**

1. With vs without the physics/context filter → FPR change
2. **Forward-drift-from-vessels vs naive nearest-ship-at-acquisition** → attribution accuracy change. **The headline chart.** The naive baseline will look terrible, which is the point
3. Single deterministic run vs 100-member ensemble → coverage of the true origin
4. Current-product choice (1/12° model vs 1/4° observational) → drift error
5. *(new in v2.0)* With vs without the boundary-gradient loss term → look-alike FPR

---

## 11. Demo script

Ten minutes. Rehearse twenty times. Full staging notes: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

| Time | Beat |
|---|---|
| 0:00 | **The gap.** One slide. Illegal discharge is routine; India has forward drift (INCOIS OOSA v5.0) and a response authority (ICG/NOSDCP) but no automated attribution. Every attribution today is manual and mostly never happens. |
| 0:45 | **Live ingest.** Select a Sentinel-1 scene over the Arabian Sea. Watch it preprocess and tile. |
| 1:30 | **Detection.** Slick appears with confidence, area, orientation, damping ratio. Then click a *rejected* candidate: *"confidence reduced 0.62 → 0.19 — wind 1.6 m/s below detection window; chlorophyll anomaly +2.1σ; recurring dark formation here in 4 of last 12 scenes."* **This is the moment that demonstrates depth.** |
| 3:00 | **Hindcast.** Backward ensemble animates. Origin *cone* widens with time. Narrate explicitly: "not a point — a probability field, and here is why it widens." |
| 4:00 | **Traffic.** 200+ AIS tracks appear. Cascade filter runs: 214 → 7. Show the audit log of drop reasons. |
| 5:00 | **Attribution.** Per-vessel forward plumes animate simultaneously in deck.gl. One plume lands on the slick. Ranked list populates. |
| 6:30 | **Explanation.** Open the top suspect. Per-factor bars: drift consistency 0.81, course alignment 0.94, 40-minute AIS gap at inferred release time, speed 30% below its own median, night, 12 nm off lane. **Inferred release 06:40 UTC ±50 min → slick age 7.3 h.** |
| 7:30 | **Dark vessel.** Switch scenes: a SAR bright target with no AIS correlate, flagged. "This is the case CleanSeaNet cannot solve." |
| 8:15 | **Forecast + impact.** 48-hour forward run, shoreline impact probability, eco-sensitive zone intersection. |
| 8:45 | **Evidence pack.** Generate the signed PDF. Show the provenance page: product ID, SHA-256 of the source scene, model weights hash, forcing dataset IDs and versions, config snapshot, timestamps. "This is what makes it defensible." |
| 9:15 | **Honest limits.** One slide: 8 km currents vs 40 m slick; cross-domain mIoU drop; synthetic AIS and why. **Volunteering limits before the jury finds them is the highest-value 30 seconds in the presentation.** |
| 9:45 | **Path to operational.** INCOIS high-resolution currents; ICG AIS feed; **NISAR and RISAT/EOS-04 ingest**; deployment on NIC/MeghRaj. |

---

## 12. Roadmap and team

Full detail: [`ROADMAP.md`](ROADMAP.md).

Today is 3 September 2026. SIH 2026 launched 21 August. Internal hackathons run through September; national screening October; **Grand Finale December 2026 (36 hours)**.

### Phase 0 — Internal hackathon (3–~25 Sept)

The 6-slide PPT and video get you through. You need a **vertical slice**, not breadth.

- [ ] **Today:** CDSE account, Copernicus Marine account, AISStream API key
- [ ] **Today: start the AISStream recorder for the Arabian Sea and Bay of Bengal.** It needs three months of runtime to be valuable, and there is no replay. Every day of delay is a day of data permanently lost
- [ ] Request the Krestenitis/M4D dataset (long lead time)
- [ ] WSL2 + Docker + micromamba working on both machines
- [ ] Zenodo dataset downloaded; one S1 scene through CDSE end-to-end
- [ ] Baseline DeepLabv3+ trained, any mIoU, on one dataset
- [ ] OpenDrift running one forward and one backward simulation
- [ ] MapLibre page showing an S1 tile, a polygon, and an AIS track
- [ ] **Video: detection → polygon → backward drift animation.** Enough for internals

### Phase 1 — End-to-end spine (late Sept – mid Oct)

- [ ] Full pipeline on one cached scene, orchestrated, zero manual steps
- [ ] SegFormer-B2 trained, evaluated, model card written
- [ ] Synthetic AIS generator producing valid encoded messages
- [ ] Per-vessel forward-drift attribution producing a ranked list (hand-set weights fine)
- [ ] PostGIS schema stable
- [ ] **Freeze the API contract by 15 October.** Frontend and backend cannot both be moving in November

### Phase 2 — Depth (mid Oct – mid Nov)

- [ ] Physics/context filter with all auxiliary layers
- [ ] Ensemble drift with the full perturbation set
- [ ] Scoring model fitted and calibrated; per-factor explanation UI
- [ ] SAR ship detection + dark vessel flagging
- [ ] MSC ELSA 3 and Ennore scenarios reproduced
- [ ] Evidence dossier generator
- [ ] All ablations run, all charts made
- [ ] *Stretch:* NISAR ingest path demonstrated

### Phase 3 — Harden (mid Nov – Dec)

- [ ] **Full offline mode. Test with the network cable out. Twice**
- [ ] Pre-computed demo cache
- [ ] Error handling everywhere; nothing shows a stack trace on stage
- [ ] Documentation site live
- [ ] Demo rehearsed 20+ times with a scripted recovery for every failure mode
- [ ] Backup laptop with an identical, tested environment

### Phase 4 — Finale (36 h, December)

**Do not rebuild anything.** Arrive with a working system. Use the 36 hours for the specific increments the jury asks for during mentoring rounds — juries reward visible responsiveness. Keep a prioritised backlog of small, high-visual-impact features deliberately left undone for exactly this purpose.

### Team roles — 6 people, ≥1 female per SIH rules

| # | Role | Owns | Must be good at |
|---|---|---|---|
| 1 | **SAR/ML lead** | M1, M2, M3 | PyTorch, image processing. **The strongest ML person. Not the integrator** |
| 2 | **Ocean/drift lead** | M5 | Python, NetCDF/xarray, patience with numerical models |
| 3 | **AIS/attribution lead** | M4, M6 | Data engineering, geospatial reasoning, statistics |
| 4 | **Backend/integration** *(Dev)* | API, DB, orchestration, Docker, CI, evidence pack, **and "does the whole thing run"** | FastAPI, PostGIS, Docker |
| 5 | **Frontend** | React, MapLibre, deck.gl, the entire operator console | React/TS, and an eye for interface density |
| 6 | **Data ops + demo owner** | Data acquisition, demo cache, documentation, presentation, rehearsals | Organisation, communication. **The most underrated role — a great demo owner is worth more than a third ML engineer** |

---

## 13. Risk register

Full register with triggers and owners: [`RISK_REGISTER.md`](RISK_REGISTER.md).

| # | Risk | P | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Three subsystems, none finished | **High** | Fatal | Vertical slice first; API contract frozen 15 Oct; weekly integration build that must be demoable |
| 2 | SNAP/snappy consumes a week | **High** | High | CDSE Sentinel Hub Process API (§6.1). SNAP-in-Docker only as offline fallback |
| 3 | OpenDrift install fails on Windows | **High** | High | WSL2 + micromamba + Docker from week 1. Never attempt native Windows |
| 4 | No real Indian AIS | **Certain** | Medium | Start AISStream recording now — no replay exists; build the synthetic generator properly; validate the method on NOAA US data |
| 5 | Model doesn't transfer to Indian waters | **High** | Medium | Expect it, measure it, report it. Fine-tune on any hand-labelled Arabian Sea scenes |
| 6 | Drift ensembles too slow to demo | Medium | High | Pre-compute and cache; parallelise across cores; one small live-compute case |
| 7 | Network fails at nodal centre | **High** | Fatal | Full offline mode by 15 Nov, tested twice with the cable out |
| 8 | Judge breaks the demo with an edge case | Medium | Medium | Rehearse failure modes; **volunteer limits first** (§11, 9:15) |
| 9 | Team member drops out | Medium | High | No single point of knowledge; everything in the repo and MkDocs; pair on critical modules |
| 10 | Overclaiming triggers hostile questioning | Medium | High | Principle #1. Say "ranked candidates", never "identifies the culprit" |
| 11 | Attribution accuracy unmeasurable (no ground truth) | **High** | Medium | Synthetic ground truth is the only path; be explicit that it is synthetic; MSC ELSA 3 as the one real known-culprit case |
| 12 | Free-tier API quotas exhausted | Low | Medium | 10k PU/month is ample; cache everything locally; multiple team accounts if needed |
| 13 | *(new)* NISAR scope creep swallows Phase 2 | Medium | Medium | Hard-scoped as ingest path only (§6.2). First thing cut if Phase 1 slips |

---

## 14. What NOT to build

Each is a plausible-sounding trap. Cut ruthlessly.

- **Super-resolution of SAR.** The YouTube video attached to this PS is about SR and will tempt you. Read the transcript carefully — it says explicitly that SR does not create data that was not there and does not change ground sampling distance. **Applying SR to SAR before oil detection is scientifically indefensible**: you would be hallucinating texture into a physics-based measurement. If a judge raises it, the answer is:

  > *"Super-resolution is a cosmetic enhancement that does not add information. For a forensic system, introducing generated pixels into evidence would undermine the entire chain of custody. We deliberately did not use it."*

  **That answer will impress more than any implementation would.** (The video appears to be generic thematic filler attached to the PS, not a requirement.) Recorded as [`adr/0004-no-super-resolution.md`](adr/0004-no-super-resolution.md).

- **Mamba/SAM2-based SOTA architectures.** Days of work, a few IoU points, zero jury impact.
- **Kafka, Kubernetes, microservices.** Compose on one box.
- **Mobile app.** Nobody asked.
- **Oil type classification from SAR.** Not physically possible with C-band alone.
- **Volume estimation in tonnes.** Thickness retrieval from SAR is unsolved.
- **Blockchain for evidence.** A signed hash chain in a PDF does the same job without the eye-roll.
- **Training a large model from scratch.** Fine-tune pretrained encoders.
- **A generic LLM chatbot bolted on.** If you want an LLM, use it for one narrow defensible thing: generating the natural-language narrative section of the evidence dossier from structured outputs. Nothing else.

---

## 15. Viva defence

Full sheet: [`VIVA_DEFENCE.md`](VIVA_DEFENCE.md). Whoever presents must answer these without hesitation.

**Why is oil dark in SAR?** Bragg scattering. C-band resonates with capillary and short gravity waves generated by wind. Oil dampens surface tension and suppresses those waves, so backscatter drops.

**How do you distinguish oil from a low-wind area or an algal bloom?** Not from pixels alone — the information is not there. We gate on modelled wind (2–12 m/s window), chlorophyll-a, SST, bathymetry, precipitation, edge sharpness, and our own archive of recurring dark formations at that location, then combine with shape and damping-ratio features. Every applied penalty is logged and shown to the analyst.

**How do you know the slick's age?** We don't measure it — it is not recoverable from a single scene. We infer it. The release time that makes a suspect vessel's forward-drifted plume best match the observed slick *is* the age estimate, with an uncertainty band from the drift ensemble.

**Why not just find the nearest ship?** Because the image may be hours old and the responsible vessel is long gone. We ran that as an explicit baseline — [show the ablation chart] — and it performs poorly. We simulate forward drift from every vessel's track over the plausible age window instead.

**How accurate is your attribution?** Top-3 accuracy of X% on held-out synthetic scenarios with known culprits. We report top-3 rather than top-1 deliberately: narrowing 200 vessels to 3 for an ICG investigator is the operational win. We do not claim to identify a single guilty vessel — the system ranks candidates with calibrated probabilities.

**Your currents are 8 km and your slick is 40 m. Isn't that broken?** It is the dominant term in our error budget and we quantify it rather than hide it. Sub-mesoscale features below 8 km are unresolved, which is why we run 100-member ensembles and output probability fields rather than point estimates. INCOIS's regional high-resolution setup measurably outperforms the global product for the west coast — ingesting it is our first operational integration step.

**Why synthetic AIS?** Bulk historical AIS for Indian waters is not publicly available — free sources are live-only and terrestrial-only with no replay, and the commercial market consolidated further in 2026. We validate the method against real AIS on NOAA's US dataset and demonstrate on Indian waters with a generator calibrated to lane geometry recorded live from AISStream. The data gap is itself part of the capability gap this PS exists to close.

**Isn't an AIS gap just a broken transponder? Aren't you going to accuse innocent fishing boats?** That is the correct question, and it is why f₄ is not "a gap exists." Gaps are overwhelmingly innocent — cheap or old transponders, vessels beyond the ~40–75 nm terrestrial receiver range, and plain bad data like MMSI 0 or GPS stuck at (0,0). We do three things. A data quality pre-filter excludes structurally invalid records entirely, and — importantly — those exclusions never push a score in either direction, so a vessel is never suspect *because* its equipment is broken. We compare each gap against that **vessel's own baseline** behaviour, so a boat that routinely drops out for hours scores low. And we discount gaps in low-coverage water. On top of that, f₄ is one of nine inputs against a strongly negative intercept; it cannot produce a suspect on its own. We would rather miss a detection than accuse the wrong operator.

**Won't every small unidentified boat show up as a dark vessel?** We attach a coarse size bucket from radar cross-section, because **many small craft are legally exempt from carrying AIS** — a fishing boat below the carriage threshold is not an evader. It is a soft flag shown to the analyst, never a hard filter, and we claim a size bucket rather than a vessel type because we have no training data for the latter.

**How is this different from EMSA CleanSeaNet?** CleanSeaNet detects and alerts with a human analyst in the loop, and it fails on orphan spills where no ship is adjacent. We automate attribution for exactly that orphan case using forward drift from all traffic. And it does not cover Indian waters.

**Would this hold up in court?** We do not claim it proves guilt. It produces a ranked, calibrated, fully explainable investigative lead with a complete provenance record — source product IDs and hashes, model version hashes, forcing dataset versions, configuration snapshot. That is what an investigator needs to justify boarding, inspection and sampling, which is where legal proof actually comes from. The Kerala High Court proceedings against the MSC ELSA 3 and Wan Hai 503 owners are exactly the context where such a record has value.

**Did you use AI to write this code?** Yes, extensively, as does most of the field in 2026. *(Then immediately demonstrate understanding of every architectural decision. That is what the question is actually testing.)*

---

## 16. References

**Datasets**

- Trujillo-Acatitla et al., Sentinel-1 SAR Oil Spill dataset — Zenodo `10.5281/zenodo.8346860`, `8253899`, `13761290`
- Yang, Singha, Goldman & Schütte (2025), *Dataset of oil slicks, look-alikes and remarkable SAR signatures obtained from Sentinel-1 data in the Eastern Mediterranean Sea*, Earth Syst. Sci. Data 17, 6807–6837, `10.5194/essd-17-6807-2025`; data at PANGAEA `10.1594/PANGAEA.980773`. **Read Section 4 in full — the best available guide to SAR look-alike interpretation**
- Refined Deep-SAR Oil Spill (SOS) — Zenodo `10.5281/zenodo.15298010`
- Krestenitis et al. (2019) oil spill detection dataset (MKLab, request required)
- NOAA MarineCadastre AccessAIS — `coast.noaa.gov/digitalcoast/tools/ais.html`
- SAR ship detection: SSDD, HRSID, LS-SSDD-v1.0

**Models and methods**

- Dagestad, Röhrs, Breivik & Ådlandsvik (2018), *OpenDrift v1.0*, Geosci. Model Dev. 11, 1405–1420
- Röhrs et al. (2018), *The effect of vertical mixing on the horizontal drift of oil spills* (OpenOil), Ocean Sci. 14, 1581–1601
- Xie et al. (2021), *SegFormer*, NeurIPS 34
- Polluter identification with spaceborne radar imagery, AIS and forward drift modelling — Marine Pollution Bulletin (2015), `10.1016/j.marpolbul.2015.08.036` — **the core method behind §8.2**
- Brekke & Solberg (2005), *Oil spill detection by satellite remote sensing* — the foundational survey
- 2025–26 SAR oil-spill segmentation literature (FCS-Net, SpillNet and related) — for SOTA context and the edge-prominence finding

**Indian operational context**

- Prasad et al. (2018), *An assessment on oil spill trajectory prediction: case study on oil spill off Ennore Port*, J. Earth Syst. Sci., `10.1007/s12040-018-1015-3`
- Prasad et al. (2019), *Oil spill trajectory prediction with high-resolution ocean currents*, J. Operational Oceanography 13(1), 84–99
- INCOIS Online Oil Spill Advisory (OOSA v5.0) and SARAT — `incois.gov.in`
- NOSDCP — Indian Coast Guard
- 2025 Kerala oil spill (MSC ELSA 3, Wan Hai 503) and subsequent Kerala High Court proceedings

**Data services**

- Copernicus Data Space Ecosystem — `dataspace.copernicus.eu` (Sentinel Hub Process API, openEO, STAC; 10,000 free PU/month)
- Copernicus Marine Service — `marine.copernicus.eu` (`copernicusmarine` toolbox)
- ECMWF ERA5 via the Copernicus Climate Data Store
- **NISAR** via ASF DAAC / NASA Earthdata — L-band public since 20 July 2026
- GEBCO bathymetry — `gebco.net`
- AISStream — `aisstream.io`

**Interface**

- Blueprint — Palantir's open-source React design system for data-dense interfaces, `blueprintjs.com`

---

*Keep this document at `/docs/PRD.md`. Update the version number on every material change and record the reasoning in the changelog at the top.*
