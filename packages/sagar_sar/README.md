# `sagar_sar` — M1 to M4

SAR preprocessing, detection, characterisation and ship detection. **Owner: SAR/ML lead.**

## Submodules

| Submodule | Module | Purpose |
|---|---|---|
| `preprocess` | M1 | Calibration, fixed 40 m/px resample, land mask, tiling, COG |
| `detect` | M2 | Three-stage detection |
| `characterise` | M3 | Geometry, damping ratio, edge sharpness, thickness class |
| `ships` | M4 | CFAR point targets, wake heading, AIS cross-match, dark vessels |

## M1 — the one line that matters

```
GRD -> orbit -> border noise -> thermal noise -> calibrate sigma-0
    -> resample to FIXED 40 m/px      <-- this line
    -> dB -> land mask -> normalise -> tile 512 with 64 overlap -> COG + STAC
```

Public datasets are built at **different** ground resolutions. Train at 80 m/px, infer at 10 m/px, and the model sees slicks at the wrong scale and fails **silently** — healthy loss curve, collapsed field performance, misdiagnosed as domain shift.

A runtime assertion rejects any tile whose transform is not 40 m/px. [ADR 0002](../../docs/adr/0002-fixed-ground-sample-distance.md).

## M2 — three stages

```
A  dark-formation proposals     cheap, high recall, low precision
B  semantic segmentation        SegFormer-B2 primary, DeepLabv3+ baseline
C  physics and context filter   the differentiator
```

**Stage C is why this project is not a baseline.** A pure pixel classifier cannot separate oil from a low-wind area, because the information is not in the pixels. Stage C scores every detection against wind (the 2–12 m/s window), chlorophyll, SST, bathymetry, precipitation, edge sharpness, and our own archive of recurring dark formations at that location.

**Every penalty is logged with a human-readable reason** and surfaced in the UI. That is the 1:50 demo beat and the single cheapest credibility win available.

**Loss:** Focal + Dice, plus a **boundary-gradient term** — 2025–26 work identifies edge prominence as a primary oil-vs-look-alike discriminator.

**Augmentation:** flips, 90-degree rotations, multiplicative speckle, sigma-0 level shift (±2 dB), incidence-angle gradient. **Never colour jitter or elastic deformation** — physically meaningless for SAR.

## M4 — dark vessels, carefully

Unmatched SAR detection means a dark vessel. But a coarse **size bucket** (`small`/`medium`/`large`) from radar cross-section is attached, because **many small craft are legally exempt from carrying AIS**. A fishing boat below the carriage threshold is not an evader.

Without this the dark-vessel list fills with legitimate small traffic and stops being useful. The bucket is analyst context and a soft flag — **it never hard-filters a detection out**. We claim a size bucket, never a vessel type; we have no training data for the latter.

## Targets

| Metric | Target |
|---|---|
| mIoU | 70–78% |
| Oil IoU | 60–70% |
| FPR on no-oil | < 15%, reported per look-alike cluster |
| **Cross-domain drop** | **Expect 10–20 points. Report it** |
| Ship detection P/R | > 0.85 for vessels > 50 m |
