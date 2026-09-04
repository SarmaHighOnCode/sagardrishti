# Architecture Decision Records

Each ADR records one significant decision: the context that forced it, the alternatives, what we chose, and what it costs us.

**Why we keep these.** Two reasons. First, in a six-person team over four months, the reasoning behind a decision evaporates faster than the decision itself, and someone will eventually propose undoing something for reasons that were already considered and rejected. Second, an SIH jury's most valuable question is *"why did you do it that way?"* — these documents are the prepared answer, written while the reasoning was fresh.

## Index

| # | Decision | Status | Why it matters |
|---|---|---|---|
| [0001](0001-forward-drift-attribution.md) | Forward drift from every vessel as the primary attribution method | Accepted | **The central architectural decision of the project.** Resolves the unknown release time by solving for it, and yields slick age as a by-product |
| [0002](0002-fixed-ground-sample-distance.md) | Fixed 40 m/px ground sample distance across training and inference | Accepted | Prevents a silent failure mode that most teams will hit and misdiagnose as domain shift |
| [0003](0003-transparent-log-odds-scoring.md) | Transparent log-odds scoring instead of a learned attribution model | Accepted | Interpretability is a requirement for an intelligence user, and we lack the labelled data to justify anything larger |
| [0004](0004-no-super-resolution.md) | No super-resolution of SAR imagery | Accepted | The PS's linked video is about SR. Declining it deliberately, with reasons, is stronger than implementing it |
| [0005](0005-go-for-the-ais-data-plane.md) | Go for the AIS data plane, Python for the science | Accepted | The AIS recorder is a three-month, data-loss-critical daemon against a feed with no replay. Different problem, different tool |

## Planned

| # | Decision | Status |
|---|---|---|
| 0006 | Blueprint tokens over a bespoke design language | Proposed — reasoning currently lives in [`DESIGN_SYSTEM.md`](../DESIGN_SYSTEM.md) §1 |
| 0007 | Synthetic AIS as a primary deliverable, not a fallback | Proposed |
| 0008 | TimescaleDB hypertables for AIS storage | Proposed |
| 0009 | Evidence dossier provenance and signing scheme | Proposed |

## Format

Keep them short. Context, Decision, Rationale, Consequences — with the negative consequences stated as plainly as the positive ones. An ADR that lists only benefits is marketing, not engineering.

Number sequentially. Never edit an accepted ADR's decision; supersede it with a new one and mark the old `Superseded by NNNN`.
