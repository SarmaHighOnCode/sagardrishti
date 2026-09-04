# Go Packages

Shared Go libraries for the AIS data plane. See [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md) for why Go is here at all.

| Package | Purpose |
|---|---|
| [`aiscodec`](aiscodec/) | AIVDM/NMEA encode and decode. **One implementation, two consumers** |
| [`geo`](geo/) | Geodesic helpers, distance-to-coast, bounding boxes |

## The boundary

**Go owns the AIS data plane. Python owns the science. The boundary is the database.** No RPC crosses it. Go writes AIS to TimescaleDB; Python reads it.

Any proposal to widen Go's footprint must supersede ADR 0005.
