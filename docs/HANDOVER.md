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
| `packages/sagar_core` | ✅ **Complete**, 63 tests | Types, units, geo, provenance, config, logs. **Depends on nothing. Read this first — everything imports it** |
| `services/api` | ✅ Full contract surface, 38 tests | Fixture-backed; unimplemented pipeline stages return honest `501` |
| `web/src/lib/api.ts` | ✅ Typed client, 17 tests | Consumed by Shell as of task B |
| `web/src/app/Shell.tsx` | ✅ **Wired to the API**, task B done | Fetches via `lib/queries.ts`; no longer imports `SAMPLE_*` fixture arrays. **Live-verified against no server**: shows an honest "Failed to fetch" rather than crashing — see PR #6. **Not yet verified against a running API** (Docker daemon was down at handover) |
| `services/aisd` | ✅ Merged (PR #1), 34 tests | Go AIS recorder. Live-verified against a real Postgres |
| `db/schema/001` | ✅ Live-verified | AIS tables |
| `db/schema/002` | ⚠️ **Parse-verified only** | Never run against a live Postgres — **do this first once Docker works** |
| `web/` | ✅ Console UI, 201 tests | Data-driven, CORS-connected to a running API; see `docs/FRONTEND_CONTRACT.md` |
| `packages/go/{store,aoi,quality,geo}` | ✅ Shared, tested | Promoted out of `services/aisd/internal/*` — see ADR 0005 and task G |
| `packages/sagar_{ingest,sar,drift,attrib,evidence}` | ❌ Empty | READMEs only |
| `services/worker` | ❌ Empty | |
| `services/aisgen` | ⚠️ Generates real rows, never hit a live DB | 32 tests, dry-run verified end-to-end — see task G |

**PRs #2, #3, #6 all merged.** No open PRs at this point in the handover — task order below reflects `main` as of the merge of #6.

### Working agreement

**Branch → push → open a PR. Never commit directly to `main`.**

CI runs only on `main` pushes and pull requests, so pushing a feature branch alone gives you *no signal* — you must open the PR to see checks. (Earlier work in this repo went straight to `main`, which contradicted `CONTRIBUTING.md`. Don't copy that.)

---

## 2. Task order (dependency-correct)

Later tasks assume earlier ones. Deviating is fine if you know why.

```
  A. Verify migration 002 on live Postgres   ← DONE, 8 September 2026 (Docker came up)
  B. Wire Shell → the API client             ← DONE (PR #6)
  C. sagar_ingest (fetchers + cache)         ← START HERE. Needs CDSE/Copernicus Marine/
                                                AISStream accounts — none confirmed to exist yet
  D. sagar_sar M1 (preprocess)               ← everything SAR needs it
  E. sagar_sar M2 (detect)  ─┐
  F. sagar_drift M5         ─┼─ can proceed in parallel once C+D land
  G. aisgen                 ─┘  ← DONE except live-DB verification (Docker's up now — worth doing)
  H. sagar_attrib M6                         ← SCORE/RANK stages DONE without waiting on F —
                                                see task H below for why that was possible and
                                                what's still blocked
  I. services/worker                         ← needs D–H
  J. sagar_evidence M7                       ← needs I
```

Task H turned out not to strictly need F first: its SCORE/RANK stages (the log-odds model) take a drift result as a *parameter* rather than computing one, so they were buildable — and genuinely useful, wired into the live API — before F exists. Worth knowing before assuming this list's ordering is a hard dependency graph rather than a reasonable default.

**Docker is up as of 8 September 2026.** Task A is done. That unblocks live-DB work generally, but does not by itself unblock C (still needs external accounts), F (still needs WSL2/OpenDrift), or D/E (still needs a real Sentinel-1 scene, which needs C).

### Environment reality check

| Tool | State |
|---|---|
| Go 1.27.1, Node 24, Python 3.11 (uv) | ✅ Working |
| Docker Desktop | ✅ Up as of 8 September 2026 |
| WSL2 | ❌ Broken — `REGDB_E_CLASSNOTREG` |

WSL2 blocks **OpenDrift (task F) only**. It does *not* block B–E: PyTorch, `rasterio` and `sentinelhub-py` all run natively on Windows. Don't let the broken WSL stop you starting.

---

## A. Verify migration `002` on a live database — ✅ done, 8 September 2026

Applied via `docker compose up -d db` — both `001` and `002` run automatically through `docker-entrypoint-initdb.d` on first container init, no manual `-f` needed once the volume is fresh. All 12 tables confirmed present with correct indexes, FKs, and PostGIS geometry columns; the `evidence_dossiers` partial-unique-index behavior verified live (rejects a second `is_current=true` row, allows a second `is_current=false` one) via a rolled-back transaction. Full detail in `db/README.md`'s verification note.

**Not yet done, and worth doing next:** this only proves the schema is *correct*, not that anything real is *in* it — `ais_positions`/`ais_static` are still empty (the recorder has never run), and nothing has inserted a real `scenes`/`detections` row outside the rolled-back test transaction above.

---

## B. Wire Shell to the API client — ✅ done (PR #6)

`Shell.tsx` fetches through `web/src/lib/queries.ts` (TanStack Query over `api.ts`). `MapCanvas` takes `slicks`/`tracks`/`ships` as props rather than importing fixtures. `web/src/lib/adapters.ts` converts wire types to the view types the map/panels already render. All affected tests (`Shell.test.tsx`, `MapCanvas.test.tsx`) updated rather than deleted.

**One thing from the original plan that did NOT get done, stated plainly rather than left for someone to assume is covered:** Shell never calls `hindcast`, `forecast`, `evidence` or `analyse`, so the `NotImplementedError` → "not built yet" panel described in the original version of this section **was not exercised or wired up**, because nothing in the current UI reaches those endpoints. If a future task adds a hindcast/forecast panel, it must handle `NotImplementedError` explicitly then — the client already throws it (see `web/src/lib/api.ts`), the console has just never had a caller for it yet.

**Verification gap, stated plainly:** the happy path (Shell against a *running* API) has not been checked — Docker's daemon was down at the time. What **was** verified live in a browser: with no server reachable at all, the console shows `Failed to fetch` in the Detection panel rather than crashing or rendering an empty panel that implies zero detections. **Before trusting this task is fully done, bring the stack up (`docker compose up`) and confirm the console renders real fixture-backed data identically to how it looked before this change.**

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

## G. `services/aisgen` — synthetic AIS — ✅ mostly done

**This is a deliverable, not a fallback** — bulk historical AIS for Indian waters isn't publicly available, and this is the **only** source of attribution ground truth, so it's the only way to compute accuracy at all.

**The `internal/` visibility blocker is fixed.** `store`, `aoi`, and `quality` are promoted out of `services/aisd/internal/*` into `packages/go/{store,aoi,quality}` (a real, tested, shared module — not a `go.work` workspace; each module's `go.mod` uses a `replace` directive pointing at `../../packages/go`, which is simpler and works identically regardless of which directory CI happens to run from). `packages/go/geo` — previously an empty placeholder — now holds the haversine/bearing/interpolation helpers `aisgen`'s lane math needs. `aisd` was rewired to the same promoted packages and its own test suite is unchanged and still green.

`services/aisgen` is a real, working Go module: `internal/lanes` (hand-specified centrelines — see the honest limitation noted in its own doc comment), `internal/fleet` (typed vessel generation), `internal/confounders` (AIS gaps, position jumps, MMSI duplication), `internal/groundtruth` (labelled discharge events as JSON), `internal/simulate` (the tick-based orchestrator), and `cmd/aisgen` (the binary). 32 tests, all pure-function — no Postgres needed to run them.

**What's genuinely done:**
- Writes through `packages/go/store.WritePositions`/`WriteStatic` when `DATABASE_URL` is set — the exact same batched-upsert code `aisd` uses. Verified structurally: `TestPositionsAndStaticsAreAisdsOwnStoreTypes` (in `internal/simulate`) is the round-trip parity test the original README asked for, checking via reflection that `Result.Positions`/`Statics` are literally `packages/go/store`'s row types.
- **Dry-run mode** (`DATABASE_URL` unset) writes JSONL instead — this is how it was verified end-to-end without a live database (Docker was still down at the time): `go run ./cmd/aisgen` with 25 vessels/6h produced 5,204 position rows, 178 static rows, 13 ground-truth events, including all three confounder types and one discharger.
- Deterministic for a given seed (`TestRunIsDeterministicForAGivenSeed`) — needed for reproducible eval runs.
- Vessel type distribution, MMSI range (900000000+, chosen to never collide with a real MID), per-type speed/dimension profiles.

**What's still a placeholder, stated plainly:**
- **Lane geometry is hand-specified**, not the KDE-fitted centrelines from recorded traffic the requirement actually calls for — because `aisd` has never recorded a single row. `internal/lanes/lanes.go`'s doc comment says so explicitly and must not go stale once real traffic exists to fit against.
- The innocent-near-slick case is found by scanning generated positions for proximity (≤15km) at the discharge time, not specially routed — empirically fires in roughly 1 of 10 runs at 40 vessels. Real, not dead code, but infrequent; a future pass could deliberately route one vessel near the discharge instead of relying on chance.
- **Never run against a live database** — same Docker blocker as Task A. Once Docker is up: `DATABASE_URL=... go run ./cmd/aisgen` and confirm rows land in `ais_positions`/`ais_static` with `source='aisgen'`.

> The original warning stands for anyone touching this further: **do not "solve" a future integration problem by copy-pasting the insert logic** instead of importing `packages/go/store`. That silently reopens the exact gap ADR 0005 exists to close.

---

## H. `sagar_attrib` M6 — attribution — ✅ scoring built, gating/drift not started

**Read [`SCORING_MODEL.md`](SCORING_MODEL.md) in full before touching this.** It's where the project both wins and is most capable of doing harm.

```
1. GATE     backward reachability region → keep intersecting tracks    214 → 46   ❌ not started
2. FILTER   timing, kinematics, drift-score floor                       46 → 7    ❌ not started
3. SEED     interpolate tracks to 15-min steps, tag (vessel, time)                ❌ not started
4. ADVECT   ONE staggered OpenDrift run (see F)                                   ❌ blocked on OpenDrift/WSL2
5. SCORE    overlap → drift_score, t*, slick age                                  ✅ built (factors.f1_drift_consistency)
6. RANK     9-factor log-odds → Platt calibration → ranked suspects               ✅ built (model.py; hand-set priors only, no Platt fitting — calibrated=False on every Suspect)
```

**What's done, in `packages/sagar_attrib`, 66 tests, all passing:** `quality_filter.py` (§2.1a pre-filter), `baseline.py` (§2.1b per-vessel gap profile), `gap_anomaly.py` (f4, kept in its own file since it's the safety-critical one), `factors.py` (f1–f3, f5–f9), `model.py` (combine → sigmoid → `rank_candidates` producing real `sagar_core.types.Suspect` objects). None of it needed Docker, WSL2, or credentials — every function takes already-extracted numeric/boolean features and returns a real, tested result.

**What's deliberately NOT done:**
- Steps 1–4 (the GATE/FILTER/SEED/ADVECT cascade, the 214→7 traffic filter, and the drift solve itself) — need `sagar_drift`/OpenDrift, blocked on the same broken WSL2 as task F.
- **Not wired into `services/api`** — `/detections/{id}/suspects` still serves the fixture. Left alone on purpose: wiring a new, freshly-built scoring engine into an already-shipped, CI-green API surface in the same pass that built it would risk destabilising something that currently works. The API-wiring task is: build a `VesselFeatures` extractor from a raw AIS track (the one genuinely missing piece — everything downstream of "already-extracted features" is done), then swap `fixtures.SUSPECTS` for a real `rank_candidates(...)` call.

**Three real bugs the tests themselves caught, worth knowing about before extending this further:**
1. `zip(seq, seq[1:], strict=True)` in the original baseline-gap computation would have raised `ValueError` on **every non-empty input** — a sliding pairwise zip is unequal length by construction, and `strict=True` is for sequences that are supposed to match.
2. `f7_off_lane_distance`'s first version (`max(-0.5, min(1.0, distance/saturation))`) could never actually reach its documented −0.5 floor for any physically valid (non-negative) distance — fixed by shifting the whole ramp, not just clamping it.
3. The quality pre-filter's teleport check originally compared each record against the immediately preceding *raw* one; a single null-island glitch would then make the next genuinely good position look like a multi-thousand-knot jump and wrongly exclude it too. Fixed to compare against the last known-*reliable* record instead.

**Overlap scoring** — the harmonic mean is deliberate:
```
hit(v,t)      = fraction of (v,t) particles inside the slick
coverage(v,t) = fraction of slick covered by the (v,t) particle KDE
drift_score   = max over t of  2·hit·coverage / (hit + coverage)
```
`hit` alone rewards a plume that's a tiny dot inside a huge slick; `coverage` alone rewards one smeared everywhere. The F-measure penalises both. `factors.f1_drift_consistency` implements exactly this formula and takes `hit`/`coverage` as arguments — it does not compute them.

**Track interpolation:** great-circle with SOG/COG. **Never naive linear interpolation across long gaps** — it invents positions the vessel never occupied, and those fabricated positions then seed particles that generate fabricated evidence. (Not yet needed by anything built so far — this applies to the still-unstarted SEED step.)

### The AIS gap factor — the dangerous one — ✅ all three corrections implemented

The naive version (*gap near spill = suspicious*) **is wrong and produces false accusations.** Gaps are overwhelmingly innocent: cheap transponders, out-of-range operation, bad data. Three corrections, all required, all built:

1. **Data-quality pre-filter** (`quality_filter.py`) — exclude MMSI 0, position (0,0), kinematically impossible implied speed (`sagar_core.geo.implied_speed_knots`), garbled static. Labelled `unreliable`, **removed from the evidence set — they neither boost nor penalise.**
2. **Per-vessel baseline** (`baseline.py`) — computed from a vessel's own reliable history. Suspicion is deviation from *this vessel's own* normal behaviour. Without it, the factor measures transponder quality, not behaviour. A vessel with no history yet (`has_sufficient_history=False`) falls back to a documented conservative constant and is marked `FactorConfidence.LOW` — never silently scored against a fleet average.
3. **Coverage proxy** (`gap_anomaly.py`) — distance-to-coast vs terrestrial AIS range (~40–75 nm), a smooth ramp rather than a hard step. **Deliberately simple; do not build a radio propagation model.** The extra accuracy isn't worth the time and is harder to defend.

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
| ~~`aisgen` can't import `aisd`'s store~~ — fixed, see G | Was Go `internal/` visibility; resolved by promoting to `packages/go` |
| `uv venv --python 3.11` fails with `REGDB_E_CLASSNOTREG`-style path error | uv's cached interpreter is corrupt: `uv python uninstall 3.11 && uv python install 3.11` |
| Web tests fail on a missing `@testing-library/react` | `node_modules` is stale relative to `package.json` — run `npm install` |

**When a doc and the code disagree, one of them is wrong — fix it, don't work around it.** That's how the `BaselineGapProfile` field-name drift was caught before it shipped, and how [ADR 0005](adr/0005-go-for-the-ais-data-plane.md)'s incorrect AIVDM claim was found.

---

## 5. Your first hour

A concrete way in, rather than reading all of the above first:

```bash
git checkout main && git pull
# Merge PRs #2 and #3 first, or branch from feat/api-and-db-schema.

# Prove the toolchain works before changing anything.
uv venv --python 3.11 .venv
uv pip install -p .venv ruff -r services/api/requirements-dev.txt
.venv/Scripts/python.exe -m pytest -q        # expect 101 passed
cd web && npm install && npm test            # expect 132 passed
```

If those two numbers come back, the environment is sound and you can start on **task B**.

Then, before writing anything: read `packages/sagar_core/types.py` end to end. It is ~350 lines and it encodes most of the project's non-obvious rules as executable constraints — what "uncertainty is mandatory" actually means, why a confidence drop needs a penalty log, why a backward drift run refuses to weather. Understanding those saves re-deriving them from the prose docs.

### What "done" looks like for a task here

1. Branch, implement, **write the tests in the same commit**
2. `pytest -q` and `cd web && npm test` both green; `ruff check .` and `ruff format --check .` clean
3. Push, open a PR, confirm all five CI checks pass
4. In the PR body: say what you verified **and what you did not**. If something is untested because you lacked Docker/GPU/credentials, write that down rather than implying coverage you don't have.

That last point is the one habit worth carrying forward from this repo's history. Every claim in it is either backed by a command that was actually run, or explicitly marked as unverified — `db/schema/002` being the standing example.
