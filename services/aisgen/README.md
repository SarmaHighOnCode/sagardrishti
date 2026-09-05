# `aisgen` — Synthetic AIS Generator (Go)

Generates physically plausible AIS traffic with labelled ground-truth discharge events.

## This is a deliverable, not a fallback

The problem statement explicitly permits synthetic AIS. Bulk historical AIS for Indian waters is not publicly available — free sources are live-only and terrestrial-only, commercial providers consolidated further through 2026.

**It is also our only source of attribution ground truth**, and therefore the only way to compute attribution accuracy at all. Built properly it is a contribution in its own right.

## Requirements

| # | Requirement | Why |
|---|---|---|
| 1 | Lane geometry from recorded AISStream data — KDE of positions to centrelines and widths | Grounded in real Indian traffic, not invented |
| 2 | Vessel types from realistic Indian-waters distributions | Tanker / container / bulker / fishing / tug |
| 3 | Per-type SOG distributions, COG jitter, correct reporting intervals | Class A: 2–10 s underway, 3 min at anchor, decimated for receiver gaps |
| 4 | **Written through `aisd`'s own `internal/store` batched-upsert path** | The same code that writes real messages — see below |
| 5 | **Labelled discharge events** — vessel, time, location, rate | The ground truth. Without this, attribution accuracy is unmeasurable |
| 6 | Realistic confounders | AIS gaps, MMSI spoofing and duplication, position jumps, innocent vessels near the slick |

## Requirement 4 is the important one

> **Corrected 5 Sept 2026.** This requirement originally called for "valid bit-level encoding via a shared `aiscodec` package" — the assumption being that AISStream sends raw AIVDM/NMEA, decoded by `aisd` and re-encoded by `aisgen` through the same codec. That assumption was wrong: **AISStream sends pre-decoded JSON.** There is no AIVDM on this wire, so there was never anything for a codec to decode or encode. See [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md) for the full correction.

The guarantee is implemented one layer downstream of where it was originally planned: `aisgen` must import and call `aisd`'s `internal/store` package directly (promoted to a location both binaries can import) rather than writing its own INSERT logic. Synthetic rows land in `ais_positions` through **the exact same batched-upsert code** that real messages go through.

That is what makes *"the ingest path is identical for real and synthetic data"* structurally true rather than a claim we make on a slide — sameness of the database row, not sameness of a wire decoder. A test asserting `aisd` and `aisgen` produce byte-identical rows for equivalent input is the guarantee behind it, and it must exist before this claim is repeated anywhere else (a slide, the evidence dossier, a viva answer).

## Requirement 6 deserves care

The confounders are what make the evaluation honest. A generator producing clean, well-behaved traffic would let the attribution model look far better than it is.

**Include the innocent-but-suspicious cases specifically:** a vessel with a genuinely flaky transponder, a vessel legitimately out of coverage, a vessel that passes near the slick at the right time but could not have caused it. If the model ranks these highly, that is a real finding — and better discovered here than by a jury.

## Honest framing

Every synthetic result is labelled `SYNTHETIC` — on charts, in tables, in the dossier, on slides. Every time.

> "We validate the attribution engine against real AIS on the NOAA US dataset, where independent tracks exist. We demonstrate on Indian waters using a generator calibrated to lane geometry we recorded live from AISStream, because bulk historical Indian AIS is not publicly available — which is itself part of the capability gap this problem statement exists to close."
