# ADR 0005 — Go for the AIS data plane

- **Status:** Accepted (revised)
- **Date:** 3 September 2026 — revised 5 September 2026
- **Deciders:** Backend/integration lead, AIS/attribution lead
- **Supersedes:** nothing

> **Revision note (5 Sept):** the original version of this ADR asserted that
> AISStream delivers raw AIVDM/NMEA sentences, decoded by a shared
> `aiscodec` package. That is factually wrong — verified against AISStream's
> own documentation and confirmed by the merged implementation in
> [PR #1](https://github.com/SarmaHighOnCode/sagardrishti/pull/1)
> (`services/aisd/internal/aisstream/messages.go`). **AISStream sends
> pre-decoded JSON.** There is no AIVDM on this wire, so there is nothing
> for a codec to decode. The Go-vs-Python decision and every reliability
> argument below are unaffected — they never depended on the wire format —
> but the codec-sharing mechanism for `aisgen` is corrected in
> [Consequences](#consequences).

## Context

The AIS ingest path has properties that the rest of the system does not:

1. **It must run for three months, unattended, starting immediately.** AISStream is our only route to real Indian-waters AIS. Its documentation states plainly that there is **no SLA, no uptime guarantee, and no durable replay of events**. A message we fail to persist is not "retryable later" — it is gone permanently, and with it a piece of the traffic-lane geometry our synthetic generator is calibrated against.

2. **It is IO-bound and long-lived**, not compute-bound and batch. A WebSocket consumer, a decoder, a bounded buffer, and a batching writer.

3. **It should run somewhere other than a developer's laptop.** A spare machine, a Raspberry Pi, or a free-tier VPS — for three months, through reboots, without anyone babysitting a Python environment.

4. **The synthetic generator's output must be indistinguishable from the recorder's, at the point where downstream code consumes it**, or the claim in PRD §6.4 — that the ingest path is the same for real and synthetic data — is not actually true. AISStream's own wire format (JSON, not AIVDM — see the revision note above) turns out not to matter for this: what has to match is the *database row*, since that is the interface every consumer downstream of `aisd`/`aisgen` actually uses.

Python with `asyncio` and `pyais` would work. This is not a case where the alternative fails. It is a case where a different tool fits the shape of the problem better.

## Decision

**Write the AIS data plane in Go 1.23. Keep everything scientific in Python. The boundary is the database.**

| Component | Language |
|---|---|
| `services/aisd` — live AIS recorder | Go |
| `services/aisgen` — synthetic AIS generator | Go |
| SAR, drift, attribution, API, everything else | Python |

Go writes AIS into TimescaleDB. Python reads it. There is no RPC between the two runtimes, no shared memory, and no ambiguity about which language owns which file.

`aisd` decodes AISStream's own JSON envelope directly (`services/aisd/internal/aisstream`) — there is no separate wire-format codec, because AISStream is already decoded. See [Consequences](#consequences) for how `aisgen` still guarantees identical output despite this.

## Rationale

**Why Go is the right fit here specifically:**

- **Reliability under long uptime.** Bounded memory, no GIL, no event-loop starvation when the decoder blocks. Goroutines plus a buffered channel give us a write-behind buffer that back-pressures cleanly instead of growing until the process is killed.
- **Deployment.** A single static binary of roughly 12 MB, cross-compiled, with no runtime to install. `scp` it to any machine and run it under systemd. This directly serves requirement 3.
- **Supervised reconnection.** Exponential backoff with jitter and a persistent write-ahead file is straightforward and hard to get subtly wrong. Implemented and tested in `services/aisd/internal/wal` and `internal/aisstream` (backoff+jitter against a fake server, WAL replay with `ON CONFLICT DO NOTHING` dedup on restart).
- **One writer, two producers.** `aisgen` is Go for the same reason `aisd` is, not because of a shared wire codec: it should share `aisd`'s `internal/store` batched-upsert path, so synthetic messages land in `ais_positions` through the exact same insertion code as real ones. That is what makes "identical ingest path" structurally true — sameness of the database row, not sameness of a decoder. See Consequences for the follow-up this requires.

**Why not Go for anything else:**

- **The API** must call PyTorch and OpenDrift in-process. FastAPI stays.
- **The tile server.** TiTiler exists and works. A Go replacement would be ego, not engineering.
- **The reachability gate.** Tempting for raw speed, but it is a PostGIS spatial query. The database is already the right engine.
- **Anything scientific.** PyTorch, rasterio, xarray, GeoPandas and OpenDrift have no Go equivalents. Rewriting any of it would be actively negligent.

## Consequences

**Positive**

- The recorder can be deployed on day one, on cheap hardware, and left alone — which is the actual constraint driving this decision. **Done:** `services/aisd` is merged, with a systemd unit (`infra/systemd/aisd.service`) for exactly this deployment.
- The two-language split is a defensible engineering story rather than a complication, provided we explain it correctly (see below).
- The reliability mechanisms this ADR asked for are now real, not aspirational: WAL-backed crash recovery, supervised reconnect with backoff+jitter, and batched idempotent upsert are implemented and unit-tested against fake servers/databases (`internal/aisstream`, `internal/wal`, `internal/recorder`, `internal/store`).

**Negative**

- Two toolchains in CI. Mitigated: the Go module is small, self-contained, and its tests run in seconds. *(Follow-up: `packages/go/aiscodec` is a stale placeholder now that this ADR no longer calls for it — see below.)*
- Team members must read a second language. Mitigated: the Go surface is a handful of files and no team member needs to modify it after Phase 1.
- A risk of Go creeping into places it does not belong. **Mitigated by this ADR being explicit about the boundary.** Any proposal to move more of the system to Go must supersede this document.
- ~~**`aisgen` does not yet exist**~~ — **resolved 8 September 2026.** `store`, `aoi` and `quality` were promoted out of `services/aisd/internal/*` into `packages/go/{store,aoi,quality}`; both `services/aisd` and `services/aisgen` depend on that module via a `replace` directive in their own `go.mod` (`replace github.com/sagardrishti/go => ../../packages/go`) — simpler than a `go.work` workspace and unaffected by which directory a CI job runs `go test` from. `aisgen` now calls `store.WritePositions`/`WriteStatic` directly; `internal/simulate`'s `TestPositionsAndStaticsAreAisdsOwnStoreTypes` is the parity test (asserted via reflection) confirming its output really is the same row type, not a second encoding. `aisd`'s own test suite is unchanged and stayed green through the move.

  **What was NOT done as part of this fix, stated plainly:** `aisgen`'s lane geometry is hand-specified from public knowledge of Indian shipping corridors, not the KDE-fitted centrelines requirement 1 of `services/aisgen/README.md` actually calls for — that needs weeks of `aisd`-recorded traffic to fit against, and `aisd` has never recorded a single row (see the still-missed 3 September recorder milestone in `docs/ROADMAP.md`). And `aisgen` has been verified only in dry-run mode (writing JSONL instead of Postgres) — never against a live database, since Docker was down throughout this work.
- `packages/go/aiscodec` (currently an empty placeholder — `.gitkeep` and a README describing AIVDM encode/decode) describes a component that is no longer part of the plan. It should be deleted, or repurposed, in the same change that builds `aisgen`, so the repository does not carry documentation for code that will never be written.

## Defending it

If asked *"why two languages?"*, the answer is:

> "Because the AIS recorder is a data-loss-critical daemon with a three-month uptime requirement against a feed with no replay, and the science pipeline is a GPU-bound research stack. Those are different engineering problems. We used the right tool for each and kept the boundary at the database so neither can destabilise the other."

**Do not say "we used Go because it's fast."** That answer invites the follow-up "what was too slow?", to which the honest answer is "nothing" — and it reframes a sound decision as resume padding.
