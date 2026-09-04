# ADR 0005 — Go for the AIS data plane

- **Status:** Accepted
- **Date:** 3 September 2026
- **Deciders:** Backend/integration lead, AIS/attribution lead
- **Supersedes:** nothing

## Context

The AIS ingest path has properties that the rest of the system does not:

1. **It must run for three months, unattended, starting immediately.** AISStream is our only route to real Indian-waters AIS. Its documentation states plainly that there is **no SLA, no uptime guarantee, and no durable replay of events**. A message we fail to persist is not "retryable later" — it is gone permanently, and with it a piece of the traffic-lane geometry our synthetic generator is calibrated against.

2. **It is IO-bound and long-lived**, not compute-bound and batch. A WebSocket consumer, a decoder, a bounded buffer, and a batching writer.

3. **It should run somewhere other than a developer's laptop.** A spare machine, a Raspberry Pi, or a free-tier VPS — for three months, through reboots, without anyone babysitting a Python environment.

4. **The synthetic generator must produce byte-identical message encoding to what the recorder decodes**, or the claim in PRD §6.4 — that the ingest path is the same for real and synthetic data — is not actually true.

Python with `asyncio` and `pyais` would work. This is not a case where the alternative fails. It is a case where a different tool fits the shape of the problem better.

## Decision

**Write the AIS data plane in Go 1.23. Keep everything scientific in Python. The boundary is the database.**

| Component | Language |
|---|---|
| `services/aisd` — live AIS recorder | Go |
| `services/aisgen` — synthetic AIS generator | Go |
| `packages/go/aiscodec` — AIVDM/NMEA encode + decode | Go |
| SAR, drift, attribution, API, everything else | Python |

Go writes AIS into TimescaleDB. Python reads it. There is no RPC between the two runtimes, no shared memory, and no ambiguity about which language owns which file.

## Rationale

**Why Go is the right fit here specifically:**

- **Reliability under long uptime.** Bounded memory, no GIL, no event-loop starvation when the decoder blocks. Goroutines plus a buffered channel give us a write-behind buffer that back-pressures cleanly instead of growing until the process is killed.
- **Deployment.** A single static binary of roughly 12 MB, cross-compiled, with no runtime to install. `scp` it to any machine and run it under systemd. This directly serves requirement 3.
- **Supervised reconnection.** Exponential backoff with jitter and a persistent write-ahead file is straightforward and hard to get subtly wrong.
- **One codec, two consumers.** Bit-level AIVDM packing is exactly the kind of work where Go's explicitness beats Python's convenience. Sharing `aiscodec` between `aisd` and `aisgen` makes the "identical ingest path" claim structurally true rather than aspirational.

**Why not Go for anything else:**

- **The API** must call PyTorch and OpenDrift in-process. FastAPI stays.
- **The tile server.** TiTiler exists and works. A Go replacement would be ego, not engineering.
- **The reachability gate.** Tempting for raw speed, but it is a PostGIS spatial query. The database is already the right engine.
- **Anything scientific.** PyTorch, rasterio, xarray, GeoPandas and OpenDrift have no Go equivalents. Rewriting any of it would be actively negligent.

## Consequences

**Positive**

- The recorder can be deployed on day one, on cheap hardware, and left alone — which is the actual constraint driving this decision.
- Real and synthetic AIS provably share an encoder.
- The two-language split is a defensible engineering story rather than a complication, provided we explain it correctly (see below).

**Negative**

- Two toolchains in CI. Mitigated: the Go module is small, self-contained, and its tests run in seconds.
- Team members must read a second language. Mitigated: the Go surface is roughly three files and no team member needs to modify it after Phase 1.
- A risk of Go creeping into places it does not belong. **Mitigated by this ADR being explicit about the boundary.** Any proposal to move more of the system to Go must supersede this document.

## Defending it

If asked *"why two languages?"*, the answer is:

> "Because the AIS recorder is a data-loss-critical daemon with a three-month uptime requirement against a feed with no replay, and the science pipeline is a GPU-bound research stack. Those are different engineering problems. We used the right tool for each and kept the boundary at the database so neither can destabilise the other."

**Do not say "we used Go because it's fast."** That answer invites the follow-up "what was too slow?", to which the honest answer is "nothing" — and it reframes a sound decision as resume padding.
