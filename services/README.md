# Services

Deployable processes. Everything here has a Dockerfile and a lifecycle.

| Service | Runtime | Purpose |
|---|---|---|
| [`api`](api/) | Python / FastAPI | REST + SSE for the console |
| [`worker`](worker/) | Python / ARQ | Runs M1–M7. Where the science executes |
| [`tiler`](tiler/) | TiTiler | Serves COGs as XYZ tiles |
| [`aisd`](aisd/) | **Go** | Live AIS recorder. Runs 24/7 for three months |
| [`aisgen`](aisgen/) | **Go** | Synthetic AIS generator |

## Two runtimes, one boundary

**Go owns the AIS data plane. Python owns the science. The boundary is the database.** No RPC between them. See [ADR 0005](../docs/adr/0005-go-for-the-ais-data-plane.md).

## `aisd` is deliberately independent

It depends on nothing except a database connection string — **not on the API, the worker, or anything else in the stack**. It must be deployable on a spare laptop or VPS on day one and left running for three months regardless of whether the rest of the system works yet.

That independence is a design requirement, not an accident.
