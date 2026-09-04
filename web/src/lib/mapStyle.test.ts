// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { makeDarkBaseStyle, DEFAULT_VIEW } from "./mapStyle";
import { resetTokenCache } from "./tokens";

function seaBackgroundColor(
  style: ReturnType<typeof makeDarkBaseStyle>,
): string | undefined {
  const layer = style.layers[0];
  return layer.type === "background"
    ? (layer.paint?.["background-color"] as string | undefined)
    : undefined;
}

describe("makeDarkBaseStyle", () => {
  afterEach(() => {
    resetTokenCache();
    document.documentElement.style.cssText = "";
    vi.restoreAllMocks();
  });

  it("references no remote sources, sprite or glyph URLs", () => {
    document.documentElement.style.setProperty("--bg-map", "#0a0e14");
    const style = makeDarkBaseStyle();
    expect(style.sources).toEqual({});
    expect(style.sprite).toBeUndefined();
    expect(style.glyphs).toBeUndefined();
  });

  it("paints the sea background from the --bg-map design token", () => {
    document.documentElement.style.setProperty("--bg-map", "#0a0e14");
    const style = makeDarkBaseStyle();
    expect(style.layers).toHaveLength(1);
    expect(style.layers[0]).toMatchObject({
      id: "sea",
      type: "background",
      paint: { "background-color": "#0a0e14" },
    });
  });

  it("re-reads the token on every call rather than caching a stale style", () => {
    document.documentElement.style.setProperty("--bg-map", "#111111");
    const first = makeDarkBaseStyle();
    document.documentElement.style.setProperty("--bg-map", "#222222");
    const second = makeDarkBaseStyle();
    expect(seaBackgroundColor(first)).toBe("#111111");
    expect(seaBackgroundColor(second)).toBe("#222222");
  });

  it("falls back to magenta and logs when --bg-map is undefined", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const style = makeDarkBaseStyle();
    expect(seaBackgroundColor(style)).toBe("magenta");
    expect(spy).toHaveBeenCalledWith(
      "[tokens] undefined design token: --bg-map",
    );
  });
});

describe("DEFAULT_VIEW", () => {
  it("centres on the Arabian Sea off Kochi with a flat, unrotated camera", () => {
    expect(DEFAULT_VIEW).toEqual({
      longitude: 75.6,
      latitude: 9.75,
      zoom: 8.2,
      pitch: 0,
      bearing: 0,
    });
  });
});
