# Roadmap

SIH 2026 launched 21 August. Internal hackathons run through September, national screening in October, **Grand Finale December 2026 (36 hours)**.

Roughly fourteen weeks. The plan below is deliberately front-loaded: a working vertical slice early beats a broad, unintegrated system late.

> **Status as of 7 September 2026.** Checkboxes below are verified against `main`, not aspirational. The short version: infrastructure is well ahead of plan — CI, schema, contracts, ~5,600 lines of tested scaffolding — and the four pipeline subsystems the PS is actually judged on (M1–M7) are **at zero lines of code**. Phase 0's exit criterion is one video of a real detection drifting backward; nothing built so far produces one. See the checklist below for exactly what's outstanding, and [`HANDOVER.md`](HANDOVER.md) for the code-level next steps.

---

## Governing principles

1. **Vertical slice before breadth.** One scene, end to end, badly, beats four excellent disconnected subsystems.
2. **The weekly integration build is sacred.** Every Friday `main` runs end to end. This is the primary defence against the failure mode that kills most SIH teams.
3. **Freeze the API contract 15 October.** Frontend and backend cannot both be moving in November.
4. **Cut scope, never cut integration.** If something must go, drop a feature — never the "does it all run together" work.
5. **Arrive at the finale with a finished system.** The 36 hours are for responding to jury feedback, not for building.

---

## Phase 0 — Internal hackathon · 3–25 September

**Goal:** a 6-slide deck and a video showing detection → polygon → backward drift. That is enough to advance.

### Day one — do these today

- [ ] **Start the AISStream recorder** for the Arabian Sea and Bay of Bengal. *(AIS lead)* — **highest-leverage action in the project. NOT STARTED — already 4+ days overdue.** `aisd` is built, tested (34 tests) and live-verified against a real Postgres, but it has never been run continuously against the real feed. It needs an AISStream API key and a host that stays up. No replay exists; every day of delay is data permanently lost — this is not a soft deadline, it is a shrinking ceiling on how much lane-calibration data `aisgen` will ever have
- [ ] Create accounts: CDSE, Copernicus Marine, ECMWF CDS, AISStream, NASA Earthdata *(Data ops)* — no evidence any exist yet. **Blocks Week 1's Sentinel-1 fetch entirely**
- [ ] **Request the Krestenitis/M4D dataset** *(ML lead)* — not requested
- [x] Repository initialised, CI running *(Integration)* — 5 CI jobs, all green on `main`
- [ ] Branch protection on *(Integration)* — **confirmed not enabled** (`gh api .../branches/main/protection` → 404). Needs repo admin

### Week 1 — 3–10 September

- [ ] WSL2 + Docker + micromamba working on **both** machines, GPU verified *(everyone)* — WSL2 is broken on at least one machine (`REGDB_E_CLASSNOTREG`); Docker Desktop installed but the daemon was not running as of last check
- [ ] Zenodo dataset downloaded and inspected *(ML lead)* — not started
- [ ] One Sentinel-1 scene fetched through CDSE end to end *(ML lead)* — not started; blocked on the CDSE account above
- [ ] OpenDrift installed, one forward run completing *(Ocean lead)* — not started; blocked on WSL2
- [x] Compose stack up: PostGIS + Redis + a hello-world API *(Integration)* — verified live in PR #1. The API has since grown into the full contract surface (fixture-backed)
- [ ] `aisd` recording verified, rows landing in Timescale *(AIS lead)* — the code path is tested; **no live recording has ever run**. Same item as the Day One entry above

### Week 2 — 11–18 September

- [ ] M1 preprocessing producing a 40 m/px COG *(ML lead)* — not started. `packages/sagar_sar` is 0 lines
- [ ] Baseline DeepLabv3+ trained, any mIoU *(ML lead)* — not started
- [ ] One backward OpenDrift run producing a particle cloud *(Ocean lead)* — not started. `packages/sagar_drift` is 0 lines
- [ ] AIS decode → PostGIS → query by bbox and time *(AIS lead)* — **partial.** `aisd` decodes and writes to `ais_positions` (tested, not yet run live). The API's `/ais/tracks` endpoint exists and is queried by the console, but currently serves fixture data, not a real PostGIS query
- [ ] MapLibre page rendering an S1 tile, a polygon and an AIS track *(Frontend)* — **partial.** Polygon and AIS track render, wired to a live API call. **No S1 tile** — no raster tiler, no COG exists to serve
- [x] Design tokens implemented from [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md) *(Frontend)* — done

### Week 3 — 19–25 September

- [ ] The three pieces wired together, however crudely *(Integration)*
- [ ] **Video recorded:** detection → polygon → backward drift animation *(Demo owner)*
- [ ] 6-slide deck *(Demo owner)*
- [ ] Submitted

**Phase 0 exit criterion:** a video showing a real slick detected on a real scene, drifting backwards. Nothing else is required. **Not yet met — no detection model and no drift engine exist.**

---

## Phase 1 — End-to-end spine · 26 September – 15 October

**Goal:** the full pipeline runs on one cached scene with zero manual steps.

- [ ] M1 → M2 → M3 orchestrated through the worker *(ML lead, Integration)* — neither M1–M3 nor `services/worker` have any code yet
- [ ] **SegFormer-B2 trained and evaluated; model card written** *(ML lead)*
- [ ] M5 backward and forward runs callable from the API *(Ocean lead)* — `packages/sagar_drift` is 0 lines; the API's `hindcast`/`forecast` endpoints already exist and correctly return `501` for this reason
- [ ] **`aisgen` producing valid AIS**, written through `aisd`'s shared `internal/store` path *(AIS lead)* — not started. Building this needs the `internal/` visibility fix noted in [ADR 0005](adr/0005-go-for-the-ais-data-plane.md) first. **See PR #10** — this fix, and a working `aisgen`, are built and awaiting merge as of this line
- [ ] M6 per-vessel forward drift producing a ranked list — hand-set weights are fine *(AIS lead, Ocean lead)* — **partial.** `packages/sagar_attrib`'s SCORE+RANK stages (the 9-factor log-odds model, all three AIS-gap corrections, hand-set priors) are built and tested (66 tests) — see `docs/HANDOVER.md` task H. The GATE/FILTER/SEED/ADVECT stages (the 214→7 traffic cascade and the drift solve itself) are not started, blocked on `sagar_drift`/OpenDrift. The API's suspect-ranking endpoints still serve fixture data — not yet wired to the new scoring engine
- [ ] Reachability gate working; the 214 → 7 cascade real *(AIS lead)* — the audit-trail endpoint and UI exist and display this cascade, but the numbers are a hardcoded fixture matching the PRD's own worked example, not a computed result
- [ ] PostGIS schema stable and migrated *(Integration)* — **partial.** Migration `001` (AIS tables) is live-verified. Migration `002` (scenes/detections/suspects/jobs) is written and parses cleanly against Postgres's real grammar but **has never been executed against a live database**
- [ ] Console showing detection, tracks and a suspect list from live API data *(Frontend)* — **partial, same shape as the items above.** The console now genuinely fetches over HTTP rather than importing sample arrays (task B, PR #6), but the API it calls still serves fixture data, not real pipeline output. Left unchecked for the same reason the AIS-decode and MapLibre items above are: the frontend half is done, the data behind it is not
- [ ] **Ablation 2 run early** — forward drift vs naive nearest ship *(AIS lead)* — cannot run without M5 and M6 existing

> **⚠ 15 OCTOBER — FREEZE THE API CONTRACT.** After this date, changes require the integration lead's sign-off. This is the single most important date on the roadmap.

**Phase 1 exit criterion:** `make demo` runs a scene end to end and produces a ranked suspect list, unattended.

---

## Phase 2 — Depth · 16 October – 15 November

**Goal:** everything that makes it more than a baseline.

- [ ] **M2 Stage C physics/context filter** with all auxiliary layers *(ML lead, Ocean lead)* — the differentiator
- [ ] Ensemble drift with the full perturbation set *(Ocean lead)*
- [ ] Scoring model fitted and **calibrated**; reliability diagram *(AIS lead)*
- [ ] **Per-factor explanation UI** *(Frontend)* — the 6:30 demo beat
- [ ] **Rejection panel with reasons** *(Frontend)* — the 1:50 demo beat
- [ ] M4 CFAR ship detection + dark-vessel flagging *(ML lead)*
- [ ] M7 evidence dossier with full provenance *(Integration)*
- [ ] MSC ELSA 3 and Ennore scenarios reproduced *(Data ops, Ocean lead)*
- [ ] **All five ablations run, all figures generated** *(ML lead, AIS lead)*
- [ ] Cross-domain evaluation and the drop reported *(ML lead)*
- [ ] Timeline scrubber driving every layer *(Frontend)*
- [ ] *Stretch:* NISAR ingest path demonstrated *(ML lead)* — **first thing cut if anything slips**

**Phase 2 exit criterion:** every demo beat in [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) works.

---

## Phase 3 — Harden · 16 November – finale

**Goal:** nothing can go wrong that has not already been rehearsed.

- [ ] **Offline mode complete. Cable-out test passed** *(Integration)* — see [`OFFLINE_MODE.md`](OFFLINE_MODE.md)
- [ ] **Cable-out test passed a second time** with frozen scenarios *(Integration)*
- [ ] Demo cache pre-computed for all four scenarios *(Data ops)*
- [ ] Error handling everywhere — **no stack trace ever reaches the screen** *(everyone)*
- [ ] Documentation site live *(Demo owner)*
- [ ] **20+ rehearsals**, including 3 offline and 2 with a hostile-judge simulation *(Demo owner)*
- [ ] Recorded full-run video *(Demo owner)*
- [ ] Screenshot fallback deck *(Demo owner)*
- [ ] **Backup laptop, independently built and separately tested** *(Integration)*
- [ ] Finale backlog prepared — small, high-visual-impact items deliberately left undone

**Phase 3 exit criterion:** the demo runs, offline, twenty times in a row, with a recovery path rehearsed for every failure mode.

---

## Phase 4 — Grand Finale · December, 36 hours

**Do not rebuild anything.** Arrive with a working system.

Use the 36 hours to implement the specific increments the jury asks for during mentoring rounds. Juries reward visible responsiveness to their feedback, and a team that ships a requested feature between rounds makes a strong impression.

**The finale backlog** — prepare this in Phase 3. Small, self-contained, visually obvious items you have deliberately left undone:

- Additional eco-sensitive zone layers
- A second demo region (Bay of Bengal)
- Export formats — KML, Shapefile
- An analyst annotation layer
- Additional suspect-list sort and filter options
- A comparison view for two scenes over the same area

Each should be a few hours' work with a visible result. When a mentor suggests something adjacent, you can ship it before the next round.

---

## Ownership

| # | Role | Owns | Phase 0 critical path |
|---|---|---|---|
| 1 | **SAR/ML lead** | M1, M2, M3 | S1 fetch, baseline model |
| 2 | **Ocean/drift lead** | M5 | OpenDrift running |
| 3 | **AIS/attribution lead** | M4, M6, Go data plane | **AISStream recorder, today** |
| 4 | **Backend/integration** *(Dev)* | API, DB, orchestration, Docker, CI, M7, **"does it all run"** | Compose stack, CI |
| 5 | **Frontend** | Console, map, design system | MapLibre + tokens |
| 6 | **Data ops + demo owner** | Data acquisition, demo cache, docs, presentation, rehearsals | Accounts, dataset requests, the video |

---

## Milestones

| Date | Milestone | Hard? | Status (7 Sept) |
|---|---|---|---|
| **3 Sept** | AIS recorder running | **Yes — irrecoverable if missed** | ⚠️ **Missed. 4+ days overdue and still not started** — the window did not close, but every day since 3 Sept is data that can never be recovered. Start it today regardless of how late |
| 25 Sept | Internal hackathon submission | Yes | At risk — Phase 0 exit criterion (a real detection drifting) has zero progress with 18 days left |
| **15 Oct** | **API contract frozen** | **Yes** | On track — contract is implemented and stable now, well ahead of schedule |
| 15 Oct | End-to-end spine working | Yes | At risk — see Phase 1 checklist |
| 15 Nov | Feature complete; ablations done | Yes | Too early to call |
| **~20 Nov** | **Offline test passed** | **Yes** | Too early to call |
| Early Dec | 20 rehearsals complete | Yes | Too early to call |
| Dec | Grand Finale | — | — |

---

## What gets cut, in order

When time runs short — and it will — cut in this order. Decide now, calmly, rather than in November under pressure.

1. NISAR ingest *(stretch from the start)*
2. Sentinel-2 quicklook overlay
3. Bay of Bengal second region
4. Forward forecast shoreline impact detail
5. Ablations 4 and 5 *(keep 1, 2, 3 — 2 especially)*
6. Dark vessel detection *(reluctantly — it is high value for NTRO)*

**Never cut:** the physics/context filter, per-factor explanations, the honest-limits slide, offline mode, or ablation 2. Those are the project.
