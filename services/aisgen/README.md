# `aisgen` — Synthetic AIS Generator (Go)

Generates physically plausible AIS traffic with labelled ground-truth discharge events.

## Status: built and live-verified against a real Postgres (8 September 2026)

```bash
cd services/aisgen
go build ./... && go vet ./... && go test ./...   # 32 tests, all pure-function

# Dry-run — no DATABASE_URL needed. Writes JSONL instead of Postgres.
SAGAR_AISGEN_VESSELS=25 SAGAR_AISGEN_DURATION_HOURS=6 SAGAR_AISGEN_SEED=1 \
  SAGAR_AISGEN_OUT_DIR=./out go run ./cmd/aisgen
# → ./out/positions.jsonl, ./out/statics.jsonl, ./out/aisgen_ground_truth.json

# Against a real database, the way the team should actually run this:
docker compose --profile aisgen run --rm aisgen
```

A run like the dry-run above produced 5,204 position rows, 178 static rows and 13 ground-truth events (including all three confounder types below and one discharger) in well under a second.

**The `docker compose` form is live-verified**, not aspirational: it wrote 33,094 position rows and 1,037 static rows across 46 vessels into the real `sagardrishti` database, confirmed by query, then the table was truncated back to empty (same "prove it, then leave it clean" convention as `docs/HANDOVER.md` task A). That first live run found and fixed a real bug in `packages/go/store` — see task G for the full story, including the regression test now guarding it (`packages/go/store/store_integration_test.go`).

See `docs/HANDOVER.md` task G for the full state — what's genuinely done, and the one thing that's still an explicit placeholder (hand-specified lane geometry instead of KDE-fitted, since `aisd` has never recorded real traffic to fit against).

## This is a deliverable, not a fallback

The problem statement explicitly permits synthetic AIS. Bulk historical AIS for Indian waters is not publicly available — free sources are live-only and terrestrial-only, commercial providers consolidated further through 2026.

**It is also our only source of attribution ground truth**, and therefore the only way to compute attribution accuracy at all. Built properly it is a contribution in its own right.

## Requirements

| # | Requirement | Why | Status |
|---|---|---|---|
| 1 | Lane geometry from recorded AISStream data — KDE of positions to centrelines and widths | Grounded in real Indian traffic, not invented | ⚠️ **Placeholder.** `internal/lanes` uses hand-specified centrelines from public knowledge of Indian shipping corridors — `aisd` has never recorded a row to fit a KDE against. See that package's doc comment |
| 2 | Vessel types from realistic Indian-waters distributions | Tanker / container / bulker / fishing / tug | ✅ `internal/fleet` — weighted distribution, per-type speed/length/beam ranges |
| 3 | Per-type SOG distributions, COG jitter, correct reporting intervals | Class A: 2–10 s underway, 3 min at anchor, decimated for receiver gaps | ✅/⚠️ SOG jitter and COG jitter are real (`internal/simulate`); the reporting interval is a configurable demo-scale constant (`SAGAR_AISGEN_REPORT_INTERVAL_SECONDS`, default 120s), not real Class A cadence — see the honest note in `simulate.Config.ReportInterval`'s doc comment for why |
| 4 | **Written through `aisd`'s own `internal/store` batched-upsert path** | The same code that writes real messages — see below | ✅ Done — see below |
| 5 | **Labelled discharge events** — vessel, time, location, rate | The ground truth. Without this, attribution accuracy is unmeasurable | ✅ `internal/groundtruth` |
| 6 | Realistic confounders | AIS gaps, MMSI spoofing and duplication, position jumps, innocent vessels near the slick | ✅ `internal/confounders` (gaps, jumps, MMSI duplication) + `internal/simulate`'s proximity scan for the innocent-near-slick case (fires in roughly 1 of 10 runs at 40 vessels — real, not dead code, but not guaranteed every run) |

## Requirement 4 is the important one — done

> **Corrected 5 Sept 2026.** This requirement originally called for "valid bit-level encoding via a shared `aiscodec` package" — the assumption being that AISStream sends raw AIVDM/NMEA, decoded by `aisd` and re-encoded by `aisgen` through the same codec. That assumption was wrong: **AISStream sends pre-decoded JSON.** There is no AIVDM on this wire, so there was never anything for a codec to decode or encode. See [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md) for the full correction.

The guarantee is implemented one layer downstream of where it was originally planned: `aisgen` imports and calls `packages/go/store` directly (promoted out of `services/aisd/internal/store` — see [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md)) rather than writing its own INSERT logic. Synthetic rows land in `ais_positions` through **the exact same batched-upsert code** that real messages go through — `cmd/aisgen/main.go`'s `writeToStore` calls `store.WritePositions`/`WriteStatic`, nothing else.

That is what makes *"the ingest path is identical for real and synthetic data"* structurally true rather than a claim we make on a slide — sameness of the database row, not sameness of a wire decoder. `internal/simulate/simulate_test.go`'s `TestPositionsAndStaticsAreAisdsOwnStoreTypes` is the test asserting this: it checks, via reflection, that the rows `simulate.Run` returns are literally `store.PositionRow`/`store.StaticRow` — the same struct `aisd`'s own recorder builds — not a parallel type that merely looks similar.

## Requirement 6 deserves care

The confounders are what make the evaluation honest. A generator producing clean, well-behaved traffic would let the attribution model look far better than it is.

**Include the innocent-but-suspicious cases specifically:** a vessel with a genuinely flaky transponder, a vessel legitimately out of coverage, a vessel that passes near the slick at the right time but could not have caused it. If the model ranks these highly, that is a real finding — and better discovered here than by a jury.

## Honest framing

Every synthetic result is labelled `SYNTHETIC` — on charts, in tables, in the dossier, on slides. Every time.

> "We validate the attribution engine against real AIS on the NOAA US dataset, where independent tracks exist. We demonstrate on Indian waters using a generator calibrated to lane geometry we recorded live from AISStream, because bulk historical Indian AIS is not publicly available — which is itself part of the capability gap this problem statement exists to close."
