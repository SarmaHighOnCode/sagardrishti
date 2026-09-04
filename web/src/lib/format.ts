/**
 * Centralised formatters — the ONLY way these values reach the screen.
 *
 * Consistent rendering of identifiers, coordinates and timestamps across
 * map tooltip, table, panel and the exported PDF dossier is what separates
 * a product from a prototype. An operator reads an MMSI character by
 * character and may read a position aloud over radio; ambiguity is a real
 * operational cost, not an aesthetic one.
 *
 * Spec: docs/DESIGN_SYSTEM.md §3
 */

/**
 * Coordinates: six decimals, explicit hemisphere, never a bare signed float.
 * "12.482100° N, 74.903300° E"
 */
export function formatCoord(lat: number, lon: number): string {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(6)}° ${ns}, ${Math.abs(lon).toFixed(6)}° ${ew}`;
}

export function formatLat(lat: number): string {
  return `${Math.abs(lat).toFixed(6)}° ${lat >= 0 ? "N" : "S"}`;
}

export function formatLon(lon: number): string {
  return `${Math.abs(lon).toFixed(6)}° ${lon >= 0 ? "E" : "W"}`;
}

/**
 * Timestamps: ISO 8601, UTC, explicit Z. Never a locale format — a demo
 * machine set to IST must not silently render a different time than the
 * dossier. If local time is shown it is shown IN ADDITION, and labelled.
 */
export function formatUTC(d: Date | string): string {
  const date = typeof d === "string" ? new Date(d) : d;
  if (Number.isNaN(date.getTime())) return "—";
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** "2026-05-25T06:40:00Z" → "06:40:00Z" for dense table cells. */
export function formatUTCTimeOnly(d: Date | string): string {
  const s = formatUTC(d);
  return s === "—" ? s : s.slice(11);
}

/** MMSI is a 9-character identifier, not a number. Never comma-grouped. */
export function formatMMSI(mmsi: string | number): string {
  return String(mmsi).padStart(9, "0");
}

/** IMO numbers are 7 digits. */
export function formatIMO(imo: string | number | null | undefined): string {
  return imo == null ? "—" : String(imo).padStart(7, "0");
}

/** Hashes are shown truncated with an ellipsis; full value goes in a tooltip. */
export function formatHash(hash: string, chars = 8): string {
  return hash.length <= chars ? hash : `${hash.slice(0, chars)}…`;
}

/**
 * Probabilities render to two decimals. We never round 0.71 to "71%" in
 * a context where it could be mistaken for a frequency — see the product
 * rule on calibrated probabilities in docs/SCORING_MODEL.md.
 */
export function formatProbability(p: number): string {
  return p.toFixed(2);
}

/**
 * An inferred value ALWAYS renders with its interval. Passing a value
 * without one is a schema violation upstream, and rendering a bare point
 * estimate here would hide it. Product principle 2.
 */
export function formatWithInterval(
  value: number,
  ci: readonly [number, number],
  unit: string,
  digits = 1,
): string {
  return `${value.toFixed(digits)} ${unit} (${ci[0].toFixed(digits)}–${ci[1].toFixed(digits)})`;
}

/** Bearings: three digits, degrees, no decimal. "247°" */
export function formatBearing(deg: number): string {
  return `${Math.round(((deg % 360) + 360) % 360)
    .toString()
    .padStart(3, "0")}°`;
}

export function formatArea(km2: number): string {
  return `${km2.toFixed(2)} km²`;
}

export function formatDecibels(db: number): string {
  return `${db.toFixed(1)} dB`;
}

export function formatSpeed(knots: number): string {
  return `${knots.toFixed(1)} kn`;
}

/** Durations in hours, for slick age and AIS gaps. */
export function formatHours(h: number): string {
  if (h < 1) return `${Math.round(h * 60)} min`;
  return `${h.toFixed(1)} h`;
}
