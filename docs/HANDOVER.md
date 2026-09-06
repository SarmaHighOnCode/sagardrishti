# Implementation Handover

**Purpose:** hand the remaining code work to someone (or some model) picking this up cold. Every section says what to build, where, against which interfaces, and what "done" means.

**Read first, in order:** [`ARCHITECTURE.md`](ARCHITECTURE.md) §§4–5 · [`adr/0001`](adr/0001-forward-drift-attribution.md) (why attribution works the way it does) · [`adr/0002`](adr/0002-fixed-ground-sample-distance.md) (the GSD trap) · [`SCORING_MODEL.md`](SCORING_MODEL.md) §2.1 (the AIS-gap correctness rules).

---

## 0. Ground rules that are not negotiable

These are not style preferences. Each one exists because violating it produces a *plausible-looking wrong answer* rather than a crash — which is the failure mode this whole project is built to avoid.

| Rule | Why | Enforced by |
|---|---|---|
| **Every value crossing a boundary carries its unit in the field name** (`sog_knots`, `speed_ms`, `area_km2`) | A constant-factor error in a drift model silently corrupts every downstream attribution | Convention + `sagar_core.units` |
| **Conversions go through `sagar_core.units`** — never an inline `* 0.514` | Inline constants are unsearchable when it turns out one was applied twice | Code review |
| **Inferred values carry their interval in the same object** | Product principle 2 | `SlickAgeEstimate`, `ReleaseTimeEstimate` — both fields required, no defaults |
| **GSD is fixed at 40 m/px** across training and inference | Mixing resolutions fails *silently*: healthy loss curve, collapsed field performance, misdiagnosed as domain shift | [ADR 0002](adr/0002-fixed-ground-sample-distance.md); assert it in every dataset adapter |
| **Backward drift runs never weather** | Evaporation/emulsification are irreversible; reversing them produces confident nonsense | `DriftRun` validator in `sagar_core.types` |
| **Unreliable AIS records are marked, never deleted — and never shift a score in either direction** | A vessel must never become a suspect *because* its transponder is broken | `data_quality` column; [`SCORING_MODEL.md`](SCORING_MODEL.md) §2.1 |
| **Negative (exculpatory) scoring factors are always shown** | Hiding them destroys the legal-defensibility claim the dossier rests on | `ScoringFactor.contribution` may be negative; CI guard on accusatory language |
| **Provenance is emitted *as* a stage runs** | M7 cannot reconstruct which weights produced a detection three stages ago | `sagar_core.provenance.ProvenanceRecord` |
| **Synthetic results are labelled everywhere** | Overstating what a demo proves is the fastest way to lose a viva | `ProvenanceChain.synthetic` contaminates the whole chain |

**Verification standard:** don't claim something works until you've run it. If you can't run it (no Docker, no GPU, no credentials), say exactly what you did verify and what remains unverified. There is precedent for this in the repo — `db/README.md` states plainly that migration `002` is parse-verified but never executed.

---

## 1. What exists now

| Component | State | Notes |
|---|---|---|
| `packages/sagar_core` | ✅ **Complete**, 63 tests | Types, units, geo, provenance, config, logs. **Depends on nothing. Start here — everything imports it** |
| `services/api` | ✅ Full contract surface, 38 tests | Fixture-backed; unimplemented pipeline stages return honest `501` |
| `services/aisd` | ✅ Merged (PR #1), 34 tests | Go AIS recorder. Live-verified against a real Postgres |
| `db/schema/001` | ✅ Live-verified | AIS tables |
| `db/schema/002` | ⚠️ **Parse-verified only** | Never run against a live Postgres — do this first when Docker works |
| `web/` | ✅ Console UI, 100 tests | **Still on local fixtures — not wired to the API** |
| `packages/sagar_{ingest,sar,drift,attrib,evidence}` | ❌ Empty | READMEs only |
| `services/worker` | ❌ Empty | |
| `services/aisgen` | ❌ Empty | |

---

## 2. Task order (dependency-correct)

Later tasks assume earlier ones. Deviating is fine if you know why.

```
  A. Verify migration 002 on live Postgres   ← unblocks everything DB-touching
  B. Wire console → API                      ← independent, high visibility, easy
  C. sagar_ingest (fetchers + cache)         ← M1 needs it
  D. sagar_sar M1 (preprocess)               ← everything SAR needs it
  E. sagar_sar M2 (detect)  ─┐
  F. sagar_drift M5         ─┼─ can proceed in parallel once C+D land
  G. aisgen                 ─┘
  H. sagar_attrib M6                         ← needs F + G
  I. services/worker                         ← needs D–H
  J. sagar_evidence M7                       ← needs I
```

---

## A. Verify migration `002` on a live database

**Why first:** it's written but never executed. If it has an error, everything built on those tables inherits it.

```bash
docker compose up -d db
docker compose exec db psql -U sagar -d sagardrishti -f /docker-entrypoint-initdb.d/002_core_pipeline.sql
docker compose exec db psql -U sagar -d sagardrishti -c '\d detections' -c '\d suspects'
```

**Done when:** every table, index and constraint from `002` exists; the partial unique index on `evidence_dossiers` rejects a second `is_current=true` row for one detection. Then update `db/README.md`'s honesty note.

**Watch for:** `GEOMETRY(Polygon, 4326)` needs PostGIS loaded (it is, from `001`). Migrations apply in numeric order — `002` has FKs into `scenes`, so `001` must have run.

---

## B. Wire the console to the API

**Why easy:** `web/src/lib/fixtures.ts` and `services/api/app/fixtures.py` were built deliberately identifier-identical — same scene id, detection ids, MMSIs, factor values. Swapping the data source should change nothing visible.

**Build:** `web/src/lib/api.ts` — a typed client. Types mirror `services/api/app/schemas.py`.

```ts
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function getDetections(sceneId?: string): Promise<Detection[]> {
  const url = new URL(`${BASE}/detections`);
  if (sceneId) url.searchParams.set("scene_id", sceneId);
  const res = await fetch(url);
  if (!res.ok) throw await problemFrom(res);   // RFC 7807 body
  return (await res.json()).items;             // Page envelope
}
```

Then swap `Shell.tsx`'s fixture imports for TanStack Query hooks.

**Handle honestly:** several endpoints return **501** by design (`hindcast`, `forecast`, `evidence`, `analyse`). The UI must show "not available yet", **not** an empty chart that implies zero drift. An empty state that looks like data is a lie.

**Done when:** console renders identically to now, but `docker compose up` is required; the 501 panels state why; error paths render the `problem+json` `detail`.

---

## C. `sagar_ingest` — fetchers with mandatory caching

**Build:**
```
packages/sagar_ingest/
  sentinel.py     CDSE Sentinel Hub Process API (calibrated, noise-removed GRD)
  marine.py       copernicusmarine — currents, waves, wind, SST, chlorophyll
  era5.py         cdsapi — wind, precipitation
  static.py       GEBCO bathymetry, GSHHG coastline (fetch once)
  cache.py        the caching contract below
```

**The caching contract is the important part.** Every fetch writes local NetCDF/GeoTIFF keyed by `(product, bbox, time_range, variables)`.

```python
def get(self, key: CacheKey) -> Path:
    hit = self._lookup(key)
    if hit:
        return hit
    if self.settings.offline:
        raise CacheMissError(
            f"{key.product} for bbox={key.bbox} time={key.time_range} not in "
            f"{self.root}. Run `make warm-cache` while online."
        )
    return self._fetch_and_store(key)
```

> **In offline mode a miss RAISES. It does not fetch.** A silent network fallback is the bug that ends the demo: everything works in the lab, then hangs at a venue with no wifi. Fail loudly at setup. See [`OFFLINE_MODE.md`](OFFLINE_MODE.md).

**Skip SNAP entirely** — the Process API returns calibrated, thermal-noise-removed GRD in one request. Installing ESA SNAP + `snappy` costs about a week on Windows ([`DATA_SOURCES.md`](DATA_SOURCES.md) §1.1).

**Done when:** a scene and its forcing fetch once, are reused from cache on a second call, and a cache miss under `SAGAR_OFFLINE=1` raises with the missing key named.

---

## D. `sagar_sar` M1 — preprocessing

```
GRD → orbit → border noise → thermal noise → calibrate σ⁰
    → resample to EXACTLY 40 m/px          ← the line that matters
    → dB → land mask → normalise → tile 512² (64 px overlap) → COG + STAC
```

**Assert the GSD.** Not a comment — a runtime check that raises:

```python
def assert_gsd(transform: Affine, expected_m: float = 40.0, tol: float = 0.5) -> None:
    actual = abs(transform.a)
    if abs(actual - expected_m) > tol:
        raise ValueError(
            f"GSD {actual:.2f} m/px != required {expected_m} m/px. Mixing "
            "resolutions between training and inference fails silently — "
            "see docs/adr/0002-fixed-ground-sample-distance.md"
        )
```

Call it in the tiler **and** in every dataset adapter in `ml/datasets/`.

**Normalisation:** pick one (sigmoid stretch, β=median α=3σ; or clip to median±3σ then min-max), apply identically at train and inference, record it in the model card. Inconsistency here is another silent failure.

**Done when:** a GRD produces a 40 m/px COG + STAC item; tiles are 512² with 64 px overlap; land is masked; the GSD assertion rejects a deliberately-wrong input.

---

## E. `sagar_sar` M2 — detection (three stages)

**Stage A — proposals.** Cheap, high recall. Adaptive threshold on σ⁰ dB (local median − k·MAD), morphological cleanup, drop < 0.1 km². Purpose: avoid running a network over 100% ocean.

**Stage B — segmentation.** SegFormer-B2 primary (`transformers`), DeepLabv3+ baseline (`segmentation_models_pytorch`). 5 classes: `sea/oil/look_alike/land/ship`. Loss: Focal + Dice + **boundary-gradient term** (2025–26 work identifies edge prominence as a primary oil-vs-look-alike discriminator).

Augment with: flips, 90° rotations, multiplicative speckle, σ⁰ level shift (±2 dB), incidence-angle gradient. **Never colour jitter or elastic deformation** — physically meaningless for SAR, and a reviewer who spots them concludes the team doesn't understand the sensor.

**Do not chase Mamba/SAM2 SOTA.** Days of work, a few IoU points, zero jury impact.

**Stage C — the physics/context filter. This is the differentiator.** A pure pixel classifier *cannot* separate oil from a low-wind area, because the information isn't in the pixels.

```python
def apply_context_filter(det: SlickPolygon, ctx: EnvironmentalContext) -> SlickPolygon:
    penalties = []
    if not (2.0 <= ctx.wind_ms <= 12.0):
        penalties.append(
            Penalty(
                check="wind_window",
                delta=-0.28,
                reason=f"wind speed {ctx.wind_ms:.1f} m/s outside 2-12 m/s detection window",
                evidence={"wind_ms": ctx.wind_ms, "source": ctx.wind_source},
            )
        )
    # ... chlorophyll anomaly, SST cold anomaly, bathymetry gradient,
    #     precipitation, recurrence at this location
    return det.model_copy(update={"confidence": adjusted, "penalties": penalties})
```

**Every penalty needs a human `reason` and machine-readable `evidence`.** The `reason` drives the rejection panel — the single cheapest credibility feature in the product ([`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) §6.3), and the demo's best 30 seconds.

`SlickPolygon` rejects a confidence drop with an empty penalty log, so an unexplained reduction fails at construction.

**Targets** (from [`EVALUATION.md`](EVALUATION.md)): mIoU 70–78%, oil IoU 60–70%, FPR < 15% on no-oil. **Report the cross-domain drop** (expect 10–20 points) — that's a credibility move, not a weakness.

---

## F. `sagar_drift` M5 — the drift engine

OpenDrift/OpenOil. Three modes:

| Mode | Direction | Weathering | Produces |
|---|---|---|---|
| Hindcast | backward | **OFF** | Origin probability field, reachability region |
| Forecast | forward | ON | 24/48/72 h extent, shoreline impact |
| Per-vessel | forward | ON | Attribution evidence |

**The one implementation detail that makes attribution viable:**

> All particles, from all vessels, at all release times, go into **ONE** OpenDrift run with staggered seed times, each tagged `(vessel_id, release_time, ensemble_member)`. Scoring is a group-by on the tags afterwards.

Naively it's 50 vessels × 96 release times × 100 members = 480,000 simulations. Impossible. Particles are independent and OpenDrift supports staggered seeding, so this is **exact, not an approximation**. Without it the whole approach collapses. See [ADR 0001](adr/0001-forward-drift-attribution.md).

**Ensembles are mandatory** — ≥100 members perturbing wind drift factor (uniform [0.02, 0.04] — the real physical range; picking one value fabricates precision), current magnitude ±10–20%, diffusivity, Stokes on/off. **The spread IS the uncertainty estimate.** A single deterministic run frequently misses the true origin entirely.

**CPU-bound, not GPU.** This is the real bottleneck. Parallelise across cores, cache forcing aggressively, pre-compute demo scenarios.

**Done when:** backward and forward runs execute from cached forcing; a 100-member ensemble produces a probability field; `DriftRun(mode=BACKWARD, config={"weathering": True})` raises.

---

## G. `services/aisgen` — synthetic AIS

**This is a deliverable, not a fallback** — bulk historical AIS for Indian waters isn't publicly available, and this is the **only** source of attribution ground truth, so it's the only way to compute accuracy at all.

**Read [ADR 0005](adr/0005-go-for-the-ais-data-plane.md) first.** It was corrected: AISStream sends **pre-decoded JSON, not AIVDM**, so there is no wire codec to share.

**The blocker you will hit:** the guarantee that synthetic and real AIS share an ingest path now rests on `aisgen` calling `aisd`'s `internal/store` — but Go's `internal/` visibility rule means `services/aisgen` (a separate module) **cannot import it**. Promote the writer to `packages/go/store` and have both modules depend on it via a `go.work` workspace.

> **Do not "solve" this by copy-pasting the insert logic.** That silently reopens the exact gap the ADR exists to close, and nothing will fail loudly when the two diverge.

**Requirements:** lane geometry from recorded AISStream data (KDE → centrelines) · realistic per-type SOG/COG/reporting intervals · **labelled ground-truth discharge events** · realistic confounders.

**The confounders matter most for honesty:** include vessels with genuinely flaky transponders, vessels legitimately out of coverage, and innocent vessels passing near the slick at the right time. If the model ranks these highly, that's a real finding — better discovered here than by a jury.

---

## H. `sagar_attrib` M6 — attribution

**Read [`SCORING_MODEL.md`](SCORING_MODEL.md) in full before touching this.** It's where the project both wins and is most capable of doing harm.

```
1. GATE     backward reachability region → keep intersecting tracks    214 → 46
2. FILTER   timing, kinematics, drift-score floor                       46 → 7
3. SEED     interpolate tracks to 15-min steps, tag (vessel, time)
4. ADVECT   ONE staggered OpenDrift run (see F)
5. SCORE    overlap → drift_score, t*, slick age
6. RANK     9-factor log-odds → Platt calibration → ranked suspects
```

**Overlap scoring** — the harmonic mean is deliberate:
```
hit(v,t)      = fraction of (v,t) particles inside the slick
coverage(v,t) = fraction of slick covered by the (v,t) particle KDE
drift_score   = max over t of  2·hit·coverage / (hit + coverage)
```
`hit` alone rewards a plume that's a tiny dot inside a huge slick; `coverage` alone rewards one smeared everywhere. The F-measure penalises both.

**Track interpolation:** great-circle with SOG/COG. **Never naive linear interpolation across long gaps** — it invents positions the vessel never occupied, and those fabricated positions then seed particles that generate fabricated evidence.

### The AIS gap factor — the dangerous one

The naive version (*gap near spill = suspicious*) **is wrong and produces false accusations.** Gaps are overwhelmingly innocent: cheap transponders, out-of-range operation, bad data. Three corrections, all required:

1. **Data-quality pre-filter** — exclude MMSI 0, position (0,0), kinematically impossible implied speed (`sagar_core.geo.implied_speed_knots`), garbled static. Labelled `unreliable`, **removed from the evidence set — they neither boost nor penalise.**
2. **Per-vessel baseline** — cached per MMSI (`ais_baseline_profiles`). Suspicion is deviation from *this vessel's own* normal behaviour. Without it, the factor measures transponder quality, not behaviour.
3. **Coverage proxy** — distance-to-coast vs terrestrial AIS range (~40–75 nm). **Deliberately simple; do not build a radio propagation model.** The extra accuracy isn't worth the time and is harder to defend.

**And f₄ is never a standalone trigger.** Nine weighted inputs against an intercept of −4.0; drift consistency (2.5) dominates by design.

**Never a neural network here.** Tens of labelled events, ten weights — a network would overfit and report the overfit as accuracy. The log-odds model *is* the explanation. [ADR 0003](adr/0003-transparent-log-odds-scoring.md).

**Report top-3, not top-1.** Narrowing 214 vessels to 3 is the operational win. Label every synthetic number `SYNTHETIC`.

---

## I. `services/worker` — orchestration

ARQ consumer. Owns the job context that modules write `ProvenanceRecord`s into as they run.

**Stages are named, never percentages** — use `sagar_core.logs.STAGES` and `validate_stage()`. *"Advecting 50 vessels × 96 release times"* tells an analyst what's happening; *"63%"* doesn't.

Mirror job state into the `jobs` table so the API's `GET /jobs/{id}` (currently an honest 404) starts returning real data.

---

## J. `sagar_evidence` M7 — the dossier

Assembles `ProvenanceChain` into a signed PDF. **Never the word "guilty"** — CI enforces this. Include exculpatory factors. Label synthetic runs on every page. Signed hash chain, **not blockchain**.

---

## 3. Working agreements

```bash
make test          # pytest (139 tests currently) + go test + vitest
make lint          # ruff + tsc + eslint + go vet
```

- Branch off `main`, PR, one reviewer, CI green. Conventional Commits.
- **Every Friday `main` must run end to end and be demoable.** This is the primary defence against the failure mode that kills most SIH teams — three excellent subsystems that have never been run together.
- **API contract freezes 15 October.** After that, additive changes only.
- A module without provenance emission is a module whose output can't go in a dossier.

## 4. If you get stuck

| Symptom | Likely cause |
|---|---|
| Model trains fine, performs terribly on real scenes | GSD mismatch — [ADR 0002](adr/0002-fixed-ground-sample-distance.md) |
| Drift results confident but wrong | Weathering on a backward run, or a units slip (knots vs m/s) |
| Attribution ranks obviously-innocent vessels | AIS gap factor uncorrected — [`SCORING_MODEL.md`](SCORING_MODEL.md) §2.1 |
| Everything works locally, hangs at the venue | A cache miss silently fetching — [`OFFLINE_MODE.md`](OFFLINE_MODE.md) |
| `aisgen` can't import `aisd`'s store | Go `internal/` visibility — see G |

**When a doc and the code disagree, one of them is wrong — fix it, don't work around it.** That's how the `BaselineGapProfile` field-name drift was caught before it shipped.
