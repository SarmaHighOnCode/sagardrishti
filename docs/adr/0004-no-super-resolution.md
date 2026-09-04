# ADR 0004 — No super-resolution of SAR imagery

- **Status:** Accepted
- **Date:** 3 September 2026
- **Deciders:** SAR/ML lead, architect

## Context

The YouTube video attached to problem statement 26143 is entirely about **super-resolution (SR)** of satellite imagery. Teams reading the PS will reasonably infer that SR is expected, and several will implement it.

Read the video's own transcript carefully. It states that SR:

- "does not unveil hidden data not present in the original"
- maintains the ground sampling distance
- "primarily delivers aesthetic improvements by generating additional pixels"

The video is a general industry explainer about commercial optical imagery products. It describes SR applied to **optical** data (Pléiades, SPOT, Sentinel-2) for **visual interpretation** tasks. It is not a specification, and nothing in the PS text itself mentions super-resolution.

## Decision

**We do not apply super-resolution to SAR imagery at any point in the detection pipeline.**

We fix ground sample distance at 40 m/px (see [ADR 0002](0002-fixed-ground-sample-distance.md)) and work at native or coarser resolution throughout.

## Rationale

**1. It is scientifically indefensible for this task.** SAR backscatter σ⁰ is a calibrated physical measurement of energy returned from the sea surface. Our entire detection basis is that oil dampens Bragg-resonant waves and lowers σ⁰. An SR network generates plausible-looking pixels learned from a training distribution — it does not measure returned energy. Feeding synthesised σ⁰ into a physics-based discriminator means the model is partly classifying the SR network's priors rather than the sea.

**2. It breaks the chain of custody.** M7 exists to produce evidence that survives challenge. A dossier asserting a vessel is drift-consistent with a slick, where the slick was segmented from partly hallucinated pixels, is not defensible. "Which pixels in this evidence were measured and which were generated?" is a question with no good answer.

**3. It does not help.** Oil slicks are hundreds of metres to kilometres across. At 40 m/px a slick is tens to hundreds of pixels wide — abundant. We deliberately *downsample* from 10 m/px because it cuts inference from minutes to seconds with no loss of relevant signal. Detection is not resolution-limited; it is **look-alike-limited**, and no amount of upsampling distinguishes a biogenic film from mineral oil. That information is in the auxiliary environmental context, which is why Stage C exists.

**4. The cost is real.** An SR model is a training pipeline, a dataset, and an evaluation burden, spent on a component that cannot improve the metric we are judged on.

## Consequences

- We must **proactively** raise this, because a judge who watched the linked video will wonder. It goes in the demo at the honest-limits slide and in [`VIVA_DEFENCE.md`](../VIVA_DEFENCE.md).
- The prepared answer:

  > "Super-resolution is a cosmetic enhancement that does not add information — the video linked to the problem statement says so itself. For a forensic system, introducing generated pixels into evidence would undermine the entire chain of custody. We deliberately did not use it, and we fixed ground sample distance at 40 m/px instead so that training and inference see slicks at identical scale."

- **This answer is worth more than an implementation would be.** It demonstrates that we read the source material critically rather than treating an attached link as a requirement. Teams that implement SR here will struggle to justify it under questioning.

## Narrow exception

SR may be used for **presentation only** — upsampling a thumbnail for a slide — provided it is never fed to a model, never used for measurement, and any such image is watermarked as enhanced. We currently have no plans to do even this.
