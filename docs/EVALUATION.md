# Evaluation Plan

How we know it works, what we will claim, and what we will refuse to claim.

**Governing rule:** every number reported on stage traces to a command in this repository, run on a stated split. If we cannot reproduce it, we do not say it.

---

## 1. Metrics and targets

| Component | Metric | Dataset / split | Honest target |
|---|---|---|---|
| Segmentation | mIoU, oil-class IoU, F1, precision/recall | Zenodo test (150 oil / 150 look-alike / 150 no-oil); M4D if granted | mIoU 70–78%, oil IoU 60–70% |
| Look-alike rejection | **FPR on the no-oil set**, broken down by Yang/Singha look-alike cluster | Yang/Singha no-oil set | FPR < 15%, reported per cluster |
| **Cross-domain robustness** | mIoU drop, Mediterranean-trained → Persian Gulf tested | SOS test split | **Report the drop. Expect 10–20 points** |
| Ship detection | Precision/recall vs AIS ground truth | Scene with concurrent AIS | P/R > 0.85 for vessels > 50 m |
| Dark-vessel flagging | Precision | Synthetic — vessels whose AIS we deliberately suppressed | Precision > 0.8 |
| Drift model | Centroid displacement error (km), success rate vs observed slick at t+24 h | Ennore 2017; any two-pass S1 slick | Report km error honestly. Published OpenOil skill scores are 0.89–0.98 under favourable conditions — **that is a benchmark, not our promise** |
| **Attribution** | **Top-1, Top-3 accuracy, MRR** | Held-out synthetic scenarios, known culprits | **Top-3 > 80% is strong and defensible** |
| Calibration | Reliability diagram, Brier score | Held-out synthetic | Visibly calibrated, or we stop claiming probabilities |
| End-to-end | Wall clock, scene ingest → ranked suspects | Cached demo scenario | < 5 min |

### On the 2025–26 literature

Recent papers report high segmentation numbers — FCS-Net at 87.8–89.6% mIoU, ensemble methods claiming more. **Treat these carefully.** They are frequently single-dataset, single-basin, and not comparable across splits. Quoting someone else's 98% next to our 74% invites the question "why is yours worse?", whose honest answer ("different split, different basin, and theirs probably does not generalise either") is a weaker position than simply reporting our own numbers on stated splits with our cross-domain drop.

**We compete on the honesty and completeness of our evaluation, not on a single headline number.**

---

## 2. Ablations — what separates a project from a submission

Five ablations. Each answers a question a good jury will ask.

### Ablation 1 — Does the physics/context filter actually help?

Detection with and without M2 Stage C.

| Config | Oil IoU | FPR on no-oil | FPR per look-alike cluster |
|---|---|---|---|
| Stage B only | | | |
| Stage B + Stage C | | | |

**Expected:** small IoU change, **large FPR reduction**. That asymmetry is the point — Stage C is not there to find more oil, it is there to stop calling wind shadows oil.

### Ablation 2 — Forward drift vs naive nearest-ship · **the headline chart**

| Method | Top-1 | Top-3 | MRR |
|---|---|---|---|
| Nearest vessel at T_sar | | | |
| Nearest vessel at T_sar − 6 h (fixed guess) | | | |
| **Forward drift from all vessels (ours)** | | | |

**This is the single most important chart in the presentation.** It is the empirical justification for [ADR 0001](adr/0001-forward-drift-attribution.md), and it is what most competing teams will have implemented as their *entire* solution.

Break results down by slick age. The naive baseline should degrade sharply as age increases, because that is precisely its failure mode — and showing *why* a baseline fails is more persuasive than showing *that* it fails.

> **If this ablation does not favour our method substantially, ADR 0001 must be revisited.** We run it early, not the week before the finale.

### Ablation 3 — Ensemble vs deterministic drift

| Config | Origin coverage (true origin inside the field) | Field area (km²) |
|---|---|---|
| Single deterministic run | | |
| 100-member ensemble | | |

**Expected:** the deterministic run frequently misses the true origin entirely; the ensemble contains it at high rate but over a larger area. That trade is exactly what an honest uncertainty estimate looks like, and it is the justification for never reporting a point origin.

### Ablation 4 — Current product choice

1/12° model currents vs 1/4° observation-based currents, measured on drift error. Directly quantifies our sensitivity to forcing quality, and supports the "ingest INCOIS high-resolution currents" upgrade path.

### Ablation 5 — Boundary-gradient loss term

Segmentation with and without the edge-aware loss, evaluated on look-alike FPR. Tests the 2025–26 edge-prominence finding on our own data.

---

## 3. Evaluation discipline

Rules that protect us from fooling ourselves.

| Rule | Why |
|---|---|
| **The test split is touched once.** Model selection uses validation only | Repeatedly checking test performance is how you overfit a test set without noticing |
| **Fixed seeds, logged** | Every number reproducible |
| **Report variance, not just the mean** | Three seeds minimum for headline segmentation numbers. A single run is an anecdote |
| **No cherry-picked scenes** | Demo scenes are chosen for narrative; metric scenes are the full held-out split |
| **Synthetic results labelled `SYNTHETIC` everywhere** | On charts, in tables, in the dossier, on slides. Every time |
| **Failures reported alongside successes** | The look-alike cluster we do worst on goes on the slide. A jury that finds a weakness we hid discounts everything else |

### The GSD assertion

Every evaluation run asserts 40 m/px on both training and test inputs. A silent resolution mismatch would invalidate every number here — see [ADR 0002](adr/0002-fixed-ground-sample-distance.md). The assertion is in code, not in a checklist.

---

## 4. Attribution ground truth — the honest position

**Attribution accuracy cannot be measured on real data at our scale**, because it requires knowing who actually discharged. That is known for a small number of investigated incidents, and essentially never for routine operational discharge — which is the case we are built for.

Three-part strategy:

1. **Method validation on real data.** Run the engine on NOAA MarineCadastre US AIS with real vessel tracks. We cannot score attribution accuracy (no ground-truth culprits), but we *can* verify that the gate, seeding, drift and scoring behave correctly on real, messy tracks with real gaps and real reporting irregularities.

2. **Accuracy measurement on synthetic data.** `aisgen` injects labelled discharge events with known vessel, time, location and rate. This is the **only** way to compute top-1/top-3/MRR. Every such number is labelled `SYNTHETIC`.

3. **One real known-culprit case.** MSC ELSA 3 — known vessel, known approximate time, ICG-confirmed slick. A single case is an anecdote, not a statistic, and we will present it as an illustration rather than as validation.

**The viva answer:**

> "Attribution accuracy is measured on synthetic scenarios because attribution ground truth requires knowing who actually discharged, which is not available at scale for anyone. We validate that the *method* behaves correctly on real AIS from the NOAA dataset, we measure accuracy on synthetic events with known culprits, and we illustrate on one real case with a known vessel. We label every synthetic number as synthetic. Anyone claiming measured attribution accuracy on real routine-discharge data does not have ground truth either."

---

## 5. What we will not claim

| Never claim | Why |
|---|---|
| "95% accurate at identifying the polluting vessel" | We rank candidates. We do not identify culprits. Product principle 1 |
| A single accuracy number for the whole system | Seven modules with different failure modes. One number hides all of them |
| Operational readiness | It is a prototype. Saying so buys credibility we can spend elsewhere |
| Oil type or volume | Not retrievable from C-band SAR. Out of scope, stated |
| That synthetic results are real-world performance | Every synthetic number carries the label |
| That we beat published SOTA | Different splits, different basins. Not comparable, and the claim invites scrutiny we would lose |

---

## 6. Reporting artefacts

Produced by `make evaluate`, versioned in the repository:

```
ml/evaluation/results/
  segmentation_metrics.json        per-split, per-seed
  lookalike_breakdown.csv          FPR by Yang/Singha cluster
  crossdomain_comparison.json      the drop, stated plainly
  attribution_ablation.json        ablation 2 — the headline
  drift_validation.json            Ennore benchmark
  calibration_curve.json           reliability diagram data
  figures/                         every chart used in the deck
```

**Each figure is generated by a script, never drawn by hand.** When a number changes, the chart changes with it. Hand-made charts drift from the data they claim to show, and a jury that catches that has caught something serious.

---

## 7. Pre-demo checklist

Run before every rehearsal and before the finale:

- [ ] Every metric in §1 has a current value from a logged run
- [ ] Ablation 2 chart regenerated from current results
- [ ] Cross-domain drop stated on the honest-limits slide
- [ ] All synthetic numbers labelled `SYNTHETIC`
- [ ] Every claim in the deck traceable to a file in `ml/evaluation/results/`
- [ ] Worst-performing look-alike cluster known and stated — we volunteer it
- [ ] Calibration diagram current
- [ ] `make evaluate` runs clean, offline, from cache
