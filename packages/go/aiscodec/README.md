# `aiscodec`

AIVDM/NMEA encode and decode for AIS message types 1, 2, 3, 5, 18, 19 and 24.

## Why this package exists separately

**One implementation, two consumers:** `aisd` decodes real messages with it, `aisgen` encodes synthetic ones with it.

That is what makes the claim in [`DATA_SOURCES.md`](../../../docs/DATA_SOURCES.md) — *"the ingest path is identical for real and synthetic data"* — **structurally true rather than aspirational**. Synthetic messages are encoded by the same code that decodes real ones, so a bug in bit packing shows up in both.

## Message types

| Type | Contents | Used for |
|---|---|---|
| 1, 2, 3 | Class A position report | Position, SOG, COG, heading, nav status |
| 5 | Class A static and voyage | Name, IMO, call sign, type, dimensions, destination |
| 18, 19 | Class B position report | Smaller vessels |
| 24 | Class B static | Name, type, dimensions |

## The round-trip test carries unusual weight

```
encode(msg) -> decode -> compare == msg
```

Property-based, across the full field range of every supported type. This test is the guarantee behind the synthetic-data claim, and it runs on every push.

## Bit-level correctness

AIS packs fields at bit boundaries with six-bit ASCII armouring. Off-by-one errors produce messages that decode to *plausible but wrong* values — a vessel at the wrong position rather than an obvious parse failure.

**Test against real captured messages**, not only synthetic ones. Reference vectors live in `testdata/`.
