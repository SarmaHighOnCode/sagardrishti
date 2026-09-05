// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { token, tokenCSS, resetTokenCache } from "./tokens";

function setToken(name: string, value: string): void {
  document.documentElement.style.setProperty(name, value);
}

describe("token", () => {
  beforeEach(() => {
    resetTokenCache();
    document.documentElement.style.cssText = "";
  });

  it("parses a 6-digit hex token into an RGBA array", () => {
    setToken("--slick-confirmed", "#ff8800");
    expect(token("--slick-confirmed")).toEqual([255, 136, 0, 255]);
  });

  it("applies the default alpha of 255 when none is given", () => {
    setToken("--foo", "#000000");
    expect(token("--foo")[3]).toBe(255);
  });

  it("applies a custom alpha", () => {
    setToken("--foo", "#000000");
    expect(token("--foo", 128)).toEqual([0, 0, 0, 128]);
  });

  it("expands a 3-digit hex shorthand", () => {
    setToken("--foo", "#0f0");
    expect(token("--foo")).toEqual([0, 255, 0, 255]);
  });

  it("caches by name and alpha so repeated reads return the same array", () => {
    setToken("--foo", "#123456");
    const first = token("--foo");
    setToken("--foo", "#654321");
    const second = token("--foo");
    expect(second).toBe(first);
  });

  it("treats different alpha values as separate cache entries", () => {
    setToken("--foo", "#123456");
    const a = token("--foo", 255);
    const b = token("--foo", 100);
    expect(a).not.toBe(b);
    expect(a[3]).toBe(255);
    expect(b[3]).toBe(100);
  });

  it("logs an error and returns magenta fallback when the token is undefined", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(token("--does-not-exist")).toEqual([255, 0, 255, 255]);
    expect(spy).toHaveBeenCalledWith(
      "[tokens] undefined design token: --does-not-exist",
    );
    spy.mockRestore();
  });

  it("resetTokenCache forces a re-read of the current computed value", () => {
    setToken("--foo", "#111111");
    const before = token("--foo");
    resetTokenCache();
    setToken("--foo", "#222222");
    const after = token("--foo");
    expect(after).not.toEqual(before);
    expect(after).toEqual([34, 34, 34, 255]);
  });
});

describe("tokenCSS", () => {
  beforeEach(() => {
    document.documentElement.style.cssText = "";
  });

  it("returns the raw, trimmed CSS string as authored", () => {
    setToken("--bg-map", "  #0a0e14  ");
    expect(tokenCSS("--bg-map")).toBe("#0a0e14");
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("logs an error and returns 'magenta' when the token is undefined", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(tokenCSS("--does-not-exist")).toBe("magenta");
    expect(spy).toHaveBeenCalledWith(
      "[tokens] undefined design token: --does-not-exist",
    );
  });
});
