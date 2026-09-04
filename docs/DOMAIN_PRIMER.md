# Domain Primer

The physics you must understand to defend this project. **NTRO juries include remote-sensing specialists.** If the presenter cannot explain why oil is dark in SAR, no F1 score will save the pitch.

Read this before writing code. Every team member, not just the SAR lead.

---

## 1. Why oil is visible in SAR at all

SAR measures **backscatter**, written σ⁰ (sigma nought) — the fraction of transmitted microwave energy returned to the antenna.

Over the open sea the dominant mechanism is **Bragg scattering**. The radar's pulses resonate with capillary and short gravity waves whose wavelength is comparable to the radar wavelength, when those waves travel along the range direction. Sentinel-1 is **C-band, ~5.6 cm**, so it resonates with centimetre-scale ripples.

**Wind creates those ripples.** No wind, no Bragg scatterers, no signal.

Oil films lower the surface tension of water and **dampen the gravity–capillary waves** — this is Marangoni damping. Fewer Bragg scatterers means less energy returned, which means a **dark patch**.

> That is the entire physical basis of the field. Oil is not "seen." Its *absence of roughness* is seen.

**The one-sentence viva answer:** *Bragg scattering — C-band resonates with wind-generated capillary waves; oil dampens surface tension and suppresses those waves, so backscatter drops.*

---

## 2. The wind window — the most important operational constraint

Oil detection in SAR works only inside a band of wind speeds.

```
   0        2–3 m/s                          7–12 m/s              20 m/s
   |──────────|═══════════════════════════════|──────────────────────|
   TOO CALM   │        DETECTION WINDOW       │      TOO ROUGH
              │                               │
  sea is glassy;                        waves overwhelm damping;
  backscatter near                      slick breaks up and mixes
  noise floor;                          downward; signature gone
  EVERYTHING looks
  like oil
```

**Below ~2–3 m/s:** the sea surface is already smooth, σ⁰ approaches the instrument noise floor, and a slick has nothing to contrast against. False positives explode.

**Above ~7–12 m/s:** wave energy overwhelms the damping, and the slick is physically broken up and mixed into the water column. True negatives — the oil is there, we cannot see it.

Exact bounds vary with oil type, slick age and sensor.

**Design consequence, and it is cheap to implement:** ingest modelled wind speed alongside every scene and **use it as a gate**. Any detection made outside the window is automatically down-weighted and flagged with the reason. This single feature puts us ahead of most teams and directly produces the best moment in the demo — see [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md), 1:30.

---

## 3. Look-alikes — the actual unsolved problem

Detecting a dark patch is easy. **Deciding whether a dark patch is mineral oil is the hard part**, and it is not solved in the literature.

| Look-alike | How it appears | Discriminating context |
|---|---|---|
| **Low wind / wind shadow** | Large, diffuse, no sharp edge | Correlates with modelled low wind; often in the lee of coast or islands |
| **Biogenic films** (surfactants, algae, plankton) | Accumulate along convergence lines | Elevated chlorophyll-a; damping generally weaker than mineral oil; **softer boundary** |
| **Oceanic internal waves** | Regular alternating bright/dark bands | Near shelf edges and steep bathymetry; suppressed above ~10 m/s wind |
| **Atmospheric gravity waves** | Also banded, but much larger area | Visible at all wind speeds; roughly perpendicular to wind |
| **Upwelling / mixing zones** | Diffuse dark region | Cold SST anomaly + elevated chlorophyll; **recurs in the same places** |
| **Rain cells** | Bright elliptical downdraft with adjacent damping | Correlates with precipitation data |
| **Meso/submesoscale eddies** | Spiral shear lines | Visible in sea-surface-height anomaly |
| **Land breeze / katabatic winds** | Coast-parallel or fan-shaped | Recur at the same coastal locations; mostly early-morning descending passes |
| **Ship and turbine wakes** | Thin linear feature attached to a bright point target | The bright target is the giveaway |
| **RFI** | Bright linear artefacts | Largely mitigated in Sentinel-1 products since March 2022, not entirely |

### 3.1 The consequence that shapes our architecture

**A pure pixel classifier cannot solve this**, because the discriminating information is not in the pixels. A low-wind zone and a thin oil sheen can be genuinely indistinguishable in σ⁰ alone.

The information is in the **auxiliary context**: wind field, SST, chlorophyll, bathymetry, precipitation, distance to coast, recurrence at that location, and proximity to a plausible source.

This is why detection is three stages, and why Stage C exists at all:

```
Stage A   dark-formation proposals     cheap, high recall
Stage B   semantic segmentation        the CNN — proposes
Stage C   physics + context filter     the environment — disposes
```

**"CNN proposes, physics disposes"** is the design in five words. Use it in the pitch.

### 3.2 Edge prominence

2025–26 literature converges on a useful finding: **mineral oil slicks have sharper boundaries** than biogenic films or wind-shadow areas. Damping by a mineral film transitions abruptly at the film's edge; wind and biological effects grade.

We exploit this twice, cheaply:
- a **boundary-gradient term** in the segmentation loss (§7.3 of the PRD)
- an explicit **edge-sharpness feature** in the Stage C filter

---

## 4. Polarisation

Sentinel-1 IW over most seas gives **VV + VH dual-pol**.

| Channel | Behaviour | Use |
|---|---|---|
| **VV** (co-pol) | Much higher backscatter over water; strong Bragg response | The workhorse. Nearly all oil detection is VV |
| **VH** (cross-pol) | Sits close to the instrument noise floor over calm water | Noisy and weak — but the fact that VH is *nearly noise-limited inside a slick* is itself a weak discriminator |

**Practical guidance:** feed both channels to the model. Do not expect VH to carry much. Do not discard it — it costs one input channel and occasionally helps.

---

## 5. Slick age — why it cannot be measured, and what we do instead

### 5.1 What actually happens to oil

| Process | Timescale | Effect on SAR signature |
|---|---|---|
| Evaporation of light fractions | Hours | Film thins, damping weakens |
| Emulsification (mousse formation) | Hours to days | Changes viscosity and damping behaviour |
| Natural dispersion | Continuous, wind-driven | Removes oil from the surface |
| Spreading | Continuous | Area grows, thickness falls |

So a weathered film damps less and shows lower contrast. **Contrast correlates with age.**

### 5.2 Why that does not give you age

The correlation is confounded by variables we do not know:

- **wind speed** — changes damping independently of age
- **incidence angle** — changes σ⁰ across the swath
- **oil type** — a heavy fuel oil and a light diesel age completely differently
- **discharge volume and rate** — sets initial thickness

Four unknowns, one observable. **Fitting age to contrast from a single scene is fitting noise.** Anyone claiming otherwise is overfitting or misreading their own validation.

### 5.3 The reframing — and it is a strength

> **Age is not measured from the image. Age is *inferred* as the release time that makes the observed slick geometry consistent with the drift field.**

In the attribution solve ([ADR 0001](adr/0001-forward-drift-attribution.md)), we search over release time. The release time `t*` that best explains the observed slick, given a candidate vessel's track and the drift field, *is* the age estimate:

```
slick age = T_sar − t*        with an uncertainty band from the ensemble spread
```

This is how operational European polluter-identification works. It converts the PS's cautious "age if feasible" into a designed output with a stated uncertainty — a much stronger answer than either claiming a pixel-based age or admitting we cannot do it.

---

## 6. Drift physics

An oil particle at the sea surface moves under three forcings:

```
u_total  =  u_current  +  α · u_wind  +  u_stokes
```

| Term | Typical magnitude | Source | Uncertainty |
|---|---|---|---|
| **Ocean current** | 0.1 – 1.5 m/s | CMEMS 1/12° model | **The dominant error term** — see §6.1 |
| **Wind drift** | α ≈ 0.02–0.04 × wind speed | ERA5 / CMEMS wind | α is genuinely uncertain across that whole range |
| **Stokes drift** | 0.5 – 5 cm/s | CMEMS wave model | Often neglected; it should not be |

The wind drift factor α is a real physical range, not a tuning parameter. **We sample it across [0.02, 0.04] in the ensemble** rather than picking a value, because picking one would fabricate precision.

### 6.1 The resolution problem — our dominant error term

```
   slick, as SAR sees it        ~40 m
   sub-mesoscale eddies         100 m – 10 km    ← controls slick shape
   best free current product    ~8 km (1/12°)    ← cannot see any of it
```

**We are advecting a metre-scale feature with a velocity field that cannot resolve anything smaller than a city.** The eddies that visibly shape real slicks are entirely absent from the forcing.

This is a **physics and data-availability limit, not an engineering failure.** It is why:

- we run 100+ member ensembles with perturbed forcing and stochastic diffusion
- we output probability fields and never point estimates
- the backward cone widens with time, visibly, in the interface
- ingesting INCOIS's higher-resolution regional currents is our stated first operational upgrade

**Say this out loud in the demo before a judge asks.** Volunteering the dominant limitation is the highest-credibility move available.

### 6.2 Why weathering is disabled in backward runs

Evaporation and emulsification are **irreversible**. Running them backwards is physically meaningless — you would be un-evaporating oil.

- **Backward runs:** advection only, weathering **off**
- **Forward runs:** advection plus full weathering (evaporation, emulsification, vertical mixing, film thickness)

Getting this wrong is a subtle bug that produces plausible-looking, entirely invalid output. It is also a good question to be ready for.

---

## 7. Sentinel-1, correctly

| Property | Value |
|---|---|
| Band | C-band, ~5.6 cm |
| Mode over sea | IW (Interferometric Wide swath), 250 km swath |
| Product | GRDH — ground range, detected, high resolution |
| Pixel spacing | 10 m (GRDH); we resample to **40 m/px** — [ADR 0002](adr/0002-fixed-ground-sample-distance.md) |
| Polarisation | VV + VH over most seas |
| **Constellation, Sept 2026** | **Sentinel-1C + Sentinel-1D.** Sentinel-1A operations terminated **29 June 2026** |
| Repeat | 6 days between C and D; **1–3 days effective over the Indian EEZ** combining ascending and descending passes |

> Teams quoting "Sentinel-1A/1B, 6-day repeat" are quoting 2021. Getting the current constellation right is a small, free credibility win.

---

## 8. Terms worth knowing

| Term | Meaning |
|---|---|
| **σ⁰ (sigma nought)** | Normalised radar cross-section — calibrated backscatter |
| **Bragg scattering** | Resonant scattering from waves matching the radar wavelength |
| **Marangoni damping** | Surface-tension-gradient damping of capillary waves by a film |
| **Speckle** | Multiplicative interference noise inherent to coherent imaging |
| **Multilooking** | Averaging independent looks to reduce speckle, at the cost of resolution |
| **Incidence angle** | Angle between radar beam and surface normal; σ⁰ varies strongly across the swath |
| **GRD** | Ground Range Detected — amplitude only, phase discarded |
| **Damping ratio** | σ⁰ background ÷ σ⁰ slick, in dB. Our mineral-oil indicator |
| **Look-alike** | Any non-oil dark feature (§3) |
| **Lagrangian** | Following individual particles rather than a fixed grid |
| **Stokes drift** | Net transport from wave orbital motion |
| **Hindcast** | Backward-in-time reconstruction |
| **CFAR** | Constant False Alarm Rate — adaptive threshold detector for point targets |
| **AIVDM** | The NMEA sentence format carrying AIS messages |
| **MMSI** | Maritime Mobile Service Identity — 9-digit vessel radio identifier |
| **SOG / COG** | Speed / Course Over Ground |
| **Dark vessel** | A vessel detected by sensor with no corresponding AIS broadcast |
| **EEZ** | Exclusive Economic Zone — 200 nm |
| **NOSDCP** | National Oil Spill Disaster Contingency Plan (India); ICG coordinates |
| **MARPOL Annex I** | The IMO convention making operational oil discharge illegal |

---

## 9. Further reading, in priority order

1. **Yang, Singha, Goldman & Schütte (2025)**, ESSD 17, 6807–6837 — **read Section 4 in full.** The best available guide to interpreting SAR look-alikes, with a clustered dataset to match
2. **Brekke & Solberg (2005)**, *Oil spill detection by satellite remote sensing* — the foundational survey
3. **Dagestad et al. (2018)**, *OpenDrift v1.0*, GMD 11, 1405–1420 — the drift engine
4. **Röhrs et al. (2018)**, Ocean Sci. 14, 1581–1601 — OpenOil and vertical mixing
5. **Marine Pollution Bulletin (2015)**, `10.1016/j.marpolbul.2015.08.036` — forward-drift polluter identification; the method behind our attribution engine
6. **Prasad et al. (2018)**, J. Earth Syst. Sci. — Ennore spill trajectory, the Indian validation case
