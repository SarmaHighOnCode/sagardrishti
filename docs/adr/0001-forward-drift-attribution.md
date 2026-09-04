# ADR 0001 — Forward drift from every vessel as the primary attribution method

- **Status:** Accepted
- **Date:** 3 September 2026
- **Deciders:** Whole team
- **Significance:** This is the central architectural decision of the project.

## Context

The PS requires us to "trace the slick towards the origin point and time" and to "attribute the spill to a vessel using historic AIS data."

The literal reading suggests: backtrack the slick, find where it started, look for a ship there. Two methods present themselves.

**Method A — backward hindcast, then search.** Seed particles in the observed slick, run the drift model backwards, obtain a probable origin, find vessels near it.

**Method B — forward drift from every candidate vessel.** Assume every vessel might have discharged at every moment along its track; simulate all of it forward to the SAR acquisition time; the vessel whose simulated plume lands on the observed slick is the suspect.

## The problem with Method A

**Backtracking requires knowing the release time, which is exactly what we do not know.**

Run the model back 6 hours and you get one origin region. Run it back 18 hours and you get a completely different one, tens of kilometres away. Backtracking alone produces a *family* of candidate origins indexed by an unknown parameter, with no internal criterion for choosing among them.

Worse, the naive shortcut most teams will take — "find the vessel nearest the slick at acquisition time" — fails on the most common real case. A slick observed six hours after discharge has drifted, while the responsible vessel has travelled 60–100 nautical miles at normal transit speed. The nearest vessel is almost always an innocent bystander.

## Decision

**Method B is the primary attribution engine. Method A is retained as a secondary product.**

```
1. Backward ensemble over T_max → reachability region R   (gate only)
2. Keep vessels whose AIS track intersects R in the window
3. Seed particles along each surviving track at 15-min steps, tagged (vessel, time)
4. ONE OpenDrift run, staggered seed times, ensembled
5. Score plume-vs-slick overlap; the best (vessel, release time) pair wins
```

Full algorithm in [PRD §8.2](../PRD.md).

## Rationale

**It resolves the unknown release time by making it the thing we solve for.** Rather than needing the release time as an input, we search over it. The best-fitting release time *is* the answer, and `T_sar − t*` is the slick age with an uncertainty band from the ensemble spread. This is how we satisfy the PS's "age if feasible" clause without pretending to measure age from pixels.

**It matches the vessel where it was, not where the slick is.** This is the entire failure mode of the naive approach.

**It produces defensible negatives.** Vessels are excluded because their plume could not have reached the slick — a physical argument — rather than because they were far away at an arbitrary instant.

**It is published operational practice.** The forward-drift-from-all-traffic concept underpins Northern European polluter identification (Marine Pollution Bulletin, 2015). We are implementing a validated method, not inventing one.

**Method A is still needed** for three reasons, so we build it too:
- It produces the origin probability field the map displays and the PS explicitly asks for.
- It provides the reachability gate that makes Method B computationally tractable.
- **It is the only option for dark vessels** — with no AIS track, there is nothing to drift forward from.

## Consequences

**Positive**
- Directly answers all three PS clauses, with (b) and (c) solved by one coherent mechanism.
- Gives us the strongest ablation in the evaluation plan: Method B vs naive-nearest-ship. The baseline will perform poorly, which is the point.
- Slick age emerges for free.

**Negative**
- **Computationally expensive.** Naively it is O(vessels × release times × ensemble members × particles).
- **Mitigation, and it is essential:** all particles from all vessels and all release times go into a **single OpenDrift run** with staggered seed times and per-particle origin tags. Particles are independent, so this is exact, not an approximation. It converts thousands of simulations into one. Without this the attribution is too slow to demo live, and the whole approach collapses.
- Still minutes on CPU for a full ensemble, so demo scenarios are pre-computed and cached (PRD §9.1).
- Requires AIS coverage in the window. Where it is absent we fall back to Method A plus dark-vessel detection, with the degradation shown in the UI.

## Verification

The ablation in [`EVALUATION.md`](../EVALUATION.md) — top-1/top-3 accuracy and MRR for Method B versus nearest-ship-at-acquisition, on held-out synthetic scenarios with known culprits — is the empirical justification for this ADR. **If that ablation does not favour Method B substantially, this decision must be revisited.**
