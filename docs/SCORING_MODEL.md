# Scoring Model

How SAGARDRISHTI ranks suspect vessels, why each weight is what it is, and how we keep the output honest.

Decision rationale: [ADR 0003](adr/0003-transparent-log-odds-scoring.md). Algorithm context: [PRD §8](PRD.md).

---

## 1. The model

```
logit(P_suspect) = w0 + Σ  wi · fi
```

Nine factors, each normalised to roughly `[0, 1]` (or `[-1, 1]` where a factor can argue for innocence), combined additively in log-odds space, then calibrated to a probability.

**Why log-odds.** Each term `wi · fi` is literally the evidence that factor contributes, in a unit comparable across factors. This is what makes the per-factor bars in the interface honest — they are the actual terms of the computation, not a post-hoc approximation of an opaque model. An analyst can read the arithmetic.

---

## 2. The nine factors

Weights below are the **hand-set priors**. They are deliberately published before fitting so that the fitted values can be compared against them, and so a domain expert can argue with them. That argument is a feature.

### f₁ — Drift consistency · `w₁ = 2.5`

**What it measures.** How well the vessel's forward-drifted plume matches the observed slick, maximised over release time:

```
hit(v,t)      = fraction of (v,t) particles landing inside S
coverage(v,t) = fraction of S covered by the (v,t) particle KDE above threshold
f_drift(v)    = max over t of  2·hit·coverage / (hit + coverage)
```

**Why the harmonic mean.** `hit` alone rewards a vessel whose plume is a tiny dot inside a huge slick. `coverage` alone rewards a vessel whose plume smears across the whole region. The F-measure penalises both failure modes, which is exactly what we want.

**Why the highest weight.** This is the physical evidence. Everything else is circumstantial. A vessel that could not have put oil where the oil is should not be a suspect regardless of how suspiciously it behaved.

**Range** `[0, 1]`. **Failure mode:** in a dense lane, several vessels score highly — which is precisely why the other eight factors exist.

---

### f₂ — Course alignment · `w₂ = 1.4`

**What it measures.** `|cos(θ_slick − θ_COG(t*))|` — alignment between the slick's major-axis bearing (from M3) and the vessel's course over ground at the inferred release time.

**Physical basis.** A vessel discharging while under way lays a trail *along its track*. An elongated slick whose long axis aligns with a candidate's heading is strong corroboration; one lying perpendicular to it is hard to explain.

**Why 1.4.** Strong and physically grounded, but it degrades for near-circular slicks where major-axis bearing is ill-defined, and for old slicks that have been rotated by shear.

**Range** `[0, 1]`. **Guard:** suppress this factor entirely when slick eccentricity is below a threshold — a bearing for a nearly round slick is noise, and feeding noise in as evidence is worse than omitting the term.

---

### f₃ — Speed anomaly · `w₃ = 1.1`

**What it measures.** How far the vessel's SOG at `t*` departs *below* its own median SOG for the voyage.

**Physical basis.** Operational discharge is typically performed at reduced, steady speed — it takes time and the crew wants controlled dispersal.

**Why relative to the vessel's own median, not an absolute threshold.** 8 knots is slow for a container ship and normal for a trawler. Self-referencing removes vessel-class confounding automatically.

**Range** `[0, 1]`, one-sided — only slower-than-usual counts. A vessel going *faster* than usual is not evidence of innocence, so this factor never contributes negatively.

---

### f₄ — AIS gap anomaly at inferred release · `w₄ = 1.3`

> **This factor was redefined.** The naive version — *"a gap exists near the spill, therefore suspicious"* — is wrong and would produce false accusations. See §2.1 below for the full treatment; it is the most dangerous factor in the model and the one most likely to harm an innocent operator.

**What it measures.** Not the presence of a gap. **How far this gap deviates from *this vessel's own* baseline gap behaviour**, discounted by expected AIS coverage at that location.

```
f_gap = deviation_from_own_baseline(gap | vessel history)  ×  coverage_confidence(position)
```

**Physical basis.** Switching off AIS during a discharge is a documented evasion signature, and it is behaviourally specific in a way most factors are not. But a raw gap is not that signature — it is one of at least three things, and only one of them is evidence.

**Why not higher.** Even corrected, we cannot fully distinguish "switched off" from "out of receiver range" or "cheap transponder." The weight stays moderate because the underlying observation is irreducibly ambiguous.

**Range** `[0, 1]`, saturating at roughly 60 minutes of *anomalous* gap.

---

### 2.1 The AIS gap problem, and how f₄ is corrected

**AIS gaps happen for innocent reasons, constantly.** Treating them all as evidence would systematically incriminate the operators least able to defend themselves — small and older fishing vessels with flaky transponders, and any vessel legitimately working far offshore.

| Cause of gap | Frequency | Is it evidence? |
|---|---|---|
| Cheap, old or misconfigured transponder dropping out | Very common, especially small craft | **No.** It happens everywhere, always — not just near this spill |
| Vessel beyond terrestrial receiver range (~40–75 nm) | Very common offshore | **No.** That is radio physics, not behaviour |
| Bad data — MMSI 0, reused MMSI, GPS stuck at (0,0), impossible speed jumps | Common and well documented | **No.** That is a data quality defect |
| Deliberate shutdown at an unusual time and place, by a vessel that otherwise reports reliably, within good coverage | Rare | **Yes.** This is the signal |

Three corrections, all of which must be implemented for f₄ to be safe to use:

#### (a) Data quality pre-filter — runs before any scoring

Records are labelled `data_quality: unreliable` and **excluded from the confident evidence set** when they show:

- MMSI of 0, or otherwise structurally invalid
- Position stuck at exactly (0, 0), or otherwise implausible
- Implied speed between consecutive positions that is kinematically impossible for the vessel type — a merchant vessel does not travel at 45 knots
- Blank or garbled static/voyage data

**Critical rule: unreliable records neither boost nor penalise a vessel's score.** They are removed from the evidence set, not converted into negative evidence. A vessel with a broken transponder must not become a suspect *because* its transponder is broken — that would invert the entire logic of the system.

#### (b) Per-vessel baseline gap profile — computed once per MMSI, cached

For each vessel, derive its normal reporting behaviour from prior weeks or months of history: gap frequency, and the distribution of typical gap durations.

**This baseline is what "suspicious" is measured against.**

- A vessel that routinely drops out for hours scores **low** on gap suspicion even when it also has a gap near the spill. That is just how it always behaves.
- A vessel that has reported like clockwork for months and then has one unusual gap at the inferred release time and place scores **high**.

Without this, the factor measures transponder quality rather than behaviour.

#### (c) Coarse coverage proxy — deliberately simple

Approximate expected AIS coverage from **distance to coast** against a terrestrial-range threshold (~40–75 nm). Near shore, a gap is meaningful. Far offshore with no satellite AIS, a gap is expected regardless of intent, and f₄ is weighted down accordingly.

> **Do not over-engineer this.** A radio propagation model would be more accurate and is not worth the time — the correction it would buy is small compared to the correction that distance-to-coast already provides. A simple, documented, explainable threshold is the right level of sophistication here, and it is far easier to defend in a viva.

#### (d) f₄ is never a standalone trigger

f₄ remains **one weighted input among nine**. A high gap-anomaly score alone must never mark a vessel as a suspect. Drift consistency (f₁, weight 2.5) dominates by design: a vessel that could not physically have put oil where the oil is does not become a suspect because its transponder was quiet.

This is enforced structurally — the intercept `w₀ = −4.0` means f₄ at its maximum contributes 1.3 against a −4.0 baseline, which is nowhere near sufficient to cross a suspicion threshold on its own.

---

### f₅ — Course change near release · `w₅ = 0.6`

**What it measures.** Magnitude of course alteration in the window around `t*`.

**Physical basis.** Weak. Some operators alter course to discharge away from the lane; many do not. Course changes also have entirely innocent causes — traffic separation, weather, waypoints.

**Why low.** Genuinely weak evidence. Included because it costs nothing and occasionally corroborates, but it should never drive a ranking on its own.

**Range** `[0, 1]`.

---

### f₆ — Night-time release · `w₆ = 0.5`

**What it measures.** Solar elevation below the horizon at the vessel's position at `t*`.

**Physical basis.** Deliberate discharge is more common at night — lower visual detection risk. But SAR is a day/night sensor and a large fraction of legitimate traffic operates at night.

**Why low.** It is a base-rate factor, not an individuating one. Roughly half of all vessel-hours are at night; treating that as strong evidence would incriminate half the fleet.

**Range** `{0, 1}`, or smoothed across twilight.

---

### f₇ — Off-lane distance · `w₇ = 0.8`

**What it measures.** Distance from the traffic-lane KDE ridge derived from recorded AIS.

**Physical basis.** Deliberate discharge away from observed traffic reduces witness risk. A vessel well outside the established lane at the release time is mildly notable.

**Why moderate and why it can go negative.** Fishing vessels, offshore support craft and coastal traffic legitimately operate outside main lanes constantly. This factor **can contribute negatively** — a vessel squarely in the middle of a busy lane is marginally *less* likely to have chosen that moment to discharge.

**Range** `[-0.5, 1]`.

---

### f₈ — Vessel type prior · `w₈ = 0.7`

**What it measures.** A prior over vessel type from AIS static data (type 5/24): tanker > bulk carrier > container > general cargo > fishing > other.

**Physical basis.** Tankers carry oil cargo residues and generate more oily waste. Larger vessels generate more sludge.

**Critical constraint — this is never a hard filter.** Small vessels absolutely do discharge, AIS static data is frequently wrong or absent, and type can be spoofed. A hard filter on type would create a systematic blind spot that anyone who reads our documentation could exploit.

**Range** `[0, 1]`. **Guard:** when static data is missing, the factor is *dropped*, not defaulted. Assuming a type we do not know is fabricating evidence.

---

### f₉ — Contextual proximity · `w₉ = 0.4`

**What it measures.** Composite: distance to nearest port, distance to offshore platform, proximity to a protected or eco-sensitive area.

**Physical basis.** Weak and ambiguous in both directions — discharge near a platform might implicate the platform rather than the vessel; discharge near a protected area is not more *likely*, only more *serious*.

**Why lowest.** Because the reasoning is genuinely ambiguous. It is included mainly to surface the platform-as-alternative-source case to the analyst.

**Range** `[0, 1]`.

---

## 3. Weight summary

| Factor | Symbol | Prior weight | Evidence class | Can be negative |
|---|---|---|---|---|
| Drift consistency | f₁ | **2.5** | Physical | No |
| Course alignment | f₂ | 1.4 | Physical | No |
| AIS gap at release | f₄ | 1.3 | Behavioural | No |
| Speed anomaly | f₃ | 1.1 | Behavioural | No |
| Off-lane distance | f₇ | 0.8 | Behavioural | **Yes** |
| Vessel type prior | f₈ | 0.7 | Prior | No |
| Course change | f₅ | 0.6 | Behavioural | No |
| Night-time | f₆ | 0.5 | Base rate | No |
| Contextual proximity | f₉ | 0.4 | Contextual | No |
| Intercept | w₀ | −4.0 | — | — |

**The intercept is strongly negative on purpose.** The prior probability that any given vessel in a busy shipping lane discharged oil is very low. A model that does not encode that will produce inflated posteriors for everyone and the calibration will be worthless.

**Physical evidence outweighs behavioural evidence roughly 2:1** (f₁ + f₂ = 3.9 versus f₃ + f₄ + f₅ + f₆ + f₇ = 4.3, but f₁ alone dominates any single behavioural factor). That ordering is deliberate: behaviour is suggestive, physics is probative. A vessel cannot have discharged oil that could not have drifted to where the oil is, no matter how suspiciously it was behaving.

---

## 4. Fitting and calibration

**Step 1 — hand-set priors.** The weights above, justified in §2. These ship as defaults and work without any training data.

**Step 2 — logistic regression.** Fit on synthetic labelled events (`aisgen` ground truth). Same functional form, so fitted weights stay interpretable and directly comparable to the priors. **We report both**, and any large divergence gets investigated rather than accepted — a fitted weight that contradicts physical reasoning usually means a bug in a feature, not a discovery.

**Step 3 — regularisation.** L2, strong. Tens of examples, ten parameters. The prior weights act as the regularisation target, so the fit shrinks toward physically justified values rather than toward zero.

**Step 4 — calibration.** Platt scaling or isotonic regression on a held-out split, so that "0.7" means close to "right 70% of the time." **Report the reliability diagram in the evaluation.** Claiming calibrated probabilities without showing calibration is exactly the sort of overclaim that invites hostile questioning.

---

## 5. Honest limitations

State these before anyone finds them.

| Limitation | Consequence | Mitigation |
|---|---|---|
| **Ground truth is synthetic** | Fitted weights are only as good as `aisgen`'s realism. If the generator's discharge behaviour is naive, we fit to our own assumptions | Report hand-set and fitted weights separately; validate the *method* on real NOAA US AIS; keep MSC ELSA 3 as one real known-culprit case |
| **Tens of labelled events** | Cannot fit interactions; confidence intervals on weights are wide | Strong L2 toward physical priors; report interval estimates, not point weights |
| **AIS gap factor confounded by coverage and equipment quality** | Risk of systematically incriminating offshore vessels and small craft with poor transponders | The three corrections in §2.1 — data quality pre-filter, per-vessel baseline, coverage proxy. **All three must actually be implemented, not just documented.** Without them f₄ is actively harmful |
| **Baseline profile needs vessel history** | A vessel first seen near the spill has no baseline to compare against | Fall back to a vessel-class prior and **mark the factor low-confidence in the UI**. Never substitute the fleet average silently — an unknown vessel is unknown, not average |
| **Correlated factors** | f₃ (speed) and f₅ (course change) are not independent; log-odds additivity assumes they are | Accept and disclose. With our data volume, modelling the correlation is not defensible either |
| **Dark vessels score zero on AIS factors** | A vessel with no AIS cannot be scored on f₃–f₈ | Handled separately — dark vessels enter through M4 with their own confidence, not through this model. Never rank a dark vessel against AIS-scored vessels on the same scale |

---

## 6. What we report

**Top-3 accuracy is the headline metric, not top-1.** An ICG analyst investigating three vessels instead of two hundred is the operational win. Claiming 95% top-1 on synthetic data would be both less credible and less useful.

| Metric | Why |
|---|---|
| **Top-3 accuracy** | The operational metric |
| Top-1 accuracy | Reported for completeness |
| Mean reciprocal rank | Rewards ranking the true culprit high even when not first |
| Reliability diagram | Proves the probabilities mean something |
| Per-factor ablation | Which factors actually carry weight |
| **vs naive-nearest-ship baseline** | The headline chart — see [`EVALUATION.md`](EVALUATION.md) |

---

## 7. Product rule, restated

**The system ranks. It never accuses.**

The output is *"Vessel X is the most drift-consistent candidate at 0.71 posterior, driven by these five factors"* — never *"Vessel X is guilty."*

Every suspect view shows **all** factor contributions, including those arguing for innocence. Hiding exculpatory evidence would destroy the legal-defensibility claim that justifies M7 existing at all.

### 7.1 The asymmetry that governs every design choice here

**A wrongful accusation against an innocent vessel operator is a far worse outcome than a missed detection.**

This is a decision-support tool for human investigators, not an automated accusation system. Wherever a design choice trades false positives against false negatives, we take the option that flags fewer vessels with better evidence.

The consequences run through the whole module:

- f₄ is corrected three ways (§2.1) rather than used raw, even though the raw version would "detect" more
- Unreliable records are **excluded**, never converted into negative evidence
- A missing factor is **dropped**, never imputed — imputing a value fabricates evidence
- Vessel type is a weight, never a hard filter
- No single factor can independently produce a suspect
- Dark vessels are scored on their own scale, never ranked against AIS-scored vessels

The system's credibility rests on defensible, explainable, low-false-positive reasoning — not on raw detection rate. A system that flags fifty vessels to catch one is not usable by an ICG watchkeeper, and a system that flags the wrong operator once is not trusted again.
