# ADR 0002 — Fixed 40 m/px ground sample distance across training and inference

- **Status:** Accepted
- **Date:** 3 September 2026
- **Deciders:** SAR/ML lead

## Context

Public SAR oil-spill datasets were built at **different effective ground resolutions**, and most do not state it prominently:

- Sentinel-1 IW GRDH is nominally 10 m/px pixel spacing (~20 m resolution)
- Some published patch datasets are downsampled to roughly 80 m/px
- ALOS PALSAR material in the SOS dataset has different geometry again
- Some datasets are terrain-corrected, others are in ground range

If a model trains on patches at ~80 m/px and runs inference on tiles at 10 m/px, it sees slicks at roughly **eight times the expected scale**. Learned features — edge sharpness, texture granularity, blob size priors — no longer correspond to anything in the input.

**This fails silently.** Training loss converges normally. Validation metrics on the same-resolution held-out split look fine. Only real-scene performance collapses, and it collapses in a way that looks like a domain-shift problem rather than a preprocessing bug — so teams spend days fine-tuning when the actual fault is a resampling step.

## Decision

**Every training patch and every inference tile is resampled to exactly 40 m/px before it touches a model.** The value is recorded in the model card and asserted at runtime.

Preprocessing (M1) resamples after calibration and before dB conversion. Dataset adapters in `ml/datasets/` resample each source to 40 m/px at load time and refuse to yield a sample they cannot verify.

## Rationale

**Why fix it at all** — the failure above is silent, expensive, and entirely avoidable.

**Why 40 m/px specifically:**

- **Slicks are hundreds of metres to kilometres across.** At 40 m/px a typical slick is tens to hundreds of pixels wide. Ample for segmentation.
- **Compute.** A full IW GRD scene drops from ~420 Mpx to ~26 Mpx — roughly 100–150 tiles at 512². Inference goes from minutes to a few seconds, which is what makes the live demo viable.
- **It is a common denominator.** Every candidate dataset can be resampled *down* to 40 m/px. Upsampling to a finer grid would invent detail (see [ADR 0004](0004-no-super-resolution.md)).
- **Speckle.** Multilooking to a coarser grid genuinely reduces speckle variance, improving the signal we care about.

**Why not finer** — no detection benefit, 16× the compute at 10 m/px, and it would force upsampling of coarser datasets.

**Why not coarser** — below roughly 100 m/px, small discharge trails start to disappear, and thin linear features are precisely the operational-discharge signature we most want.

## Consequences

- Dataset adapters must know each source's true GSD. Where a dataset does not document it, we derive it from the georeferencing and **record the derivation**.
- A runtime assertion in the inference path rejects any tile whose transform does not correspond to 40 m/px. Loud failure beats silent degradation.
- Model cards state GSD explicitly. Comparisons against published numbers carry a note where the source used a different GSD.
- Changing this value invalidates every trained checkpoint. It is a breaking change requiring a new ADR.

## Note for the viva

Raise this unprompted. *"We fixed ground sample distance at 40 m/px across every dataset and the inference path, because the public datasets are built at different resolutions and mixing them fails silently — the loss curve looks healthy while field performance collapses."*

It is a small, specific, unglamorous decision that demonstrates real familiarity with the data. Most teams will not have considered it.
