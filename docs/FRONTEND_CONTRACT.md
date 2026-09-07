# Frontend ↔ Backend Contract

**Read this before writing console code.** It is short on purpose.

The rule underneath everything here: **the console renders what the API returns.** Not what we hope it will return, not a local copy, not a plausible-looking placeholder. A screen that looks right with the API switched off is the most expensive kind of wrong, because the first person to discover it is a judge.

Most of this is enforced by CI. The parts that are not are marked **[judgement]**.

---

## 1. Get it running

Two terminals, from the repo root. No Docker, no Postgres, no WSL2 — the API is fixture-backed and reads no tables.

```bash
make dev-api
```

```bash
make dev-web
```

Console on <http://localhost:5173>, API docs on <http://localhost:8000/docs>.

If the console shows **"Failed to fetch"**: the API is not running, or `SAGAR_CORS_ORIGINS` excludes your origin. The API only grants `localhost:5173` and `127.0.0.1:5173` by default.

---

## 2. What actually works today

Everything below is **fixture-backed**: real HTTP, real schemas, hardcoded data. There is no database, no SAR processing, no drift model.

| Endpoint | Returns | Client function |
|---|---|---|
| `GET /scenes` | `Page<Scene>` | `listScenes()` |
| `GET /scenes/{id}` | `Scene` | `getScene()` |
| `GET /detections` | `Page<Detection>` | `listDetections()` |
| `GET /detections/{id}` | `Detection` | `getDetection()` |
| `GET /detections/{id}/suspects` | `Suspect[]` | `getSuspects()` |
| `GET /detections/{id}/audit` | `AuditTrail` | `getAudit()` |
| `GET /ais/tracks` | `Page<AisTrack>` | `listAisTracks()` |
| `GET /ais/vessels/{mmsi}` | `VesselStatic` | `getVessel()` |
| `GET /ships` | `Page<ShipDetection>` | `listShips()` |
| `GET /ships/{id}` | `ShipDetection` | `getShip()` |

### What returns 501, and why it must stay visible

| Endpoint | Blocked on |
|---|---|
| `GET /detections/{id}/hindcast` | M5 drift engine |
| `GET /detections/{id}/forecast` | M5 drift engine |
| `POST /detections/{id}/evidence` | M7 dossier + job queue |
| `POST /scenes/{id}/analyse` | the worker service |

`GET /jobs/{id}` returns **404**, not 501 — the endpoint works fine, no job has ever been created because nothing issues job ids yet.

**These 501s are a feature.** `lib/api.ts` throws `NotImplementedError` (a distinct subclass of `ApiError`) so you can render *"Drift hindcast — not available until M5"* instead of an empty chart. An empty chart means "zero drift". That is a different claim, and it is false.

```ts
try {
  const drift = await getHindcast(id);
} catch (e) {
  if (e instanceof NotImplementedError) {
    // Render an honest "not built yet" panel. e.problem.detail says why.
    return <Pending reason={e.problem.detail} />;
  }
  throw e;
}
```

Nothing in the console calls these yet. Building the panel that does is a genuinely useful task.

### Demo fixture ids

| | |
|---|---|
| Scene | `S1C_IW_GRDH_1SDV_20260525T064012` |
| Detections | `det_synthetic_001` (oil), `det_synthetic_002` (look-alike, rejected) |
| Ships | `shp_1`, `shp_2`, `shp_3` (dark) |
| Vessels | `419001234`, `563889000`, `477995100` |

---

## 3. The five rules

### 3.1 Never import fixture *data* into a component — **CI-enforced**

```ts
import { SAMPLE_SLICKS } from "../lib/fixtures";   // ✗ CI fails
import type { SlickFeature } from "../lib/fixtures"; // ✓ view type, fine
```

`fixtures.ts` holds two different things: **view types** (`SlickFeature`, `VesselTrack`, `ShipPoint`) which are the console's own models and free to import anywhere, and **sample data** (`SAMPLE_*`) which exists only so tests and the map have something to render in isolation. Importing the data into a component builds a screen that works with the backend down.

Fetch through `lib/queries.ts` instead. If you need a new query, add a hook there.

### 3.2 Never invent a field — **CI-enforced**

`web/src/lib/apiTypes.ts` mirrors `services/api/app/schemas.py`. It is hand-written, which means it *can* drift — so it is checked:

- `src/lib/contract.ts` lists every field of every wire type as a real value. `FieldSpec<T>` is computed **from the interface**, so `tsc` fails if a manifest and its interface disagree.
- `src/lib/contract.test.ts` diffs those manifests against `docs/api/openapi.json`, generated from the server's own Pydantic models.

Result: you cannot add a field to `apiTypes.ts` that the server does not send. It would be `undefined` at runtime and render as a blank panel — which reads as *"no data"*, not *"wrong field name"*. That bug can survive a long time.

**When the contract test fails, do not edit until it goes green.** Work out which side is wrong:

| Failure | Means |
|---|---|
| Field on server, missing in client | API gained a field. Mirror it, or decide you don't need it |
| Field in client, missing on server | You invented it. Remove it, or add it to `schemas.py` first |
| Optionality disagrees | The dangerous one — see below |

Client `required` + server `optional` means you will dereference a field the server may omit. It works for every record until the one that doesn't have it.

**Changing the API?** Edit `schemas.py`, then run `python tools/export_openapi.py` and commit the regenerated `docs/api/openapi.json` in the same commit. CI fails if it is stale.

### 3.3 Never show an empty state that could be mistaken for data — **[judgement]**

Loading, error, and empty are three different things and must look different.

An empty detections panel while a request is in flight silently claims *"we scanned and found nothing."* `Shell.tsx` handles this with `QueryStatusRow`; follow that pattern. Every TanStack hook gives you `isLoading` and `error` — use both.

When an API call fails, render `error.message`. `lib/api.ts` already extracts the server's RFC 7807 `detail`, which is the most useful sentence available. Replacing it with "Something went wrong" throws that away.

### 3.4 Never filter out exculpatory evidence — **[judgement]**

`SuspectFactor.contribution` can be **negative**. Those are factors arguing a vessel is *innocent*, and they must render exactly like positive ones. Sorting by absolute value is fine; dropping them is not.

This is the difference between a ranking tool and an accusation tool. Same reason `Detection.confidence_raw` is struck through in the UI rather than hidden — the analyst sees the score went `0.62 → 0.19` and why.

### 3.5 Colours come from tokens — **CI-enforced**

No hex literals outside `web/src/styles/tokens.css`. The PDF dossier generator reads the same tokens; drift between screen and export is a credibility failure. Read them via `lib/tokens.ts`.

---

## 4. Where things live

```
web/src/
  app/Shell.tsx        layout + selection state. Reads no wire types directly
  lib/apiTypes.ts      wire types — mirrors schemas.py. CI-checked
  lib/api.ts           typed fetch. Throws ApiError / NotImplementedError
  lib/queries.ts       TanStack hooks. Adaptation happens HERE, not in components
  lib/adapters.ts      wire types → view types
  lib/contract.ts      field manifests. Do not hand-edit to silence a test
  lib/fixtures.ts      view types + SAMPLE_* data (tests and map only)
  features/map/        MapCanvas — maplibre-gl + deck.gl
  components/          Panel, ConfidenceBar, StatusStrip
```

**Components should not see wire types.** `queries.ts` adapts `Detection` → `SlickFeature` before it reaches a component, which is what keeps `Shell.tsx` readable as a layout rather than a mapping exercise. Keep it that way.

Two things worth knowing about `MapCanvas.tsx` before you touch it:

- It mounts the map **once** and pushes data through `overlay.setProps()` in a separate effect. Merging those effects remounts the map on every refetch and throws away the operator's pan and zoom. There is a test pinning this.
- Click hit-testing is **geographic** (`lib/geo.ts` `pointInPolygon`), not deck.gl picking. deck.gl's picking framebuffer reported a 300×150 viewport against a 1172×772 canvas and silently never matched. Don't "simplify" it back.

---

## 5. Before you push

```bash
cd web && npm run lint && npx tsc --noEmit && npm test
```

Branch, push, open a PR. Never commit to `main`.

CI runs: python tests + schema freshness, web typecheck + lint + tests, Go vet/test, and the project guards (hex colours, fixture data in components, accusatory language, committed secrets).

---

## 6. Good first tasks

1. **The 501 panel.** Wire the Drift rail button to `getHindcast()` and render `NotImplementedError` honestly. The whole design exists and nothing exercises it.
2. **The audit cascade.** `getAudit()` returns the 214 → 7 filter chain with per-stage drop counts and is fully populated for `det_synthetic_001`. Nothing renders it. It is the strongest defensibility story we have.
3. **Vessel detail.** `getVessel(mmsi)` returns `VesselStatic` including `baseline_gap_profile`. Note `has_sufficient_history` — when it is `false`, the AIS-gap factor must be shown as low-confidence. An unknown vessel is unknown, never silently treated as average.
