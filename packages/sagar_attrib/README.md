# `sagar_attrib` — M6

Traffic gating, drift overlap scoring, and the suspect model. **Owner: AIS/attribution lead.**

> **This is where the project wins, and where it is most capable of doing harm.** Read [`SCORING_MODEL.md`](../../docs/SCORING_MODEL.md) in full before changing anything here.

## Status: steps 5–6 (scoring) built and tested. Steps 1–4 (gating, drift) not started.

```bash
cd packages/sagar_attrib  # or run from repo root — pytest finds it either way
pytest ../../packages/sagar_attrib -v   # 66 tests
```

| Module | Does | Status |
|---|---|---|
| `quality_filter.py` | §2.1(a) data-quality pre-filter — MMSI 0, null island, out-of-range, impossible implied speed | ✅ Built, tested |
| `baseline.py` | §2.1(b) per-vessel baseline gap profile (median/p95/sample count) | ✅ Built, tested |
| `gap_anomaly.py` | f4 — deviation from own baseline × coverage proxy | ✅ Built, tested (own file — the safety-critical factor) |
| `factors.py` | f1, f2, f3, f5–f9 | ✅ Built, tested |
| `model.py` | Combine into logit → sigmoid → ranked `Suspect` list | ✅ Built, tested |
| GATE/FILTER (214→46→19→11→7 cascade) | — | ❌ Not started |
| SEED/ADVECT (drift solve itself) | — | ❌ Blocked on `sagar_drift`/OpenDrift (WSL2 broken) |
| Wiring into `services/api`'s fixture-backed `/suspects` endpoint | — | ❌ Not started — deliberately left alone rather than risk destabilising a shipped, CI-green surface in the same pass that built the scoring engine |

**The honest boundary, stated in `factors.py`'s own docstring for `f1_drift_consistency`:** this module does not run OpenDrift and never will (that's `sagar_drift`'s job). `f1` takes `hit`/`coverage` — the output of an M5 ensemble solve — as arguments. Every other factor (f2–f9, including the safety-critical f4) is genuinely computed here from AIS + context data, no external physics needed.

**Every claim above is backed by a passing test**, including three real bugs the tests themselves caught during development: `zip(seq, seq[1:], strict=True)` in the baseline-gap computation would have raised on every non-empty input (sliding-pairwise zips are unequal length by construction); `f7_off_lane_distance`'s original formula could never actually reach its documented negative floor for any physically valid distance; and the teleport check originally would have let one bad GPS glitch cascade into wrongly excluding every good position that followed it.

## Pipeline

```
1  GATE       backward reachability region -> keep intersecting tracks   214 -> 46    ❌ not started
2  FILTER     timing, kinematics, drift-score floor                       46 -> 7     ❌ not started
3  SEED       interpolate tracks to 15-min steps, tag (vessel, time)                  ❌ not started
4  ADVECT     ONE staggered OpenDrift run, ensembled              (sagar_drift)       ❌ blocked on OpenDrift/WSL2
5  SCORE      overlap -> drift_score, t*, slick age                                   ✅ factors.f1_drift_consistency
6  RANK       9-factor log-odds -> Platt calibration -> ranked suspects               ✅ model.py (hand-set priors only — no Platt fitting yet, calibrated=False)
```

## Overlap scoring

```
hit(v,t)      = fraction of (v,t) particles landing inside the slick
coverage(v,t) = fraction of slick covered by the (v,t) particle KDE
drift_score   = max over t of  2*hit*coverage / (hit + coverage)
t*            = argmax t
slick age     = T_sar - t*,  band from ensemble spread
```

**The harmonic mean is deliberate.** `hit` alone rewards a plume that is a tiny dot inside a huge slick; `coverage` alone rewards a plume smeared everywhere. The F-measure penalises both.

## Track interpolation

Great-circle with SOG/COG. **Never naive linear interpolation across long gaps** — it invents positions the vessel never occupied, and those fabricated positions then seed particles that generate fabricated evidence.

Gaps beyond a threshold are left as gaps and the segment is marked low-confidence.

## The AIS gap factor — handle with care

The naive version — *gap near spill equals suspicious* — **is wrong and produces false accusations.** Gaps happen for innocent reasons constantly: cheap transponders, out-of-range operation, bad data.

Three corrections, all required:

**(a) Data quality pre-filter.** Exclude MMSI 0, position stuck at (0,0), kinematically impossible implied speed, garbled static data. These are labelled `data_quality: unreliable` and **removed from the evidence set — they neither boost nor penalise a score.** A vessel must never become a suspect *because* its transponder is broken.

**(b) Per-vessel baseline gap profile.** Cached per MMSI from prior weeks. Suspicion is measured as **deviation from this vessel's own normal behaviour**. A vessel that routinely drops out for hours scores low. A vessel that reports like clockwork for months and then has one gap at the inferred release time scores high. Without this the factor measures transponder quality, not behaviour.

**(c) Coarse coverage proxy.** Distance-to-coast against a terrestrial-AIS threshold (~40–75 nm). Offshore gaps are discounted. **Deliberately simple** — a radio propagation model is not worth the time and is harder to defend.

**And f4 is never a standalone trigger.** It is one of nine weighted inputs; drift consistency (weight 2.5) dominates by design against an intercept of −4.0.

## Never a neural network here

Tens of labelled attribution events. Ten weights. A network would overfit and report the overfit as accuracy — and our user must justify a boarding decision. The log-odds model **is** the explanation: the factor bars in the UI are the actual terms of the computation. [ADR 0003](../../docs/adr/0003-transparent-log-odds-scoring.md).

## Reporting

**Top-3 accuracy is the headline, not top-1.** Narrowing 214 vessels to 3 for an ICG investigator is the operational win. Every synthetic number is labelled `SYNTHETIC`.

## The governing asymmetry

**A wrongful accusation against an innocent operator is far worse than a missed detection.** Where a choice trades false positives against false negatives, take fewer flags with better evidence. Exclusions never become negative evidence; missing factors are dropped, never imputed; vessel type is a weight, never a filter.
