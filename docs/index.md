# SAGARDRISHTI

**Automated oil-spill detection, drift hindcasting, and vessel attribution for Indian waters.**

*From satellite pixel to named vessel — with an error bar on every number.*

SIH 2026 · Problem Statement 26143 · National Technical Research Organisation

---

## Start here

| If you are... | Read |
|---|---|
| New to the project | [PRD](PRD.md), then [Domain Primer](DOMAIN_PRIMER.md) |
| Setting up to develop | [Development](DEVELOPMENT.md) |
| Writing console code | [Frontend Contract](FRONTEND_CONTRACT.md) |
| Building the interface | [Design System](DESIGN_SYSTEM.md) |
| Working on attribution | [Scoring Model](SCORING_MODEL.md) — **in full, before changing anything** |
| Wondering why something is the way it is | [ADRs](adr/README.md) |
| Preparing to present | [Demo Script](DEMO_SCRIPT.md), [Viva Defence](VIVA_DEFENCE.md) |

## The idea in one box

```
Assume EVERY vessel MIGHT have discharged at EVERY moment along its track.
Simulate all of it forward to the SAR acquisition time.
Whoever's simulated plume lands on the observed slick is the suspect —
and the release time that fits IS the slick's age.
```

Naive attribution finds the nearest ship, and fails because a six-hour-old image means the responsible vessel is 80 nautical miles away. [ADR 0001](adr/0001-forward-drift-attribution.md).

## Principles

1. **Rank, never accuse.** Calibrated probabilities with per-factor explanations, not verdicts
2. **Every number has an error bar.** No point estimates for origin. Ever
3. **Explainable over accurate.** An intelligence user must be able to audit the reasoning
4. **Physics gates the ML.** The network proposes; environmental context disposes
5. **Degrade gracefully.** No AIS still yields origin plus dark-vessel candidates
6. **The interface is evidence, not decoration**

## Honest limits

Published before a jury has to find them — see the [PRD](PRD.md) and the root README. The dominant one: our best free currents are ~8 km while a slick is ~40 m. That is a physics limit, quantified with ensembles, not hidden.
