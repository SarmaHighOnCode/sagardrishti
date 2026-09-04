# ADR 0003 — Transparent log-odds scoring instead of a learned attribution model

- **Status:** Accepted
- **Date:** 3 September 2026
- **Deciders:** AIS/attribution lead, architect

## Context

M6 must combine roughly nine heterogeneous signals — drift consistency, course alignment, speed anomaly, AIS gaps, course changes, time of day, off-lane distance, vessel type prior, contextual proximity — into a single ranked suspect list.

The instinctive 2026 approach is a small neural network, or gradient boosting, trained end-to-end on labelled attribution events.

Two facts make that wrong here.

**1. We will have on the order of tens of labelled events.** Attribution ground truth requires knowing who actually discharged. That exists only in our synthetic scenarios plus a small number of real cases (MSC ELSA 3). Tens of examples cannot reliably fit ten parameters, let alone a network. We would be fitting noise and reporting the fit as accuracy.

**2. The user is an intelligence analyst who must justify a decision.** NTRO does not need a number; they need a number *with a reason*, sufficient to justify boarding, inspection and sampling. A model that outputs 0.71 with no decomposable explanation cannot support that, regardless of accuracy.

## Decision

**Combine evidence additively in log-odds space, with hand-initialised weights, refined by logistic regression and calibrated for probability.**

```
logit(P_suspect) = w0 + Σ wi · fi
```

Four-step process:

1. **Hand-set initial weights**, each with a written justification in [`SCORING_MODEL.md`](../SCORING_MODEL.md).
2. **Fit logistic regression** on synthetic labelled events to refine — same functional form, so weights stay interpretable and can be compared against the hand-set priors.
3. **Calibrate** with Platt scaling or isotonic regression, so 0.7 means roughly "right 70% of the time."
4. **Render per-factor contribution bars** in the UI for every suspect.

## Rationale

**Log-odds is the right space.** Each factor contributes additively to the log-odds, so `wi · fi` is directly the evidence that factor contributes, in a unit that is meaningfully comparable across factors. That is what makes the UI's per-factor bars honest rather than a post-hoc rationalisation — they are the actual terms of the computation, not a SHAP approximation of an opaque model.

**Interpretability is a requirement, not a trade-off.** Product principle 3: an intelligence user must be able to audit the reasoning. Here the model *is* the explanation.

**It degrades gracefully.** Missing a factor (no chlorophyll data, no vessel type) means dropping a term, not failing to run. A neural network with a missing input needs imputation, which quietly fabricates evidence.

**Logistic regression is the correct amount of learning for the data we have.** Ten parameters, tens of examples, strong priors from hand-set weights. Anything larger overfits.

**Calibration is what makes ranking meaningful.** Uncalibrated scores are ordinal only. We claim calibrated probabilities, so we must actually calibrate and report a reliability diagram.

## Consequences

**Positive**
- Every score is decomposable and auditable, including exculpatory factors.
- Weights are directly criticisable — a domain expert can look at `w4 = 1.3` for AIS gaps and argue it is too high. That is a feature.
- The evidence dossier can state the arithmetic in full.
- No risk of a spurious "97% accurate" claim from an overfitted model.

**Negative**
- Cannot capture interactions between factors unless we add explicit interaction terms. Accepted: with our data volume we could not fit them reliably anyway.
- Hand-set weights are subjective. Mitigated by writing the justification down, then refining empirically, and reporting both the prior and fitted values.
- A jury may ask "why not deep learning?" — the answer below is a strength.

## Defending it

> "We have tens of labelled attribution events, because attribution ground truth requires knowing who actually discharged. Ten weights fitted on tens of examples is at the limit of what is statistically honest, and a network would simply overfit and report the overfit as accuracy. More importantly, our user has to justify a boarding decision. A log-odds model is the explanation — the bars in the interface are the actual terms of the computation, not a post-hoc attribution method approximating a black box. We use deep learning where we have thousands of labelled examples, which is the segmentation stage."

That last sentence matters: it shows the choice is considered per-component, not an aversion to ML.
