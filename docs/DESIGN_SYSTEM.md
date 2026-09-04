# Design System — the SAGARDRISHTI Operator Console

**Target: a Palantir-grade intelligence interface.** Not a dashboard. Not a data-viz portfolio piece. An operator console for someone who has to make a defensible decision about a specific vessel, at 03:00, under time pressure.

> **Design principle zero:** *The interface is evidence, not decoration.* Every pixel either carries information an analyst can act on, or it is removed. Uncertainty is always rendered — never flattened into a single confident marker.

---

## 1. Why Blueprint is the anchor

**Blueprint is Palantir's own open-source design system** — a React toolkit they built and use for exactly this class of problem: complex, data-dense desktop interfaces for operators processing large volumes of structured information in environments where a missed detail has real consequences. That is a precise description of our user.

We therefore do not *imitate* the Palantir look. We adopt the actual system, and use their published tokens verbatim.

### The hybrid, and why

| Layer | Choice | Reason |
|---|---|---|
| **Colour, density, typography** | **Blueprint 6 tokens, verbatim** | This is the Palantir visual language. Copying the tokens is the whole point |
| **Interactive primitives** | **Radix UI / shadcn** | Modern accessibility, unstyled, composable, better DX than fighting Blueprint's component API |
| **Utility styling** | **Tailwind v4**, configured with Blueprint tokens as the theme | Speed. The palette below becomes the Tailwind theme, so `bg-dark-gray2` is Blueprint's exact `#252a31` |
| **The heavy grid** | **`@blueprintjs/table`** | When we need a virtualised, resizable, 10k-row operator grid, Blueprint's table is genuinely excellent and reimplementing it is a waste of the timeline |

Verified compatible: `@blueprintjs/core@6.18`, `@blueprintjs/table@6.2` — peer dependency `react: 18 || 19`. We target React 19.

> **Rule:** never mix Blueprint components and shadcn components inside the same visual unit. Pick one per panel. Mixed button styles inside one toolbar is the fastest way to look amateur.

---

## 2. Colour

Blueprint's exact palette. These are the values, not approximations.

### 2.1 Greyscale — the structural spine

```
$black        #111418     app chrome, deepest wells, map background
$dark-gray1   #1c2127     primary panel background
$dark-gray2   #252a31     DEFAULT APP BACKGROUND  ← Blueprint dark theme base
$dark-gray3   #2f343c     raised surface, popovers, panel headers
$dark-gray4   #383e47     borders, dividers, hover fill
$dark-gray5   #404854     active fill, selected row
$gray1        #5f6b7c     disabled text, tertiary icons
$gray2        #738091     secondary text, axis labels
$gray3        #8f99a8     muted body text
$gray4        #abb3bf     body text (dark theme)
$gray5        #c5cbd3     primary text (dark theme)
$light-gray1  #d3d8de
$light-gray5  #f6f7f9     high-emphasis headings on dark
$white        #ffffff     reserved — use sparingly, it is loud on a dark canvas
```

### 2.2 Intents — meaning, never mood

Only four intents. Each has exactly one meaning in this product. Never use an intent colour decoratively.

| Intent | Ramp (1→5) | Reserved for |
|---|---|---|
| **Blue** | `#184a90` `#215db0` `#2d72d2` `#4c90f0` `#8abbff` | Interaction only — selection, focus, primary action, active state. **Never** a data encoding |
| **Green** | `#165a36` `#1c6e42` `#238551` `#32a467` `#72ca9b` | Confirmed / validated / AIS-correlated / low risk |
| **Orange** | `#77450d` `#935610` `#c87619` `#ec9a3c` `#fbb360` | Caution — degraded confidence, outside detection window, stale data |
| **Red** | `#8e292c` `#ac2f33` `#cd4246` `#e76a6e` `#fa999c` | Confirmed slick, dark vessel, top-ranked suspect, high risk |

Primary interaction blue is `blue3 #2d72d2`. Focus rings use `blue4 #4c90f0`.

### 2.3 Domain encodings — fixed, documented, never improvised

This is the part that makes the interface legible to a domain expert. Each encoding is a commitment.

| Entity | Colour | Note |
|---|---|---|
| **Confirmed oil slick** | `red3 #cd4246` @ 55% fill, `red4` 1.5 px stroke | The only saturated red fill on the map |
| **Rejected candidate** (look-alike) | `gray2 #738091` @ 25% fill, 1 px dashed stroke | Visible but clearly demoted — the analyst can still inspect it |
| **Low-confidence detection** | `orange3 #c87619` @ 40% fill | Wind gate or context penalty applied |
| **AIS-broadcasting vessel** | `gold4 #fbd065` | *Matches the SeaVision convention operators already know* |
| **Dark vessel** (SAR, no AIS) | `red4 #e76a6e`, pulsing halo | *Also the SeaVision convention. Use it — do not invent a new one* |
| **Suspect vessel track** | `blue4 #4c90f0`, weight by rank | Rank 1 brightest, fades to `blue1` by rank 5 |
| **Excluded vessel track** | `dark-gray5 #404854`, 0.5 px | Present in the audit view only |
| **Backward drift (hindcast)** | `violet` ramp `#5c255c → #d69fd6` | Backward = violet. Consistent everywhere |
| **Forward drift (forecast)** | `cerulean` ramp `#0c5174 → #68c1ee` | Forward = cerulean. Consistent everywhere |
| **Origin probability field** | `turquoise` sequential `#004d46 → #7ae1d8` | Density heatmap; **always shown with its own legend and confidence contours** |
| **Shoreline impact risk** | `vermilion` sequential `#96290d → #ff9980` | Coastal segments only |
| **Eco-sensitive zone** | `forest3 #1d7324` @ 20% fill, hatched | Static overlay |

**Backward is violet, forward is cerulean.** Memorise it. Consistency across map, timeline, charts and PDF dossier is what makes the product feel engineered rather than assembled.

### 2.4 Accessibility

All body text meets WCAG AA (4.5:1) against its background. `gray4 #abb3bf` on `dark-gray2 #252a31` is the minimum for sustained reading; `gray2` and below are for labels and non-essential chrome only.

**Never encode meaning by hue alone.** Every colour-coded state carries a second channel — an icon, a border style, a text label, or a position. Deuteranopia is common and red/green is our two most important states.

---

## 3. Typography

Palantir interfaces are dense and quiet. Small type, tight leading, heavy use of monospace for anything an operator might read aloud, copy, or cross-reference.

```
UI / body      Inter  (fallback: -apple-system, "Segoe UI", Roboto, sans-serif)
Numeric / ID   JetBrains Mono  (fallback: "SF Mono", Consolas, monospace)
```

| Role | Size / line-height | Weight | Notes |
|---|---|---|---|
| Panel title | 11 / 16 | 600 | **Uppercase, `letter-spacing: 0.06em`**, `gray3`. The signature Palantir panel header |
| Section label | 10 / 14 | 600 | Uppercase, `gray2` |
| Body | 13 / 18 | 400 | `gray4` |
| Body emphasis | 13 / 18 | 500 | `gray5` |
| Table cell | 12 / 16 | 400 | Tabular numerals on |
| **Identifiers** | 12 / 16 | 400 | **Mono.** MMSI, IMO, product ID, hash, timestamp |
| **Coordinates** | 12 / 16 | 400 | **Mono.** Always `12.4821° N, 74.9033° E` — six decimals, explicit hemisphere |
| Metric value | 20 / 24 | 500 | Mono, tabular |
| Metric unit | 11 / 16 | 400 | `gray2`, follows the value |
| Micro / caption | 10 / 14 | 400 | `gray2` |

**Rules that matter:**

- **Every identifier is monospace.** MMSI `419001234`, IMO `9123221`, SHA-256 prefixes, scene IDs. An operator reads these character by character; proportional fonts make that harder.
- **Every timestamp is monospace, ISO 8601, explicitly UTC**: `2026-05-25T06:40:00Z`. Never a locale format. Never an ambiguous timezone. If local time is shown, it is shown *in addition*, labelled `IST`.
- **Tabular numerals everywhere numbers stack vertically.** `font-variant-numeric: tabular-nums`.
- Sentence case for content. **UPPERCASE only for panel and section headers** — that specific move is a large part of the Palantir feel.

---

## 4. Density and layout

Density is the single most recognisable property of this class of interface. Consumer interfaces breathe; operator interfaces pack.

### 4.1 The spacing scale

4 px base. `2 · 4 · 6 · 8 · 12 · 16 · 24 · 32`. **Anything above 32 px is almost certainly wrong** — large whitespace reads as a marketing page.

| Element | Value |
|---|---|
| Panel padding | 12 px |
| Panel header height | 32 px |
| Table row height | **24 px** (compact), 28 px (default) |
| Control height | 24 px (small), 30 px (default) |
| Icon size | 14 px inline, 16 px standalone |
| Border radius | **2 px.** Everywhere. Never more |
| Border | 1 px solid `dark-gray4 #383e47` |

**No drop shadows except on true overlays** (popover, dialog, context menu), and then only `0 1px 4px rgba(17,20,24,0.4)`. Elevation is communicated by background value, not by shadow. Cards floating on a page with soft shadows and 12 px radii is the consumer-SaaS look we are explicitly avoiding.

### 4.2 The shell

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ▪ SAGARDRISHTI    Scene S1C_IW_20260525T0640Z ▾     ⬤ LIVE   14:22:07Z    │ 32px
├───┬───────────────────────────────────┬────────────────────────────────────┤
│   │                                   │  ANALYSIS                          │
│ N │                                   │ ┌────────────────────────────────┐ │
│ A │                                   │ │ DETECTION                      │ │
│ V │          MAP CANVAS               │ │  area      12.43 km²           │ │
│   │      (MapLibre + deck.gl)         │ │  bearing   247.3°              │ │
│ 48│                                   │ │  damping   8.4 dB              │ │
│ px│      the primary work surface     │ │  confidence 0.81  ▓▓▓▓▓▓▓░░    │ │
│   │      chrome floats over it        │ └────────────────────────────────┘ │
│   │                                   │ ┌────────────────────────────────┐ │
│   │                                   │ │ SUSPECTS              7 of 214 │ │
│   │                                   │ │  1 ▪ 419001234   0.71 ▓▓▓▓▓▓▓░ │ │
│   │                                   │ │  2 ▪ 563889000   0.44 ▓▓▓▓░░░░ │ │
│   │                                   │ │  3 ▪ 477995100   0.31 ▓▓▓░░░░░ │ │
│   │                                   │ └────────────────────────────────┘ │
│   ├───────────────────────────────────┤                          360-420px │
│   │ TIMELINE  ◀◀ ▶ ▶▶   T−24h ────●──────────── T_sar ──────► T+48h        │
└───┴───────────────────────────────────┴────────────────────────────────────┘
                                     96px
```

- **Left rail, 48 px, icon-only** with tooltips. Never a labelled sidebar — it steals canvas.
- **Right panel, 360–420 px, resizable, dockable.** Stacked collapsible sections, not tabs. An analyst needs detection *and* suspects visible simultaneously.
- **Bottom timeline, 96 px, always present.** This is a time-series product; hiding time in a modal would be a category error.
- **The map is the application.** Everything else floats over it. No page scroll, ever — the shell is exactly viewport height and individual panels scroll internally.

### 4.3 Panel anatomy

Every panel follows the same structure, without exception:

```
┌─────────────────────────────────────────┐
│ SECTION LABEL              [badge]  ⌄   │  32px, dark-gray3, 10px uppercase
├─────────────────────────────────────────┤
│  content, 12px padding                  │  dark-gray1
└─────────────────────────────────────────┘
```

Header carries: uppercase label (left), optional count/status badge (right), collapse chevron (far right). The badge is where `7 of 214` lives — the count that tells the story.

---

## 5. The map

The map is the product. It gets specific rules.

| Layer | Implementation |
|---|---|
| Basemap | MapLibre GL, **custom dark style** — desaturated to `dark-gray1/2`, labels `gray2`, no POIs, no roads inland. The sea must be the darkest thing on screen so slicks read instantly. **Vector tiles bundled locally** for offline mode |
| Bathymetry | Optional GEBCO contour underlay, `dark-gray4`, 15% opacity |
| SAR raster | TiTiler COG, greyscale, user-adjustable dB stretch |
| Slick polygons | deck.gl `PolygonLayer` — encodings per §2.3 |
| AIS tracks | deck.gl `PathLayer` + `TripsLayer` for animated playback |
| Drift particles | deck.gl `ScatterplotLayer`, GPU-instanced. **This is why we chose deck.gl over Leaflet** — 100k animated particles at 60 fps is the best moment in the demo |
| Origin probability | deck.gl `HeatmapLayer` or `ContourLayer` with explicit probability contours |

**Map rules:**

1. **Always show scale, north arrow, and the projection.** Non-negotiable in a geospatial forensic tool.
2. **Every layer has a legend.** A heatmap without a scale bar is a decoration, not evidence.
3. **Uncertainty is drawn, never implied.** Origin renders as a field with contours; if we ever draw a point, it carries an error ellipse.
4. **Hover reveals, click commits.** Hover shows a compact tooltip; click selects and populates the right panel. Never a modal for primary data.
5. **The time scrubber drives every layer simultaneously.** One clock. Layers that cannot honour it are visibly marked stale rather than silently wrong.

---

## 6. Component patterns

### 6.1 Confidence bar — the workhorse

Used for detection confidence and every suspect score. Appears dozens of times, so it must be tiny and instantly readable.

```
0.71 ▓▓▓▓▓▓▓░░░
```

Mono value, then an 80×6 px track. Fill colour by band: `≥0.7 red3` (high suspicion), `0.4–0.7 orange3`, `<0.4 gray2`. 2 px radius. **Always paired with the number** — a bar alone is not readable to three significant figures.

### 6.2 Per-factor explanation — the differentiator

The single most important component in the product. When an analyst opens a suspect, they see *why*:

```
┌── SUSPECT 1 · MMSI 419001234 ────────── 0.71 ──┐
│  VESSEL   MV EXAMPLE CARRIER · IMO 9123221      │
│           Tanker · 183 m · Flag: Panama         │
│                                                  │
│  CONTRIBUTING FACTORS                            │
│    drift consistency    +2.14  ▓▓▓▓▓▓▓▓▓░       │
│    course alignment     +1.87  ▓▓▓▓▓▓▓▓░░       │
│    AIS gap at t*        +1.32  ▓▓▓▓▓▓░░░░       │
│    speed anomaly        +0.94  ▓▓▓▓░░░░░░       │
│    night-time release   +0.41  ▓▓░░░░░░░░       │
│    off-lane distance    −0.22  ░░▒               │
│                                                  │
│  INFERRED RELEASE   2026-05-25T06:40:00Z ±50m   │
│  SLICK AGE          7.3 h  (5.9 – 8.8 h)        │
│                                                  │
│  [ Evidence dossier ]  [ Show drift ]  [ Track ] │
└──────────────────────────────────────────────────┘
```

Positive contributions extend right in `red3`; negative extend left in `blue3`. Sorted by magnitude. **Every factor is always listed, including the ones that argue for innocence.** Hiding exculpatory factors would undermine the entire legal-defensibility claim.

### 6.3 Rejection notice — the depth moment

When a detection is demoted, say exactly why. This is the 1:30 demo beat.

```
┌── CANDIDATE 4 · REJECTED ────────────────────────┐
│  confidence  0.62 → 0.19                          │
│                                                    │
│  ⚠  wind speed 1.6 m/s — below 2–12 m/s window    │
│  ⚠  chlorophyll-a anomaly +2.1σ — biogenic likely │
│  ⚠  recurring dark formation: 4 of last 12 scenes │
│                                                    │
│  Classification: LOOK-ALIKE (low-wind / biogenic)  │
└────────────────────────────────────────────────────┘
```

`orange3` icons, `gray4` body, mono numerics. Struck-through original confidence in `gray2`.

### 6.4 Filter cascade audit

```
TRAFFIC FILTER                        214 → 7
  reachability gate      214 → 46   −168
  timing gate             46 → 19    −27
  kinematic plausibility  19 → 11     −8
  drift-score floor       11 →  7     −4     [ expand ]
```

Expanding lists dropped vessels with per-vessel drop reasons. Directly answers the PS's "irrelevant traffic is to be filtered out" clause, and it is a strong live-demo moment.

### 6.5 Status and provenance strip

Persistent, bottom of the right panel. Small, quiet, always there:

```
scene  S1C_IW_GRDH_1SDV_20260525T064012  ·  sha256 a3f9c2e1…
model  segformer-b2 @ 40m/px  ·  weights 7d41b8a9…
force  CMEMS PHY_001_024 · ERA5 · GEBCO 2024
```

10 px mono, `gray2`. Nobody reads it until someone asks "how do I know this is real" — and then it is the answer.

---

## 7. Motion

Restraint. Operator tools that bounce feel unserious.

| Interaction | Duration | Easing |
|---|---|---|
| Hover / focus | 80 ms | `ease-out` |
| Panel expand / collapse | 140 ms | `cubic-bezier(0.4, 0, 0.2, 1)` |
| Map fly-to | 600 ms | `ease-in-out` |
| Drift playback | real-time scrubbed | linear |

**No bounce, no spring, no parallax, no scroll-triggered reveals.** The only elaborate motion in the product is drift particle animation, and that is *data*, not decoration.

Dark-vessel markers pulse at 1.4 s — the sole persistent animation in the chrome, justified because it is an alert state.

Respect `prefers-reduced-motion`: disable particle animation and replace it with a static time-slice the scrubber steps through.

---

## 8. Anti-patterns

Explicitly forbidden. Each is a way this could end up looking like a student project.

| Never | Because |
|---|---|
| Gradient-filled hero sections, glassmorphism, blur panels | Consumer aesthetics. This is a forensic tool |
| Border radius > 2 px | Instantly reads as a web app rather than an operator console |
| Emoji in the interface | (Fine in this repo's docs. Never in the product) |
| More than one accent hue per view | Colour is meaning here. A rainbow interface is an unreadable one |
| Rainbow / jet colourmaps for continuous data | Perceptually non-uniform and creates false boundaries. Use the sequential ramps in §2.3 |
| Full-page loading spinners | Show skeleton panels with real structure; long jobs get a progress bar with the actual stage name |
| Toast notifications for anything important | Ephemeral. Alerts go in the alert queue, where they persist |
| Hiding uncertainty to look confident | The single worst thing we could do, scientifically and for the pitch |
| Charts without axis labels or units | Every axis labelled, every unit stated, always |
| A point marker for the spill origin | The origin is a probability field. Drawing it as a pin is a lie |

---

## 9. Implementation notes

```
web/src/
  app/          shell, routing, layout, keyboard shortcuts
  components/   primitives — Panel, ConfidenceBar, FactorBars, MetricRow,
                Timeline, LayerLegend, StatusStrip
  features/     domain surfaces — detection/, drift/, attribution/,
                darkvessel/, evidence/
  lib/          api client, deck.gl layer factories, MapLibre style,
                formatters (coords, timestamps, identifiers)
  styles/       tokens.css (the §2 palette as CSS custom properties),
                tailwind theme extension
```

**Token discipline:** the palette in §2 lives in exactly one place — `web/src/styles/tokens.css` — as CSS custom properties, consumed by the Tailwind theme. **No hex literal appears anywhere else in the codebase.** A hardcoded `#cd4246` in a component is a review rejection, because the PDF dossier generator reads the same tokens and drift between screen and export would be a credibility failure.

**Formatters are centralised too.** `formatCoord`, `formatUTC`, `formatMMSI`, `formatHash` live in `lib/format.ts` and are the only way those values reach the screen. Consistent identifier rendering across map tooltip, table, panel and PDF is exactly the sort of detail that separates a product from a prototype.

---

## 10. Reference

- [Blueprint](https://blueprintjs.com) — Palantir's design system; source of every token in §2
- [deck.gl](https://deck.gl) — GPU layers
- [MapLibre GL JS](https://maplibre.org) — basemap
- SeaVision's AIS/dark-vessel colour convention — adopted deliberately in §2.3 so operators read our map without retraining
