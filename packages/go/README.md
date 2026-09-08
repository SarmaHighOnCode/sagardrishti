# Go Packages

Shared Go libraries for the AIS data plane. See [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md) for why Go is here at all.

| Package | Purpose |
|---|---|
| [`store`](store/) | Batched COPY + `ON CONFLICT DO NOTHING` upsert into `ais_positions`/`ais_static`. Promoted out of `services/aisd/internal/store` (5 Sept 2026) so `services/aisgen` writes through the exact same code `aisd` does. **Live-verified against a real Postgres 8 Sept 2026** via `aisgen` — that run caught a real bug (staging table missing `recorded_at`'s default, fixed with `INCLUDING DEFAULTS`), now guarded by `store_integration_test.go` |
| [`aoi`](aoi/) | Area-of-interest bounding boxes and point classification. Promoted alongside `store` so both binaries tag rows using identical box definitions |
| [`quality`](quality/) | Data-quality pre-filter (`ok`/`unreliable`) applied to every position/static row. Promoted alongside `store` |
| [`geo`](geo/) | Haversine distance, initial bearing, linear interpolation — the geodesic primitives `aisgen`'s lane-following logic needs. Was an empty placeholder until `aisgen` needed it |

**Why promoted rather than left in `services/aisd/internal`:** Go's `internal/` visibility rule means only code rooted at `services/aisd/...` can import an `internal` package — `services/aisgen`, with its own `go.mod`, could not, even though both are "the AIS data plane" per ADR 0005. Each module depends on this one via a `replace` directive (`replace github.com/sagardrishti/go => ../../packages/go`) rather than a `go.work` workspace — simpler, and it works identically regardless of which directory a CI job happens to run `go test` from.

> **This directory used to list an `aiscodec` package** (AIVDM/NMEA encode and decode, shared between `aisd` and `aisgen`). It was removed 5 September 2026: the plan assumed AISStream sends raw AIVDM, which is wrong — AISStream sends pre-decoded JSON (`services/aisd/internal/aisstream`), so there was never anything for a codec to decode. The corresponding guarantee — that synthetic and real AIS share an ingest path — is implemented by `aisgen` calling `store.WritePositions`/`WriteStatic` directly, so both binaries write through identical code. See [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md) and [`services/aisgen/README.md`](../../services/aisgen/README.md).

## The boundary

**Go owns the AIS data plane. Python owns the science. The boundary is the database.** No RPC crosses it. Go writes AIS to TimescaleDB; Python reads it.

Any proposal to widen Go's footprint must supersede ADR 0005.
