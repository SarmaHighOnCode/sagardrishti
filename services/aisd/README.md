# `aisd` — AIS Recorder (Go)

Live AIS recorder. Consumes AISStream over WebSocket, decodes, persists to TimescaleDB.

> ## Start this today.
> AISStream provides **no SLA and no durable replay**. A message not persisted on receipt is permanently lost. Every day this is not running is a day of Indian AIS we can never recover, and the synthetic generator's lane calibration depends on it.
>
> This is the highest-leverage single action in the project and it takes an afternoon.

## Why Go

This is a **data-loss-critical daemon with a three-month uptime requirement**. Goroutines for concurrent bounded-buffer writes, flat memory under sustained load, and a ~12 MB static binary that deploys anywhere with no Python environment to install.

Full reasoning in [ADR 0005](../../docs/adr/0005-go-for-the-ais-data-plane.md). **Do not say "we used Go because it's fast"** — that reframes a sound decision as resume padding.

## Reliability requirements

| Requirement | Why |
|---|---|
| Supervised reconnect, exponential backoff with jitter | The feed drops. Planned for, not exceptional |
| Bounded write-behind buffer | Back-pressure cleanly instead of growing until the OOM killer intervenes |
| Write-ahead file | A database outage must not lose the stream |
| Batch COPY into Timescale | Per-message inserts will not keep up |
| Structured logging with reconnect counters | `make ais-status` reads these |

## Deployment

Under systemd, on a machine that will stay up. **Not in a terminal someone will close.**

```bash
go build -o aisd ./cmd
sudo cp infra/systemd/aisd.service /etc/systemd/system/
sudo systemctl enable --now aisd
```

Static binary, no runtime dependencies. Copy the binary, copy the config, run it.

## AOIs

Both from day one:

| AOI | Bounds |
|---|---|
| Arabian Sea | Gulf of Kutch to Kanyakumari, out to the EEZ |
| Bay of Bengal | Kanyakumari to the Sundarbans |

## Verify it is recording

```bash
make ais-status     # rows in last 24h, gap report, reconnect count
```

**Daily for the first week, weekly after.** A recorder that silently stopped in October and is discovered in December is the worst outcome available here.

## Known limitation — state it honestly

AISStream uses terrestrial receivers, so coverage degrades with distance from shore and is sparse in the open ocean — which is exactly where much operational discharge happens.

We use this data for **lane geometry calibration**, not as a complete traffic picture. It is also why the AIS gap factor needs a coverage correction ([`SCORING_MODEL.md`](../../docs/SCORING_MODEL.md) section 2.1).
