/**
 * Wire types (`apiTypes.ts`) → view types (`fixtures.ts`).
 *
 * The map and analysis panel components were built against small,
 * render-shaped types (`SlickFeature`, `VesselTrack`, `ShipPoint`) before
 * the API existed. Rather than rewrite every component to consume the
 * wire shape directly, this module is the one place that translates
 * between them — components stay decoupled from the contract, and the
 * translation is a pure function anyone can unit test without a network.
 *
 * `VesselTrack` in particular combines two API resources: a suspect's
 * rank/posterior (from `GET /detections/{id}/suspects`) and a vessel's
 * physical path (from `GET /ais/tracks`). `tracksFromApi` is the join.
 */

import type { AisTrack, Detection, ShipDetection, Suspect } from "./apiTypes";
import type { ShipPoint, SlickFeature, VesselTrack } from "./fixtures";

export function detectionToSlickFeature(d: Detection): SlickFeature {
  return {
    id: d.id,
    // The exterior ring. GeoJSON repeats the first vertex as the last to
    // close the ring; deck.gl's PolygonLayer tolerates the duplicate
    // fine, so no special-casing is needed here.
    polygon: d.geometry.coordinates[0],
    confidence: d.confidence,
    confidenceRaw: d.confidence_raw,
    classification: d.classification,
    areaKm2: d.attributes.area_km2,
    bearingDeg: d.attributes.major_axis_bearing_deg,
    dampingDb: d.attributes.damping_ratio_db,
    penalties: d.penalties.map((p) => ({ check: p.check, delta: p.delta, reason: p.reason })),
  };
}

export function shipDetectionToShipPoint(s: ShipDetection): ShipPoint {
  return {
    id: s.id,
    position: s.position.coordinates,
    dark: s.dark_vessel,
    sizeBucket: s.size_bucket,
  };
}

/**
 * Join AIS tracks with suspect rankings into the combined view model the
 * map layer expects.
 *
 * A track whose MMSI has no matching suspect is rendered with status
 * "ais" — ordinary traffic, not a candidate. This is a deliberate
 * default: absence of a suspect record means "not ranked", never
 * "excluded" or "cleared". Rendering it as "excluded" would assert a
 * finding the data doesn't support.
 */
export function tracksFromApi(tracks: AisTrack[], suspects: Suspect[]): VesselTrack[] {
  const byMmsi = new Map(suspects.map((s) => [s.mmsi, s]));

  return tracks.map((t) => {
    const suspect = byMmsi.get(t.mmsi);
    return {
      mmsi: t.mmsi,
      name: t.vessel_name ?? t.mmsi,
      type: suspect?.vessel_type ?? "unknown",
      path: t.points.map((p) => [p.lon, p.lat] as [number, number]),
      status: suspect ? "suspect" : "ais",
      rank: suspect?.rank,
      posterior: suspect?.posterior,
    };
  });
}
