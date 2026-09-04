import { describe, it, expect } from "vitest";
import { pointInPolygon, type LngLat } from "./geo";

/**
 * Hit-testing is how an analyst selects a detection to inspect. If it is
 * subtly wrong they select the wrong slick and read the wrong evidence,
 * so the geometry is worth pinning down rather than eyeballing.
 */

// The rejected look-alike from the fixtures — a real shape we render.
const LOOK_ALIKE: LngLat[] = [
  [75.9, 10.05],
  [76.05, 10.02],
  [76.08, 9.94],
  [75.92, 9.96],
];

/**
 * An L-shape, to catch the classic ray-casting failure where a naive
 * implementation reports the notch as inside.
 *
 *   4 ┌───┐        solid: the full bottom band (y 0–2, x 0–4)
 *     │notch│ ▓▓   plus the right arm      (y 2–4, x 2–4)
 *   2 ├───┼───┤    notch (empty):           y 2–4, x 0–2
 *     │▓▓▓▓▓▓▓│
 *   0 └───────┘
 *     0   2   4
 */
const CONCAVE: LngLat[] = [
  [0, 0],
  [4, 0],
  [4, 4],
  [2, 4],
  [2, 2],
  [0, 2],
];

describe("pointInPolygon", () => {
  it("accepts a point inside a real slick polygon", () => {
    expect(pointInPolygon([75.9875, 9.9925], LOOK_ALIKE)).toBe(true);
  });

  it("rejects a point outside", () => {
    expect(pointInPolygon([70, 5], LOOK_ALIKE)).toBe(false);
  });

  it("rejects a point near but beyond the boundary", () => {
    // Just north of the top edge — this exact 40px-scale miss is what made
    // click-to-select appear broken during development.
    expect(pointInPolygon([75.99, 10.08], LOOK_ALIKE)).toBe(false);
  });

  it("handles a concave polygon's notch correctly", () => {
    expect(pointInPolygon([1, 1], CONCAVE)).toBe(true); // bottom band, left
    expect(pointInPolygon([3, 1], CONCAVE)).toBe(true); // bottom band, right
    expect(pointInPolygon([3, 3], CONCAVE)).toBe(true); // right arm
    expect(pointInPolygon([1, 3], CONCAVE)).toBe(false); // the notch
  });

  it("is not fooled by a point sharing a vertex's latitude", () => {
    // Horizontal rays through a vertex are the standard degenerate case.
    expect(pointInPolygon([10, 0], CONCAVE)).toBe(false);
    expect(pointInPolygon([-1, 2], CONCAVE)).toBe(false);
  });

  it("returns false for a degenerate polygon", () => {
    expect(pointInPolygon([1, 1], [])).toBe(false);
    expect(pointInPolygon([1, 1], [[0, 0]])).toBe(false);
  });
});
