# Data Sources

Every dataset the system touches: what it gives us, how we get it, what it costs, what it is licensed under, and what we do when it is unavailable.

**Rule:** nothing enters the pipeline without an entry here. If a teammate adds a source, they add a row.

---

## 1. Satellite imagery

### 1.1 Sentinel-1 — primary sensor

| | |
|---|---|
| **Product** | Sentinel-1 IW GRDH, dual-pol VV+VH |
| **Access** | CDSE Sentinel Hub Process API (primary), CDSE STAC/OData (discovery + raw), ASF DAAC (mirror) |
| **Cost** | Free. **10,000 Processing Units/month** per account; openEO adds ~10,000 credits |
| **Licence** | Copernicus open data — free, full, open |
| **Client** | `sentinelhub-py`, `pystac-client` |

**Constellation status, verified September 2026:** Sentinel-1A operations terminated **29 June 2026** after 11 years. The final configuration is **Sentinel-1C + Sentinel-1D** at 6-day repeat, following orbital reconfiguration in June 2026. Effective revisit over the Indian EEZ combining ascending and descending passes is roughly **1–3 days**.

> Quoting "Sentinel-1A/1B, 6-day repeat" is quoting 2021. Get this right on stage.

**Why Sentinel Hub and not SNAP.** The Process API returns GRD **already calibrated and thermal-noise-removed**, optionally speckle-filtered and orthorectified, as GeoTIFF for a given AOI and time window, in one HTTP request. Installing ESA SNAP and wiring `snappy` on Windows costs roughly a week and still produces JVM/Python bridge problems. See PRD §6.1.

**Fallback ladder:** Sentinel Hub → CDSE STAC raw download → ASF DAAC → SNAP `gpt` CLI in Docker (offline reproducibility only; never `snappy`).

### 1.2 NISAR — the sovereign angle

| | |
|---|---|
| **Product** | NISAR L-band SAR (24 cm); S-band (9.4 cm) |
| **Access** | ASF DAAC / NASA Earthdata |
| **Availability** | **L-band public since 20 July 2026**, covering acquisitions from 17 June 2026. Full science record expected by end 2026 |
| **Cost** | Free, registration required |

**Why it is in this document.** NISAR is a **NASA–ISRO joint mission — India co-owns it**, and the S-band instrument exists specifically to serve Indian science priorities including coastal applications. For an NTRO audience this reframes the hardest question we will be asked ("why are you dependent on European satellites?") into a demonstrated answer.

**Scope discipline.** NISAR is a **Phase 2 stretch goal**. The commitment is a working ingest and preprocessing path plus a qualitative comparison over a common AOI — **not** a trained L-band oil detector. L-band slick damping behaves differently from C-band and validating a detector there is a research programme, not a sprint. If Phase 1 slips, this is the first thing cut, and we say so rather than quietly dropping it.

### 1.3 Sentinel-2 — optional quicklook only

True-colour overlay for context where cloud-free and coincident. **Cut first if time is short.** Optical oil detection is a separate problem and we are not solving it.

---

## 2. Training datasets

| Dataset | Contents | Access | Licence | Role |
|---|---|---|---|---|
| **Trujillo-Acatitla et al.** — Zenodo `10.5281/zenodo.8346860` (I), `8253899` (II), `13761290` (III) | 2048×2048×2 (VV, VH) σ⁰ dB GeoTIFF, **georeferenced**. 1200 oil + 685 no-oil train/val; 150 oil / 150 look-alike / 150 no-oil test | Direct download | Open | **Primary.** The dataset the PS links. Georeferenced dual-pol dB matches our production format exactly |
| **Yang & Singha (DLR)** — PANGAEA `10.1594/PANGAEA.980773`; ESSD 17, 6807–6837 (2025) | 1365 patches / 3225 **object-level** bboxes + 2290 no-oil patches, **K-means clustered by look-alike type**. 640×640, VV | Direct download | CC-BY | **Stage A detection + the look-alike ablation.** The clustered no-oil set lets us report *which kind* of look-alike we fail on — nobody else at SIH will do this |
| **Refined Deep-SAR Oil Spill (SOS)** — Zenodo `10.5281/zenodo.15298010` | ALOS PALSAR (Gulf of Mexico) + Sentinel-1 (Persian Gulf), 256×256, ~8k images. ~38% of train masks manually corrected | Direct download | Open | **Cross-domain test set.** The Persian Gulf split is climatically the closest available proxy to Indian waters |
| **Krestenitis / MKLab "OSD"** | ~1002 train / 110 test, 5 classes (oil, look-alike, land, ship, sea). Sourced from EMSA CleanSeaNet | **Request required** — proposal to authors | Restricted | The standard benchmark. Having it makes our numbers comparable to published work. **Request day 1, do not block on it** |
| **SSDD / HRSID / LS-SSDD-v1.0** | SAR ship detection, bboxes | Direct | Open | M4 ship detection, if we train rather than use CFAR |

**Every dataset is resampled to 40 m/px on load.** Adapters live in `ml/datasets/` and refuse to yield a sample whose GSD they cannot verify. See [ADR 0002](adr/0002-fixed-ground-sample-distance.md) — this is the silent failure mode that will bite teams who skip it.

---

## 3. AIS — the constrained resource

**There is no free source of bulk historical AIS for Indian waters.** This is the defining data constraint of the project. Face it directly rather than discovering it in November.

| Source | Gives | Coverage | Cost | Our use |
|---|---|---|---|---|
| **NOAA MarineCadastre** | Bulk historical CSV, excellent quality | **US waters only** | Free | **Method validation.** We build and validate the entire attribution engine against real tracks here, then apply it to Indian synthetic data. This is what makes the method claim credible |
| **AISStream.io** | Live WebSocket, bbox subscribe, JSON | Global, **terrestrial receivers only** | Free, API key | **Live recording, starting immediately.** Three months of runtime yields real Indian AIS for lane calibration |
| **AISHub** | Live feed | Global | Free *if you contribute a receiver* | Impractical for us |
| **Global Fishing Watch** | AIS-derived vessel presence and events | Global | Free for research | Fishing-traffic context. Worth a look |
| Kpler / Spire / Datalastic | Satellite + terrestrial historical | Global | Paid | Out of scope. **Note the 2026 market consolidation on the slide** — it strengthens the case for indigenous capability |
| **`aisgen` (ours)** | Synthetic tracks with ground-truth discharge events | Our AOI | — | **Required. The only source of attribution ground truth** |

### 3.1 AISStream: start recording today

> **AISStream provides no SLA, no uptime guarantee, and no durable replay of past events.** A message not persisted on receipt is permanently lost.

This has two consequences that drive real engineering decisions:

1. **Every day of delay is a day of Indian AIS permanently unavailable to us.** Starting the recorder is the highest-leverage single action in the project and it takes an afternoon.
2. **The recorder must be genuinely reliable** — supervised reconnect with exponential backoff and jitter, bounded write-behind buffer, batch commit, and a write-ahead file so a database outage does not lose the stream. This is why it is a Go binary rather than a notebook. See [ADR 0005](adr/0005-go-for-the-ais-data-plane.md).

**AOIs to record:** Arabian Sea (Gulf of Kutch → Kanyakumari, out to the EEZ boundary) and Bay of Bengal (Kanyakumari → Sundarbans). Both from day one.

**Known limitation, state it honestly:** AISStream is terrestrial-receiver-based, so coverage degrades with distance from shore and is sparse in the open ocean where much operational discharge happens. We use it for **lane geometry calibration**, not as a complete traffic picture.

### 3.2 Synthetic AIS — a deliverable, not a fallback

The PS explicitly permits synthetic AIS. Built properly it is a contribution in its own right. `aisgen` must:

1. Derive lane geometry from recorded AISStream data — KDE of positions → lane centrelines → lane widths
2. Sample vessel types from realistic Indian-waters distributions (tanker / container / bulker / fishing / tug)
3. Generate tracks with per-type SOG distributions, realistic COG jitter, and correct reporting intervals (Class A: 2–10 s underway, 3 min at anchor), decimated to reflect terrestrial receiver gaps
4. **Write to `ais_positions` through `aisd`'s own `internal/store` batched-upsert path**, not a parallel implementation — so the ingest path is provably identical at the point every downstream consumer actually reads it: the database row. (AISStream itself sends pre-decoded JSON, not AIVDM, so there is no wire-level codec to share here — see [ADR 0005](adr/0005-go-for-the-ais-data-plane.md).)
5. Inject labelled ground-truth discharge events with known vessel, time, location and rate — **our only means of computing attribution accuracy**
6. Inject realistic confounders: AIS gaps, MMSI spoofing and duplication, position jumps, innocent vessels transiting near the slick

**The viva answer:**

> "We validate the attribution engine against real AIS on the NOAA US dataset, where independent tracks exist. We demonstrate on Indian waters using a synthetic generator calibrated to lane geometry we recorded live from AISStream, because bulk historical Indian AIS is not publicly available — which is itself part of the capability gap this problem statement exists to close."

---

## 4. Ocean and meteorological forcing

All free via `copernicusmarine` (registration at marine.copernicus.eu) and `cdsapi` (ECMWF CDS).

| Variable | Product | Resolution | Used by |
|---|---|---|---|
| Surface currents, analysis + forecast | `GLOBAL_ANALYSISFORECAST_PHY_001_024` | 1/12° (~8 km), hourly | M5 — primary advection |
| Surface currents, observation-based | `MULTIOBS_GLO_PHY_MYNRT_015_003` | 1/4°, hourly, 0 m and 15 m | M5 — ensemble perturbation, ablation 4 |
| Waves + **Stokes drift** | `GLOBAL_ANALYSISFORECAST_WAV_001_027` | 3-hourly | M5 |
| Sea surface wind, L4 | `WIND_GLO_PHY_L4_*` | 0.125°, hourly | **M2 Stage C wind gate**, M5 wind drift |
| Sea surface temperature | CMEMS SST | Daily | M2 Stage C — upwelling discrimination |
| Chlorophyll-a | CMEMS Ocean Colour | Daily | M2 Stage C — biogenic film discrimination |
| Wind + precipitation (reanalysis) | ECMWF **ERA5** via CDS | 0.25°, hourly | M2 Stage C — rain-cell discrimination; wind fallback |
| Bathymetry | **GEBCO** 2024 grid | 15 arcsec (~450 m) | M2 Stage C — internal-wave context |
| Coastline | GSHHG or OSM | — | M1 land mask, buffered 500 m |

### 4.1 The resolution mismatch — put it on a slide

SAR resolves the slick at 10–40 m. The best free currents are ~8 km. **We are advecting a metre-scale feature with a field that cannot see anything smaller than a city.** Sub-mesoscale eddies (100 m – 10 km), which visibly control slick shape, are entirely unresolved.

This is **the dominant term in our error budget**. It is a physics and data-availability limit, not an engineering failure. We handle it by:

- running 100+ member ensembles with stochastic diffusion and perturbed forcing
- outputting probability fields, never point estimates
- naming INCOIS's higher-resolution regional setup as the first operational integration step

Stating this clearly is worth more than hiding it. See the honest-limits beat in [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

### 4.2 Caching is mandatory

Drift ensembles read the same forcing fields hundreds of times. Every fetch writes local NetCDF keyed by `(product, bbox, time_range, variables)`. **The drift engine reads only from cache — a miss raises rather than silently fetching**, so an offline run fails loudly at setup rather than hanging mid-demo.

---

## 5. Reference incidents

| Incident | Date | Location | Value |
|---|---|---|---|
| **MSC ELSA 3** | 25 May 2025 | Off Kochi | **Headline demo.** Known vessel, known ground truth. ICG confirmed slick within hours; INCOIS activated SARAT and its oil/nurdle trajectory system. Real AIS track exists |
| **Wan Hai 503** | June 2025 | Off Kerala | Second incident weeks later. Together these triggered a Kerala contingency overhaul and **High Court proceedings against both owners** — the live legal context for our evidence dossier |
| **Ennore collision** | 28 Jan 2017 | Chennai | ~196 t heavy furnace oil. **INCOIS published a trajectory-vs-Sentinel-1A validation of this exact case** — lets us benchmark drift against a peer-reviewed Indian result |
| **MV Rak Carrier** | Aug 2011 | Off Mumbai | Covered in INCOIS drift literature |
| **Deepwater Horizon** | 2010 | Gulf of Mexico | Pre-Sentinel-1. Training data only (present in SOS) |

---

## 6. Accounts to create — day one

| Service | URL | Needed for | Lead time |
|---|---|---|---|
| Copernicus Data Space Ecosystem | dataspace.copernicus.eu | Sentinel-1 | Immediate |
| Copernicus Marine Service | marine.copernicus.eu | Currents, waves, wind, SST, chl-a | Immediate |
| ECMWF Climate Data Store | cds.climate.copernicus.eu | ERA5 | Immediate |
| AISStream | aisstream.io | **Live AIS — start recording the same day** | Immediate |
| NASA Earthdata | urs.earthdata.nasa.gov | NISAR, ASF DAAC mirror | Immediate |
| Krestenitis/M4D dataset | Author request | Benchmark comparability | **Days to weeks — request first** |

Credentials go in `.env`, never in the repository. Template in [`.env.example`](../.env.example).

---

## 7. Licensing and attribution

| Source | Licence | Obligation |
|---|---|---|
| Copernicus Sentinel data | Free, full, open | Credit "Contains modified Copernicus Sentinel data [year]" |
| Copernicus Marine | Free, registration | Cite product IDs — we do, in every dossier |
| ERA5 | Free, CDS terms | Cite ECMWF |
| GEBCO | Free | Credit GEBCO Compilation Group |
| NISAR / ASF DAAC | Free, registration | Cite mission and DAAC |
| Zenodo datasets | Per-dataset, mostly open/CC-BY | Cite the DOI |
| Yang & Singha | CC-BY | Cite the ESSD paper |
| Krestenitis/M4D | Restricted, by request | Respect terms; **do not redistribute** |
| NOAA MarineCadastre | US public domain | Credit NOAA |
| OpenDrift/OpenOil | GPL-2.0 | **We use it as a library. Check our distribution story before claiming a permissive licence for the whole system** |
| Blueprint | Apache 2.0 | Attribution |

> **Open action for the integration lead:** OpenDrift is GPL-2.0. Our repository is Apache 2.0. Confirm whether our use constitutes a combined work before publishing distribution claims. In practice for SIH this is a non-issue (we are not distributing binaries), but the question should be answered rather than assumed.

Every evidence dossier carries a data-lineage page listing each source with its product ID, version and access timestamp. That is both good scientific practice and the thing that makes the dossier defensible.
