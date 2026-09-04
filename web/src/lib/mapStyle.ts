import type { StyleSpecification } from "maplibre-gl";
import { tokenCSS } from "./tokens";

/**
 * Offline-safe basemap style.
 *
 * Deliberately references NO remote tile server, sprite or glyph URL.
 * Offline mode is a hard requirement (docs/OFFLINE_MODE.md) and CI rejects
 * CDN references — a single remote style URL produces a multi-second stall
 * on a dead network at the nodal centre and looks like a crash.
 *
 * Before the finale, bundle local vector tiles into web/public/tiles/ and
 * point `coastline` at them. Being able to do that without a vendor account
 * is a chief reason we chose MapLibre over a hosted provider.
 *
 * The sea must be the darkest thing on screen so slicks read instantly.
 */
/**
 * Built as a function, not a module-level constant, so the background is
 * read from the design tokens at map-creation time — after the stylesheet
 * has applied. Hardcoding the hex here would fork the palette, which is
 * exactly what tokens.css exists to prevent (and what CI rejects).
 */
export function makeDarkBaseStyle(): StyleSpecification {
  return {
    version: 8,
    name: "sagardrishti-dark",
    // No glyphs/sprite: we render no basemap labels. Data labels are DOM overlays.
    sources: {},
    layers: [
      {
        id: "sea",
        type: "background",
        paint: {
          "background-color": tokenCSS("--bg-map"),
        },
      },
    ],
  };
}

/** Arabian Sea off Kochi — the MSC ELSA 3 reference area. */
export const DEFAULT_VIEW = {
  longitude: 75.6,
  latitude: 9.75,
  zoom: 8.2,
  pitch: 0,
  bearing: 0,
} as const;
