# `web` — Operator Console

React 19 + Vite + TypeScript. MapLibre GL + deck.gl. **Owner: Frontend lead.**

## Read this first

[`docs/DESIGN_SYSTEM.md`](../docs/DESIGN_SYSTEM.md) — the complete interface specification. Colour tokens, density, typography, component patterns, and the anti-patterns list.

**Target: a Palantir-grade intelligence interface.** Not a dashboard. An operator console for someone deciding about a specific vessel, at 03:00, under time pressure.

> **Principle zero:** the interface is evidence, not decoration. Every pixel carries information an analyst can act on, or it is removed. Uncertainty is always rendered, never flattened into a confident marker.

## Stack

| Layer | Choice |
|---|---|
| Framework | React 19 + Vite + TypeScript |
| **Design tokens** | **Blueprint 6 — Palantir's own open-source design system**, used verbatim |
| Primitives | Radix / shadcn |
| Utility CSS | Tailwind v4, themed with Blueprint tokens |
| Heavy grid | `@blueprintjs/table` where a virtualised operator grid is genuinely needed |
| Map | MapLibre GL 6 |
| GPU layers | deck.gl 9 |
| Server state | TanStack Query |
| UI state | Zustand |
| Charts | visx or Recharts |

Verified: `@blueprintjs/core@6.18` peer-depends on `react: 18 || 19`.

## Why deck.gl and not Leaflet

**100k animated drift particles at 60 fps.** Leaflet cannot do it, and that animation is the best moment in the demo.

## Structure

```
src/
  app/          shell, routing, layout, keyboard shortcuts
  components/   Panel, ConfidenceBar, FactorBars, MetricRow,
                Timeline, LayerLegend, StatusStrip
  features/     detection/, drift/, attribution/, darkvessel/, evidence/
  lib/          api client, deck.gl layer factories, MapLibre style, formatters
  styles/       tokens.css, tailwind theme
```

## Two rules that get enforced in review

**Token discipline.** The palette lives in exactly one place — `src/styles/tokens.css`. **No hex literal appears anywhere else.** The PDF dossier generator reads the same tokens; drift between screen and export is a credibility failure.

**Centralised formatters.** `formatCoord`, `formatUTC`, `formatMMSI`, `formatHash` in `lib/format.ts` are the only way those values reach the screen. Identifiers are monospace, timestamps are ISO 8601 UTC, coordinates are six decimals with explicit hemisphere — consistently across tooltip, table, panel and PDF.

## The three components that matter most

| Component | Demo beat | Why |
|---|---|---|
| **Rejection panel** | 1:50 | Shows *why* a candidate was demoted. Almost no other team will have this |
| **Factor bars** | 6:30 | Makes "we rank, we never accuse" visible. The actual arithmetic, not a black-box visualisation |
| **Filter cascade audit** | 4:00 | 214 to 7 with every drop reason. Directly answers the PS |

## Offline

**No CDN references anywhere.** Fonts self-hosted, basemap tiles bundled as local MBTiles, no remote style JSON. A single font-CDN `<link>` produces a multi-second stall on a dead network and looks like a crash. See [`OFFLINE_MODE.md`](../docs/OFFLINE_MODE.md).
