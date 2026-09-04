/**
 * Bridge from CSS custom properties to the RGB arrays deck.gl needs.
 *
 * deck.gl paint properties cannot read CSS variables, and hardcoding hex
 * here would fork the palette — exactly what tokens.css exists to prevent,
 * and what CI rejects. So we read the computed value at runtime instead.
 * One source of colour, honoured by both DOM and WebGL layers.
 *
 * Spec: docs/DESIGN_SYSTEM.md §9 (token discipline)
 */

export type RGBA = [number, number, number, number];

const cache = new Map<string, RGBA>();

function parseHex(hex: string): [number, number, number] {
  const h = hex.trim().replace("#", "");
  const full =
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h;
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ];
}

/**
 * Read a design token as an RGBA array.
 * @param name CSS custom property, e.g. "--slick-confirmed"
 * @param alpha 0–255
 */
export function token(name: string, alpha = 255): RGBA {
  const key = `${name}:${alpha}`;
  const hit = cache.get(key);
  if (hit) return hit;

  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();

  if (!raw) {
    // Loud failure: a missing token is a bug in tokens.css, not something
    // to paper over with a default colour that would silently look fine.
    console.error(`[tokens] undefined design token: ${name}`);
    const fallback: RGBA = [255, 0, 255, alpha];
    return fallback;
  }

  const [r, g, b] = parseHex(raw);
  const rgba: RGBA = [r, g, b, alpha];
  cache.set(key, rgba);
  return rgba;
}

/**
 * Read a design token as its raw CSS string, as authored in tokens.css.
 *
 * For consumers that need a colour string rather than an RGBA array —
 * notably MapLibre style specifications, whose paint properties cannot
 * resolve CSS custom properties.
 */
export function tokenCSS(name: string): string {
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  if (!raw) {
    console.error(`[tokens] undefined design token: ${name}`);
    // Named colour, not a hex literal: the palette lives in tokens.css
    // and CI rejects hex anywhere else. Magenta is deliberately jarring.
    return "magenta";
  }
  return raw;
}

/** Clear the cache — call if the theme ever changes at runtime. */
export function resetTokenCache(): void {
  cache.clear();
}
