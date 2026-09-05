# Go Packages

Shared Go libraries for the AIS data plane. See [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md) for why Go is here at all.

| Package | Purpose |
|---|---|
| [`geo`](geo/) | Geodesic helpers, distance-to-coast, bounding boxes |

> **This directory used to list an `aiscodec` package** (AIVDM/NMEA encode and decode, shared between `aisd` and `aisgen`). It was removed 5 September 2026: the plan assumed AISStream sends raw AIVDM, which is wrong — AISStream sends pre-decoded JSON (`services/aisd/internal/aisstream`), so there was never anything for a codec to decode. The corresponding guarantee — that synthetic and real AIS share an ingest path — is now implemented by `aisgen` calling `aisd`'s `internal/store` batched-upsert package directly, so both binaries write through identical code. See [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md) and [`services/aisgen/README.md`](../../services/aisgen/README.md).

## The boundary

**Go owns the AIS data plane. Python owns the science. The boundary is the database.** No RPC crosses it. Go writes AIS to TimescaleDB; Python reads it.

Any proposal to widen Go's footprint must supersede ADR 0005.
