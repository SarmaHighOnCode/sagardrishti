# `infra`

Docker, Compose, environments, deployment scripts.

```
docker/      Dockerfiles per service
compose/     Compose fragments and overrides
env/         micromamba environment files (geo.yml)
systemd/     unit files — notably aisd.service
scripts/     cache warming, backup, health checks
wheels/      vendored Python wheels for offline installs
```

## Bring-up

```bash
make up                                    # normal
make offline                               # cache-only mode
```

| Service | Image |
|---|---|
| `db` | `timescale/timescaledb-ha:pg16` |
| `redis` | `redis:7-alpine` |
| `api` | local build, uv environment |
| `worker` | local build, micromamba geo env, GPU passthrough |
| `tiler` | `ghcr.io/developmentseed/titiler` |
| `aisd` | local build, `scratch` base — **static Go binary** |
| `web` | local build |

**Not Kubernetes.** One box, Compose. Noted in [`ARCHITECTURE.md`](../docs/ARCHITECTURE.md) section 11.

## Two Python environments

`env/geo.yml` (micromamba, conda-forge) for GDAL/PROJ/OpenDrift. `uv` for the API. The conda-forge geospatial stack pins compiled dependencies aggressively; mixing it with a fast-moving web stack wastes hours. [`DEVELOPMENT.md`](../docs/DEVELOPMENT.md) section 2.

## `aisd` runs outside Compose too

`systemd/aisd.service` deploys the recorder to a spare machine or VPS, independently of the rest of the stack. That independence is the point — it must run for three months regardless of whether anything else works. [ADR 0005](../docs/adr/0005-go-for-the-ais-data-plane.md).

## Offline

`compose/docker-compose.offline.yml` sets `SAGAR_OFFLINE=1`, switching every fetcher to cache-only, pointing the frontend at local tiles, and disabling update checks.

**Leak detection:** run the stack on an internal-only Docker network so any outbound attempt fails loudly rather than hanging.

```bash
docker network create --internal sagar-offline
```

Worth a nightly CI job once the stack stabilises — a dependency added in December then fails in CI rather than on stage. [`OFFLINE_MODE.md`](../docs/OFFLINE_MODE.md).
