# Demo Script

Ten minutes. **Rehearse twenty times.** The demo owner (role 6) owns this document and the rehearsal schedule.

The single most common way a good SIH project loses is a demo that runs long, breaks, or fails to make its point in the first ninety seconds. Everything here is about preventing that.

---

## Run of show

| Time | Beat | What is on screen | What the presenter says |
|---|---|---|---|
| **0:00** | **The gap** | One slide. The three-row capability table | Illegal operational discharge is routine. India has forward drift — INCOIS OOSA v5.0 — and a response authority — ICG under NOSDCP. What is missing is automated attribution. Today it is manual, slow, and in practice almost never happens |
| **0:45** | **Live ingest** | Scene selector, Arabian Sea. Preprocessing progress with named stages | Sentinel-1C, acquired 25 May. Calibrated, resampled to a fixed 40 metres per pixel, tiled |
| **1:30** | **Detection** | Slick polygon appears with attributes | 12.4 km², bearing 247°, damping ratio 8.4 dB, confidence 0.81 |
| **1:50** | **★ The rejected candidate** | Click a grey polygon. The rejection panel opens | *This* is a candidate we rejected. Confidence went from 0.62 to 0.19 — wind speed 1.6 m/s, below the detection window; chlorophyll anomaly plus 2.1 sigma; and this location produced a dark formation in 4 of the last 12 scenes. It is a low-wind biogenic film, not oil |
| **3:00** | **Hindcast** | Backward ensemble animates, violet, cone widening | Backward drift. Note this is not a point — it is a probability field, and it widens with time because our best free currents are 8 km resolution and the eddies that shape slicks are smaller than that |
| **4:00** | **Traffic filter** | 214 AIS tracks appear, cascade runs to 7 | 214 vessels in the window. Reachability gate, timing, kinematics, drift-score floor — down to 7. Every drop is logged with its reason |
| **5:00** | **Attribution** | Per-vessel plumes animate simultaneously | We assume every vessel might have discharged at every moment along its track, and drift all of it forward to the acquisition time. One plume lands on the slick |
| **6:30** | **★ Explanation** | Suspect panel with factor bars | Drift consistency 0.81, course alignment 0.94, a 40-minute AIS gap at the inferred release time, speed 30% below its own median, night, 12 nm off the lane. Inferred release 06:40 UTC ± 50 minutes — **which makes the slick 7.3 hours old.** We never measured age from the image; it falls out of the solve |
| **7:30** | **Dark vessel** | Second scene. Red pulsing marker | A SAR bright target with no AIS correlate. This is the case CleanSeaNet cannot solve — no ship broadcasting means nothing to correlate against |
| **8:15** | **Forecast + impact** | Forward run, cerulean, shoreline risk | 48 hours forward with weathering. Shoreline impact probability, eco-sensitive zone intersection |
| **8:45** | **Evidence pack** | PDF generates, provenance page shown | Product ID, SHA-256 of the source scene, model weights hash, forcing dataset versions, config snapshot. This is what makes it defensible |
| **9:15** | **★ Honest limits** | One slide, three bullets | Currents are 8 km, slicks are 40 m — our dominant error term. Cross-domain mIoU drops 10–20 points between basins. Indian AIS is synthetic, calibrated to lanes we recorded live, because bulk historical Indian AIS does not exist publicly |
| **9:45** | **Path to operational** | Final slide | INCOIS high-resolution currents. ICG AIS feed. NISAR — a NASA–ISRO mission whose L-band data went public in July. Deployment on NIC infrastructure |

**★ marks the three beats that win the demo.** If time runs short, cut 8:15 first, then 7:30. **Never cut 1:50, 6:30 or 9:15.**

---

## Why these three beats matter most

**1:50 — the rejected candidate.** Every team will show a detection. Almost none will show a *rejection with reasons*. This beat proves the physics filter exists, that we understand look-alikes, and that the analyst can audit the system. It is thirty seconds and it separates us from the field.

**6:30 — the explanation panel.** This is where "we rank, we never accuse" becomes visible rather than asserted, and where the age inference lands. The factor bars are the actual arithmetic, not a visualisation of a black box.

**9:15 — honest limits.** Volunteering the dominant limitation before a judge finds it is the highest-value thirty seconds in the presentation. It converts every subsequent claim from "unverified" to "from a team that tells us when things don't work."

---

## Preparation

### Pre-computed vs live

| Runs live | Pre-computed and cached |
|---|---|
| Scene selection and tiling | Full 100-member drift ensembles |
| Segmentation inference | Per-vessel attribution advection |
| Stage C physics filter | 48-hour forecast |
| Scoring and ranking | Evidence PDF (pre-rendered, regenerated live for show) |

**Be honest about this if asked.** The prepared answer is in [`VIVA_DEFENCE.md`](VIVA_DEFENCE.md) §E. Keep a **live-compute button** for one small scenario — a handful of vessels, a short window — so the claim that it is real is demonstrable on demand.

Never claim live computation you are not doing. If caught, every other claim becomes suspect.

### The cache

```
data/demo/
  scenario_elsa3/       headline — MSC ELSA 3, known vessel
  scenario_darkvessel/  the 7:30 beat
  scenario_lookalike/   the 1:50 beat — rejection with reasons
  scenario_live/        small, genuinely computes in under 60 s
```

Every scenario must run with the network cable out. See [`OFFLINE_MODE.md`](OFFLINE_MODE.md).

---

## Failure recovery

Rehearse each of these until the recovery is automatic. **Never debug on stage.**

| Failure | Recovery |
|---|---|
| Detection returns nothing | "Let me use the cached scenario" — switch immediately, keep talking. Do not investigate |
| Map fails to render | Screenshot fallback deck, one slide per beat. Keep narrating |
| Drift animation stutters | Pause it, use the static time-slice view. The scrubber still works |
| API times out | Restart button on the demo control panel; meanwhile talk through the architecture slide |
| Whole stack down | **Recorded video of the full run.** Have it on the machine, in the deck, and on a USB stick |
| Judge asks for an unseen scene | Run it if offline mode supports it. If it fails, that is a real result — say what you would expect and why |
| Projector colour is wrong | The interface is dark-on-dark. **Check the projector before the slot** and have a high-contrast mode ready |

**The recorded video is not optional.** It costs an afternoon and it is the difference between a bad day and no demo.

---

## Rehearsal log

| # | Date | Presenter | Time | What broke | Fixed |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

Target: **20 rehearsals before the finale**, at least 5 with a full run-through under time, at least 3 with the network physically disconnected, and at least 2 with a teammate playing a hostile judge interrupting mid-demo.

---

## Speaking notes

- **Time is the enemy.** At 10 minutes with questions, every sentence must earn its place. Cut adjectives, not content.
- **One presenter drives, one operates.** The person talking should not be the person clicking.
- **Say the number, then the meaning.** "0.71 posterior — the most drift-consistent candidate of seven" not "a high score."
- **Never say "identifies the culprit."** Say "ranks candidates." Every single time. This is a product principle, and inconsistency here undermines the legal-defensibility claim.
- **When a judge interrupts, stop and answer.** Engagement is good. Do not defer to "I'll cover that later" unless you genuinely will within thirty seconds.
- **End on the operational path, not on limitations.** Limits at 9:15, then finish forward-looking at 9:45.
