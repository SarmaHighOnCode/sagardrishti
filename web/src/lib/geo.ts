/**
 * Geographic hit-testing.
 *
 * We test against our own geometry in lon/lat rather than using deck.gl's
 * picking framebuffer. deck's MapboxOverlay in overlaid mode reported an
 * internal viewport of 300x150 (the default canvas size) while the real
 * canvas was 1172x772, so every pick coordinate fell outside its believed
 * bounds and returned null.
 *
 * Testing geometry we already own is exact rather than pixel-quantised,
 * independent of deck's version and render mode, and a pure function we
 * can unit-test. At our data volumes (tens of slicks, hundreds of tracks)
 * the linear scan is irrelevant to performance.
 */

export type LngLat = [number, number];

/**
 * Ray-casting point-in-polygon. Returns true if the point lies inside.
 *
 * Note: operates in planar lon/lat. Over a slick a few km across, well
 * away from the poles and the antimeridian, the error is far below the
 * resolution any of this is displayed at. Revisit if we ever need to
 * hit-test geometry spanning the 180th meridian.
 */
export function pointInPolygon(point: LngLat, polygon: readonly LngLat[]): boolean {
  const [x, y] = point;
  let inside = false;

  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];

    // Does the horizontal ray from the point cross this edge?
    const straddles = yi > y !== yj > y;
    if (straddles) {
      const xCross = ((xj - xi) * (y - yi)) / (yj - yi) + xi;
      if (x < xCross) inside = !inside;
    }
  }
  return inside;
}

/** Squared pixel distance — avoids a sqrt in hover hit-tests. */
export function distSq(a: { x: number; y: number }, b: { x: number; y: number }): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return dx * dx + dy * dy;
}
