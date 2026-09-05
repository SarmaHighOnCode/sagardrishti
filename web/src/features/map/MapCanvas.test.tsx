// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { MapCanvas } from "./MapCanvas";
import { SAMPLE_SLICKS, SAMPLE_TRACKS, SAMPLE_SHIPS } from "../../lib/fixtures";
import type { VesselTrack } from "../../lib/fixtures";
import { DEFAULT_VIEW } from "../../lib/mapStyle";

const { tokenCalls } = vi.hoisted(() => ({ tokenCalls: [] as [string, number | undefined][] }));

vi.mock("../../lib/tokens", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../lib/tokens")>();
  return {
    ...actual,
    token: (name: string, alpha?: number) => {
      tokenCalls.push([name, alpha]);
      return actual.token(name, alpha);
    },
  };
});

const { controls, handlers, getLastMap, FakeMap } = vi.hoisted(() => {
  type Handler = (e: unknown) => void;

  const controls: unknown[] = [];
  const handlers: Record<string, Handler[]> = {};
  let lastMapInstance: InstanceType<typeof FakeMap> | undefined;

  class FakeMap {
    options: Record<string, unknown>;
    canvas = { style: { cursor: "" } };
    removed = false;

    constructor(options: Record<string, unknown>) {
      this.options = options;
      // eslint-disable-next-line @typescript-eslint/no-this-alias -- capture the instance the component just created for assertions
      lastMapInstance = this;
    }

    addControl(control: unknown) {
      controls.push(control);
    }

    on(event: string, handler: Handler) {
      handlers[event] = [...(handlers[event] ?? []), handler];
    }

    off(event: string, handler: Handler) {
      handlers[event] = (handlers[event] ?? []).filter((h) => h !== handler);
    }

    getCanvas() {
      return this.canvas;
    }

    resizeCalls = 0;
    resize() {
      this.resizeCalls++;
    }

    remove() {
      this.removed = true;
    }
  }

  return { controls, handlers, getLastMap: () => lastMapInstance, FakeMap };
});

vi.mock("maplibre-gl", () => ({
  Map: FakeMap,
  ScaleControl: class ScaleControl {},
  NavigationControl: class NavigationControl {},
}));

vi.mock("maplibre-gl/dist/maplibre-gl.css", () => ({}));

vi.mock("@deck.gl/mapbox", () => ({
  MapboxOverlay: class MapboxOverlay {
    constructor(public props: Record<string, unknown>) {}
  },
}));

vi.mock("@deck.gl/layers", () => ({
  PolygonLayer: class PolygonLayer {
    constructor(public props: Record<string, unknown>) {}
  },
  PathLayer: class PathLayer {
    constructor(public props: Record<string, unknown>) {}
  },
  ScatterplotLayer: class ScatterplotLayer {
    constructor(public props: Record<string, unknown>) {}
  },
}));

let lastResizeCb: (() => void) | undefined;
class FakeResizeObserver {
  constructor(cb: () => void) {
    lastResizeCb = cb;
  }
  observe() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", FakeResizeObserver);

function fire(event: string, payload: unknown) {
  for (const h of handlers[event] ?? []) h(payload);
}

/** Average of vertices — safely interior for the roughly-convex fixture shapes. */
function centroid(polygon: readonly [number, number][]): [number, number] {
  const [sx, sy] = polygon.reduce(
    ([ax, ay], [x, y]) => [ax + x, ay + y],
    [0, 0],
  );
  return [sx / polygon.length, sy / polygon.length];
}

afterEach(() => {
  cleanup();
  controls.length = 0;
  for (const key of Object.keys(handlers)) delete handlers[key];
});

describe("MapCanvas", () => {
  it("creates the map centered on DEFAULT_VIEW with no attribution control", () => {
    render(<MapCanvas onSelectSlick={vi.fn()} />);
    const map = getLastMap();
    expect(map?.options.attributionControl).toBe(false);
    expect(map?.options.center).toEqual([DEFAULT_VIEW.longitude, DEFAULT_VIEW.latitude]);
    expect(map?.options.zoom).toBe(DEFAULT_VIEW.zoom);
  });

  it("registers scale, navigation, and a deck.gl overlay control", () => {
    render(<MapCanvas onSelectSlick={vi.fn()} />);
    expect(controls.length).toBe(3);
  });

  it("calls onSelectSlick when a click lands inside a slick polygon", () => {
    const onSelectSlick = vi.fn();
    render(<MapCanvas onSelectSlick={onSelectSlick} />);

    const [lng, lat] = centroid(SAMPLE_SLICKS[0].polygon);
    fire("click", { lngLat: { lng, lat } });

    expect(onSelectSlick).toHaveBeenCalledTimes(1);
    expect(onSelectSlick.mock.calls[0][0].id).toBe(SAMPLE_SLICKS[0].id);
  });

  it("does not call onSelectSlick when a click misses every polygon", () => {
    const onSelectSlick = vi.fn();
    render(<MapCanvas onSelectSlick={onSelectSlick} />);

    fire("click", { lngLat: { lng: -999, lat: -999 } });

    expect(onSelectSlick).not.toHaveBeenCalled();
  });

  it("sets a pointer cursor on hover over a slick and clears it off-target", () => {
    render(<MapCanvas onSelectSlick={vi.fn()} />);

    const [lng, lat] = centroid(SAMPLE_SLICKS[0].polygon);
    fire("mousemove", { lngLat: { lng, lat } });
    expect(getLastMap()?.canvas.style.cursor).toBe("pointer");

    fire("mousemove", { lngLat: { lng: -999, lat: -999 } });
    expect(getLastMap()?.canvas.style.cursor).toBe("");
  });

  it("resizes the map when the container's ResizeObserver fires", () => {
    render(<MapCanvas onSelectSlick={vi.fn()} />);
    const map = getLastMap();
    expect(map?.resizeCalls).toBe(0);

    lastResizeCb?.();

    expect(map?.resizeCalls).toBe(1);
  });

  it("removes the map and detaches handlers on unmount", () => {
    const { unmount } = render(<MapCanvas onSelectSlick={vi.fn()} />);
    const map = getLastMap();
    unmount();
    expect(map?.removed).toBe(true);
    expect(handlers.click ?? []).toHaveLength(0);
    expect(handlers.mousemove ?? []).toHaveLength(0);
  });
});

interface FakeLayer {
  props: Record<string, unknown> & { id: string };
}

interface FakeOverlay {
  props: { layers: FakeLayer[] };
}

function isFakeOverlay(c: unknown): c is FakeOverlay {
  return (
    typeof c === "object" &&
    c !== null &&
    "props" in c &&
    Array.isArray((c as { props: { layers?: unknown } }).props.layers)
  );
}

describe("buildLayers (deck.gl accessor logic)", () => {
  function layerById(id: string) {
    const overlay = controls.find(isFakeOverlay)!;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- deck.gl accessor props are heterogeneous per layer type
    return overlay.props.layers.find((l) => l.props.id === id)!.props as Record<string, any>;
  }

  it("colours the slicks layer by classification: confirmed oil vs. rejected look-alike", () => {
    render(<MapCanvas onSelectSlick={vi.fn()} />);
    const slicks = layerById("slicks");
    const [oil, lookAlike] = SAMPLE_SLICKS;
    expect(oil.classification).toBe("oil");
    expect(lookAlike.classification).toBe("look_alike");

    expect(slicks.getPolygon(oil)).toBe(oil.polygon);

    expect(slicks.getLineWidth(oil)).toBe(1.5);
    expect(slicks.getLineWidth(lookAlike)).toBe(1);

    tokenCalls.length = 0;
    slicks.getFillColor(oil);
    slicks.getFillColor(lookAlike);
    slicks.getLineColor(oil);
    slicks.getLineColor(lookAlike);
    expect(tokenCalls).toEqual([
      ["--slick-confirmed", 140],
      ["--slick-rejected", 64],
      ["--slick-confirmed-stroke", 255],
      ["--slick-rejected", 180],
    ]);
  });

  it("colours and widens the tracks layer by suspect rank vs. AIS vs. excluded status", () => {
    render(<MapCanvas onSelectSlick={vi.fn()} />);
    const tracks = layerById("tracks");
    const rank1 = SAMPLE_TRACKS.find((t) => t.status === "suspect" && t.rank === 1)!;
    const rank2 = SAMPLE_TRACKS.find((t) => t.status === "suspect" && t.rank === 2)!;
    const ais = SAMPLE_TRACKS.find((t) => t.status === "ais")!;
    const excluded: VesselTrack = { ...ais, status: "excluded", rank: undefined };

    expect(tracks.getPath(rank1)).toBe(rank1.path);
    expect(tracks.getWidth(rank1)).toBe(2.5);
    expect(tracks.getWidth(rank2)).toBe(1.5);
    expect(tracks.getWidth(ais)).toBe(1.5);

    tokenCalls.length = 0;
    tracks.getColor(rank1);
    tracks.getColor(rank2);
    tracks.getColor(ais);
    tracks.getColor(excluded);
    expect(tokenCalls).toEqual([
      ["--vessel-suspect", 255],
      ["--vessel-suspect", 150],
      ["--vessel-ais", 170],
      ["--vessel-excluded", 120],
    ]);
  });

  it("colours the ships layer by dark-vessel flag and sizes by size bucket", () => {
    render(<MapCanvas onSelectSlick={vi.fn()} />);
    const ships = layerById("ships");
    const dark = SAMPLE_SHIPS.find((s) => s.dark)!;
    const lit = SAMPLE_SHIPS.find((s) => !s.dark)!;

    expect(ships.getPosition(dark)).toBe(dark.position);

    tokenCalls.length = 0;
    ships.getFillColor(dark);
    ships.getFillColor(lit);
    expect(tokenCalls).toEqual([
      ["--vessel-dark", 230],
      ["--vessel-ais", 230],
    ]);

    expect(ships.getRadius({ sizeBucket: "large" })).toBe(5);
    expect(ships.getRadius({ sizeBucket: "medium" })).toBe(4);
    expect(ships.getRadius({ sizeBucket: "small" })).toBe(3);
  });
});
