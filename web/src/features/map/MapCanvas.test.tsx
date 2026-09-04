// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { MapCanvas } from "./MapCanvas";
import { SAMPLE_SLICKS } from "../../lib/fixtures";
import { DEFAULT_VIEW } from "../../lib/mapStyle";

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

    resize() {}

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

class FakeResizeObserver {
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

  it("removes the map and detaches handlers on unmount", () => {
    const { unmount } = render(<MapCanvas onSelectSlick={vi.fn()} />);
    const map = getLastMap();
    unmount();
    expect(map?.removed).toBe(true);
    expect(handlers.click ?? []).toHaveLength(0);
    expect(handlers.mousemove ?? []).toHaveLength(0);
  });
});
