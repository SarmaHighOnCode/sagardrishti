import { useEffect, useRef } from "react";
// maplibre-gl v6 has no default export — named imports only.
import {
  Map as MapLibreMap,
  ScaleControl,
  NavigationControl,
  type MapMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { PolygonLayer, PathLayer, ScatterplotLayer } from "@deck.gl/layers";

import { makeDarkBaseStyle, DEFAULT_VIEW } from "../../lib/mapStyle";
import { token } from "../../lib/tokens";
import { pointInPolygon } from "../../lib/geo";
import type { ShipPoint, SlickFeature, VesselTrack } from "../../lib/fixtures";

/**
 * The map is the application. Everything else floats over it.
 *
 * deck.gl rather than Leaflet because 100k animated drift particles at
 * 60fps is the best moment in the demo, and Leaflet cannot render it.
 *
 * Spec: docs/DESIGN_SYSTEM.md §5
 */
export function MapCanvas({
  slicks,
  tracks,
  ships,
  onSelectSlick,
}: {
  slicks: SlickFeature[];
  tracks: VesselTrack[];
  ships: ShipPoint[];
  onSelectSlick: (s: SlickFeature) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);

  // Hit-testing and layer updates read from refs, not closure-captured
  // props: the mount effect below runs once, but `slicks` changes every
  // time a query refetches, and a stale closure would keep testing
  // clicks against whatever data existed at mount.
  const slicksRef = useRef(slicks);
  useEffect(() => {
    slicksRef.current = slicks;
  }, [slicks]);

  useEffect(() => {
    if (!container.current || mapRef.current) return;

    const map = new MapLibreMap({
      container: container.current,
      style: makeDarkBaseStyle(),
      center: [DEFAULT_VIEW.longitude, DEFAULT_VIEW.latitude],
      zoom: DEFAULT_VIEW.zoom,
      attributionControl: false,
    });
    mapRef.current = map;

    // Scale and north are non-negotiable in a geospatial forensic tool.
    map.addControl(new ScaleControl({ unit: "nautical" }), "bottom-left");
    map.addControl(new NavigationControl({ showCompass: true }), "top-right");

    const overlay = new MapboxOverlay({
      interleaved: false,
      layers: buildLayers(slicksRef.current, tracks, ships),
    });
    overlayRef.current = overlay;
    map.addControl(overlay);

    // Hit-testing is done geographically against our own geometry rather
    // than through deck.gl's picking framebuffer — see lib/geo.ts for why.
    // "Hover reveals, click commits" — docs/DESIGN_SYSTEM.md §5.
    const slickAt = (e: MapMouseEvent): SlickFeature | undefined => {
      const { lng, lat } = e.lngLat;
      const current = slicksRef.current;
      // Reverse order so the topmost drawn polygon wins a hit.
      for (let i = current.length - 1; i >= 0; i--) {
        if (pointInPolygon([lng, lat], current[i].polygon)) {
          return current[i];
        }
      }
      return undefined;
    };

    const handleClick = (e: MapMouseEvent) => {
      const hit = slickAt(e);
      if (hit) onSelectSlick(hit);
    };

    const handleMove = (e: MapMouseEvent) => {
      map.getCanvas().style.cursor = slickAt(e) ? "pointer" : "";
    };

    map.on("click", handleClick);
    map.on("mousemove", handleMove);

    // The map must track its container. Without this the canvas is merely
    // CSS-stretched while maplibre's transform keeps the old dimensions —
    // the view appears wrongly zoomed and every screen/geo conversion is
    // off, which breaks hit-testing. Matters here because panels dock and
    // resize, not only when the window changes.
    const ro = new ResizeObserver(() => map.resize());
    ro.observe(container.current);

    return () => {
      ro.disconnect();
      map.off("click", handleClick);
      map.off("mousemove", handleMove);
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
    // Mount once. `slicks`/`tracks`/`ships` are read via refs / the effect
    // below rather than added here — remounting the whole map (and losing
    // pan/zoom state) every time a query refetches would be wrong.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onSelectSlick]);

  // Push new data into the existing overlay without touching the map.
  useEffect(() => {
    overlayRef.current?.setProps({ layers: buildLayers(slicks, tracks, ships) });
  }, [slicks, tracks, ships]);

  return (
    <div
      ref={container}
      style={{ position: "absolute", inset: 0, background: "var(--bg-map)" }}
    />
  );
}

function buildLayers(slicks: SlickFeature[], tracks: VesselTrack[], ships: ShipPoint[]) {
  return [
    // Slick polygons. Confirmed oil is the only saturated red fill on the map;
    // rejected candidates stay visible but clearly demoted so the analyst can
    // still inspect why they were rejected.
    new PolygonLayer<SlickFeature>({
      id: "slicks",
      data: slicks,
      getPolygon: (d) => d.polygon,
      filled: true,
      stroked: true,
      getFillColor: (d) =>
        d.classification === "oil"
          ? token("--slick-confirmed", 140)
          : token("--slick-rejected", 64),
      getLineColor: (d) =>
        d.classification === "oil"
          ? token("--slick-confirmed-stroke", 255)
          : token("--slick-rejected", 180),
      getLineWidth: (d) => (d.classification === "oil" ? 1.5 : 1),
      lineWidthUnits: "pixels",
      pickable: true,
    }),

    // Vessel tracks. Rank 1 brightest; excluded traffic present but recessive.
    new PathLayer<VesselTrack>({
      id: "tracks",
      data: tracks,
      getPath: (d) => d.path,
      getColor: (d) =>
        d.status === "suspect"
          ? token("--vessel-suspect", d.rank === 1 ? 255 : 150)
          : d.status === "ais"
            ? token("--vessel-ais", 170)
            : token("--vessel-excluded", 120),
      getWidth: (d) => (d.status === "suspect" && d.rank === 1 ? 2.5 : 1.5),
      widthUnits: "pixels",
      pickable: true,
    }),

    // Ship point targets. Colours follow the SeaVision convention operators
    // already know: AIS-broadcasting gold, uncorrelated (dark) red.
    new ScatterplotLayer<ShipPoint>({
      id: "ships",
      data: ships,
      getPosition: (d) => d.position,
      getFillColor: (d) =>
        d.dark ? token("--vessel-dark", 230) : token("--vessel-ais", 230),
      getRadius: (d) => (d.sizeBucket === "large" ? 5 : d.sizeBucket === "medium" ? 4 : 3),
      radiusUnits: "pixels",
      stroked: true,
      getLineColor: token("--black", 200),
      lineWidthUnits: "pixels",
      getLineWidth: 1,
      pickable: true,
    }),
  ];
}
