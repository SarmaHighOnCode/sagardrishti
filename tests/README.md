# `tests`

Cross-package integration and contract tests. Unit tests live beside the code they test.

| Level | Scope | Runs |
|---|---|---|
| Unit | Pure functions — geometry, scoring, codec, formatters | Every push |
| **Contract** | Pydantic schemas at every module boundary | Every push |
| Golden-file | M1 output on a fixture scene, byte-comparable | Every push |
| Integration | Full pipeline on a small cached scene | Every PR |
| Go | `aiscodec` round-trip | Every push |
| Smoke | `docker compose up`, hit every endpoint | Nightly + pre-demo |

## Tests that carry unusual weight

**`aiscodec` round-trip.** `encode -> decode -> compare`, property-based across the full field range. This is what makes *"synthetic and real AIS share an ingest path"* verifiable rather than aspirational. [`DATA_SOURCES.md`](../docs/DATA_SOURCES.md) section 3.2 depends on it.

**AIS data quality filter.** Must exclude, with a test each: MMSI 0, position stuck at (0,0), kinematically impossible implied speed, garbled static data. And critically — **an excluded record must not shift a suspicion score in either direction.** A vessel must never become a suspect because its transponder is broken. [`SCORING_MODEL.md`](../docs/SCORING_MODEL.md) section 2.1.

**GSD assertion.** Any tile whose transform is not 40 m/px must raise. Loud failure beats silent degradation. [ADR 0002](../docs/adr/0002-fixed-ground-sample-distance.md).

**Uncertainty schema.** An inferred value without its interval must fail validation. Product principle 2, enforced structurally.

## Fixtures

Small, committed, real where possible. A 512x512 SAR crop, a handful of AIS messages including deliberately malformed ones, a tiny forcing NetCDF.

**Fixtures must be small enough to commit.** A test suite depending on gigabytes of external data is a test suite that stops being run.
