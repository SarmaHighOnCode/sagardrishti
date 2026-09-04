# Risk Register

Owned by the integration lead. Reviewed every Friday at the integration build.

**Rating:** Probability (Low / Medium / High / Certain) x Impact (Low / Medium / High / Fatal).
*Fatal* means the project cannot be demonstrated at the finale.

---

## Active risks

| # | Risk | P | Impact | Owner | Mitigation | Trigger to escalate |
|---|---|---|---|---|---|---|
| 1 | **Three subsystems built, none integrated** | High | **Fatal** | Integration | Vertical slice first. API contract frozen 15 Oct. **Weekly integration build that must be demoable** | Any Friday where `main` does not run end to end |
| 2 | SNAP/snappy install consumes a week | High | High | ML lead | CDSE Sentinel Hub Process API instead. SNAP-in-Docker only as offline fallback | Anyone spends more than half a day on SNAP |
| 3 | OpenDrift install fails on Windows | High | High | Ocean lead | WSL2 + micromamba + Docker from week 1. **Never attempt native Windows** | Install not working by 10 Sept |
| 4 | No real historical Indian AIS | **Certain** | Medium | AIS lead | Recorder running from day 1. Synthetic generator built properly. Method validated on NOAA US data | Already realised — mitigation is the plan |
| 5 | Model does not transfer to Indian waters | High | Medium | ML lead | Expect it, measure it, report it. Fine-tune on hand-labelled Arabian Sea scenes | Cross-domain drop exceeds 25 points |
| 6 | Drift ensembles too slow to demo | Medium | High | Ocean lead | Pre-compute and cache. Parallelise across cores. One small live-compute case | Full ensemble exceeds 20 min on the demo machine |
| 7 | **Network fails at the nodal centre** | High | **Fatal** | Integration | Full offline mode by 15 Nov, **tested twice with the cable out** | Offline test not passed by 20 Nov |
| 8 | Judge breaks the demo with an edge case | Medium | Medium | Demo owner | Rehearse failure modes. **Volunteer limits first** | — |
| 9 | Team member drops out | Medium | High | All | No single point of knowledge. Everything in the repo and MkDocs. Pair on critical modules | Any module with exactly one person who understands it |
| 10 | Overclaiming triggers hostile questioning | Medium | High | Demo owner | Product principle 1. Say *ranked candidates*, never *identifies the culprit* | Any rehearsal where a presenter says "identifies" |
| 11 | Attribution accuracy unmeasurable | High | Medium | AIS lead | Synthetic ground truth is the only path. Label it everywhere. MSC ELSA 3 as the one real case | — |
| 12 | Free-tier API quota exhausted | Low | Medium | Data ops | 10k PU/month is ample. Cache aggressively. Multiple accounts if needed | Usage exceeds 5k PU in a month |
| 13 | NISAR scope creep swallows Phase 2 | Medium | Medium | ML lead | Hard-scoped to ingest path only. **First thing cut** | Any NISAR work before Phase 2 exit criteria are met |
| 14 | **AIS gap factor produces false accusations** | High | High | AIS lead | The three corrections in `SCORING_MODEL.md` section 2.1 — data quality filter, per-vessel baseline, coverage proxy | Any suspect ranked top-3 primarily on f4 |
| 15 | Dark-vessel list floods with small exempt craft | Medium | Medium | ML lead | Coarse size bucket as a soft flag. Small craft marked *likely AIS-exempt* | Dark-vessel list exceeds ~20 per scene |
| 16 | Two toolchains (Go + Python) complicate CI | Low | Low | Integration | Go surface is small and self-contained. Separate CI jobs | Go build time exceeds 60 s |

---

## Realised risks

Move rows here when a risk materialises, with what actually happened. This is where the retrospective comes from.

| # | Risk | Date | What happened | Response | Cost |
|---|---|---|---|---|---|
| | | | | | |

---

## The three that actually kill projects

Everything above matters, but experience says three failure modes end SIH teams. Guard these specifically.

### Risk 1 — integration
Three people build three excellent subsystems, nobody wires them together until December, and the interfaces do not match. Entirely predictable and entirely preventable.

**The defence is the weekly integration build.** Not a status meeting. `main` runs end to end on Friday or the week failed. Everything else is negotiable.

### Risk 7 — the network
The venue Wi-Fi will be saturated. Assume it does not work at all.

**The defence is a cable-out test, done twice.** A team that tests offline once in November and passes will still fail in December, because dependencies get added. Test again with the frozen configuration.

### Risk 10 — overclaiming
A team that says "our system identifies the polluting vessel with 95% accuracy" invites a jury to disprove it, and a jury can. A team that says "we narrow 214 vessels to 3, here is our error budget, and here is what we cannot do" is much harder to attack and reads as more competent.

**The defence is discipline in language, rehearsed.** Correct each other during rehearsals, every time.
