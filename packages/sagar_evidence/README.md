# `sagar_evidence` — M7

Provenance assembly and the signed evidence dossier. **Owner: Integration lead.**

## Why this exists

An ICG or NTRO analyst must be able to justify boarding, inspecting and sampling a vessel. That requires showing **where every number came from**.

This is not hypothetical. Kerala High Court proceedings against the owners of MSC ELSA 3 and Wan Hai 503 are exactly the context where a defensible evidence record has value.

## Provenance is captured, not reconstructed

**M7 cannot rebuild lineage after the fact.** Every module emits a `ProvenanceRecord` into the job context **as it runs** — input hashes, versions, parameters, timestamps. M7 assembles them.

A module that does not emit provenance produces output that cannot go in a dossier, and CI treats that as a failure.

## Dossier contents

| Section | Contents |
|---|---|
| Summary | Slick location, time, area, confidence |
| Detection | Polygon, attributes, **every applied penalty with its reason** |
| Origin | Probability field, inferred release window with uncertainty |
| Traffic | The full filter cascade with per-vessel drop reasons |
| Suspects | Ranked, with **all** factor contributions including exculpatory ones |
| Forecast | Predicted extent, shoreline impact |
| **Provenance** | The page that makes it defensible — see below |
| Limitations | Stated in the document, not omitted |

## The provenance page

```
SOURCE     S1C_IW_GRDH_1SDV_20260525T064012_...
           sha256  a3f9c2e1...
           CDSE product ID, access timestamp
MODEL      segformer-b2-oil v1.2  weights sha256  7d41b8a9...
           GSD 40 m/px, normalisation: median +/- 3 sigma clip
FORCING    CMEMS GLOBAL_ANALYSISFORECAST_PHY_001_024  v202411
           ERA5 reanalysis, GEBCO 2024
AIS        source: synthetic (aisgen v0.4, seed 42)  [or: AISStream recorded]
CONFIG     full snapshot, sha256  c8e2f114...
GENERATED  2026-05-25T14:22:07Z  by sagardrishti v0.9.1
```

## Rules

- **Synthetic data is labelled `SYNTHETIC` on every page.** Not a footnote
- **Limitations are inside the document.** A dossier that omits its own error budget is not evidence
- **Exculpatory factors are included.** Hiding them would destroy the defensibility claim that justifies this module existing
- **Never the word "guilty."** The dossier presents a ranked candidate with calibrated probability

## Signing

A hash chain over the manifest, signed with a project key, embedded in the PDF.

**Not blockchain.** A signed hash chain does the same job without the eye-roll — and a jury that hears "blockchain" for a document-integrity problem will draw conclusions.

## LLM use — narrowly scoped

An LLM may generate the **narrative summary paragraph** from structured outputs. Nothing else. It never touches a number, a probability, or a provenance field, and the generated text is marked as such. This is the one defensible use in the system.
