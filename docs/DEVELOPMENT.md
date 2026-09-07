# Development Setup

Getting a working environment on Windows machines with an RTX 4060 and an RTX 4070.

**Budget half a day for first-time setup.** Do it in week 1, together, on both machines. Environment problems discovered in November cost days.

---

## 0. The one non-negotiable rule

> ### Use WSL2. Do not attempt native Windows.

GDAL, PROJ, and especially **OpenDrift** are painful to install on native Windows. The conda-forge builds that work reliably are Linux builds. Teams lose days to this every year.

WSL2 gives a real Linux environment with GPU passthrough, full Docker support, and access to your Windows filesystem. There is no meaningful downside.

```powershell
# In an elevated PowerShell, once
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
```

Reboot. Everything after this point happens **inside WSL2**, not in PowerShell.

### The exception, while the pipeline does not exist yet

The rule above is about **GDAL, PROJ and OpenDrift** — the geospatial stack. None of that is wired up yet. Today the API is entirely fixture-backed: it reads no tables and imports nothing heavier than Pydantic.

So until the worker exists, you can run the whole visible system on native Windows, macOS or Linux with no Docker, no Postgres and no WSL2:

```bash
uv venv .venv
uv pip install --python .venv -r services/api/requirements.txt -r services/api/requirements-dev.txt
cd web && npm ci
```

Then, in two terminals:

```bash
make dev-api    # :8000  — FastAPI, reload on
```

```bash
make dev-web    # :5173  — the console, pointed at :8000
```

Open <http://localhost:5173>. You should see the map with two detections, three AIS tracks and a ranked suspects panel — all fetched over HTTP from the API, not from `web/src/lib/fixtures.ts`.

Confirm that with the Network tab: you want requests to `localhost:8000`, not an empty list. If you see **"Failed to fetch"** with nothing in the response, the API is not running or `SAGAR_CORS_ORIGINS` has been set to something that excludes your origin.

Do the full WSL2 setup below **before** starting M1/M2/M5 work. Do not put it off to November.

---

## 1. Prerequisites

| Tool | Version | Install |
|---|---|---|
| WSL2 + Ubuntu 22.04 | — | above |
| Docker Desktop | latest | Windows installer, **enable WSL2 integration for Ubuntu-22.04** |
| NVIDIA driver | ≥ 550 | Windows host driver. Do **not** install a driver inside WSL |
| CUDA toolkit | 12.x | Inside WSL, via the WSL-specific package |
| micromamba | latest | geospatial + OpenDrift environment |
| uv | latest | fast pure-Python environments |
| Go | 1.23+ | AIS data plane |
| Node | 20 LTS | frontend |

### Verify GPU passthrough before anything else

```bash
nvidia-smi
```

If this does not show your card inside WSL, stop and fix it. Nothing downstream will work.

---

## 2. Two Python environments, on purpose

This looks like complexity. It prevents a category of dependency conflict that is very hard to unpick later.

| Environment | Manager | Contains | Used by |
|---|---|---|---|
| `sagar-geo` | **micromamba** (conda-forge) | GDAL, PROJ, OpenDrift, xarray, cartopy, rasterio | Worker, ML training, drift |
| `sagar-api` | **uv** (PyPI) | FastAPI, Pydantic, ARQ, asyncpg, httpx | API service |

**Why split.** The conda-forge geospatial stack pins compiled dependencies aggressively. Mixing it with a fast-moving pure-Python web stack produces conflicts that waste hours. Separating them means the API can update freely while the geo environment stays pinned and reproducible.

```bash
# geo environment
micromamba create -f infra/env/geo.yml
micromamba activate sagar-geo

# api environment
uv venv .venv && source .venv/bin/activate
uv pip install -r services/api/requirements.txt
```

`make setup` does both, plus Go modules and npm.

---

## 3. Repository setup

```bash
git clone https://github.com/<org>/sagardrishti.git
cd sagardrishti
cp .env.example .env
```

Fill in `.env` with credentials from the accounts listed in [`DATA_SOURCES.md`](DATA_SOURCES.md) §6. **`.env` is git-ignored and must stay that way** — a committed CDSE token is both a security problem and an embarrassing thing for a jury to find in your history.

```bash
make setup     # environments + dependencies
make up        # docker compose: db, redis, api, worker, tiler, web
make demo      # load the cached MSC ELSA 3 scenario
```

| Service | URL |
|---|---|
| Operator console | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Tile server | http://localhost:8001 |
| PostGIS | localhost:5432 |

---

## 4. Start the AIS recorder — today

**This is the highest-leverage action in the project and it is time-critical.**

AISStream offers no replay. Every day the recorder is not running is a day of Indian AIS permanently unavailable to us, and the synthetic generator's lane calibration depends on it.

```bash
cd services/aisd
go build -o aisd ./cmd
./aisd --config config/arabian-sea.yaml
```

**Deploy it somewhere it will stay running for three months.** A spare laptop, a Raspberry Pi, or a free-tier VPS. Under systemd, not in a terminal someone will close.

```bash
sudo cp infra/systemd/aisd.service /etc/systemd/system/
sudo systemctl enable --now aisd
```

The Go binary is static and has no runtime dependencies — that is precisely why it is written in Go ([ADR 0005](adr/0005-go-for-the-ais-data-plane.md)). Copy the binary, copy the config, run it.

**Verify it is actually recording** — daily for the first week, weekly after:

```bash
make ais-status     # rows in last 24h, gap report, reconnect count
```

---

## 5. GPU allocation

| Machine | Card | Role |
|---|---|---|
| A | **RTX 4070, 12 GB** | Training. Keep it free — do not run the dev stack here |
| B | **RTX 4060, 8 GB** | Development, integration, inference, the UI |

**Training on the 4070:** SegFormer-B2 at 512², batch 8–16 with AMP fits comfortably.

**If you must train on the 4060:** batch 4 with gradient accumulation ×2 to keep the effective batch at 8. Expect roughly 1.6× the wall time.

Always use AMP (`torch.amp`). It roughly halves memory and speeds training up on both cards for no accuracy cost on this task.

---

## 6. Common problems

| Symptom | Cause | Fix |
|---|---|---|
| `nvidia-smi` works in PowerShell, not WSL | Driver installed inside WSL | Uninstall it. Only the Windows host driver is needed |
| GDAL import fails with a PROJ error | Mixed pip and conda GDAL | Never `pip install gdal` in the geo env. Use conda-forge only |
| OpenDrift install hangs solving | conda solving from defaults | Use micromamba with conda-forge, and `channel_priority: strict` |
| Docker cannot see the GPU | Missing container toolkit | Install `nvidia-container-toolkit` inside WSL, restart Docker Desktop |
| Extremely slow file IO | Repository on `/mnt/c/` | **Clone inside the WSL filesystem** (`~/sagardrishti`). Crossing the Windows boundary is very slow |
| PostGIS extension missing | Wrong base image | Use `timescale/timescaledb-ha:pg16` — PostGIS is included |
| `aisd` reconnect-looping | Bad or rate-limited API key | Check `make ais-status`. Verify the key at aisstream.io |
| CUDA out of memory | Batch too large for 8 GB | Batch 4 + accumulation ×2, and confirm AMP is on |

---

## 7. Working agreements

| Practice | Rule |
|---|---|
| Branching | `feat/`, `fix/`, `docs/`, `chore/` off `main`. Never commit to `main` |
| Commits | Conventional Commits — `feat(m6): add reachability gate` |
| PRs | Required. One reviewer. CI green — `ruff`, `pytest`, `go test`, `tsc` |
| Module ownership | See PRD §12. Ask the owner before changing their module's public interface |
| **API contract** | **Frozen 15 October.** Changes after that need the integration lead's sign-off |
| Secrets | Never committed. `.env` only |
| Large files | Never in git. `data/` is ignored; use the shared SSD |
| Documentation | A module without a README is not done |

### The weekly integration build

**Every Friday, `main` must run end to end and be demoable.** Not "nearly working" — actually running, on the cached scenario, start to finish.

This is the single most effective defence against risk #1, which has ended more SIH projects than any algorithmic problem. Three subsystems that each work in isolation and have never been run together is the classic failure, and it becomes visible only in December when there is no time left.

---

## 8. Useful commands

```bash
make setup           # environments and dependencies
make up / down       # start / stop the stack
make logs            # tail all containers
make test            # unit + contract tests
make test-integration# full pipeline on a cached scene
make lint            # ruff, tsc, go vet
make demo            # load cached demo scenarios
make warm-cache      # populate the offline cache (online, slow)
make offline         # bring the stack up in cache-only mode
make evaluate        # regenerate all metrics and figures
make ais-status      # AIS recorder health
make docs            # serve the MkDocs site locally
```
