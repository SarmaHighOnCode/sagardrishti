import { describe, expect, it } from "vitest";

import { detectionToSlickFeature, shipDetectionToShipPoint, tracksFromApi } from "./adapters";
import type { AisTrack, Detection, ShipDetection, Suspect } from "./apiTypes";

function detection(overrides: Partial<Detection> = {}): Detection {
  return {
    id: "det_synthetic_002",
    scene_id: "S1C_TEST",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [75.9, 10.05],
          [76.05, 10.02],
          [75.9, 10.05],
        ],
      ],
    },
    confidence: 0.19,
    confidence_raw: 0.62,
    classification: "look_alike",
    attributes: {
      area_km2: 5.1,
      major_axis_bearing_deg: 103.0,
      damping_ratio_db: 3.1,
      edge_sharpness: 0.22,
      thickness_class: "sheen",
    },
    penalties: [
      {
        check: "wind_window",
        delta: -0.28,
        reason: "wind speed 1.6 m/s below 2-12 m/s detection window",
        evidence: { wind_ms: 1.6 },
      },
    ],
    ...overrides,
  };
}

describe("detectionToSlickFeature", () => {
  it("maps snake_case attributes to the flat view shape", () => {
    const slick = detectionToSlickFeature(detection());
    expect(slick.areaKm2).toBe(5.1);
    expect(slick.bearingDeg).toBe(103.0);
    expect(slick.dampingDb).toBe(3.1);
    expect(slick.confidenceRaw).toBe(0.62);
  });

  it("passes the exterior ring through, closing duplicate intact", () => {
    const d = detection();
    const slick = detectionToSlickFeature(d);
    expect(slick.polygon).toEqual(d.geometry.coordinates[0]);
  });

  it("drops the machine-readable evidence but keeps the human reason", () => {
    const slick = detectionToSlickFeature(detection());
    expect(slick.penalties[0].reason).toMatch(/wind speed/);
    expect(slick.penalties[0]).not.toHaveProperty("evidence");
  });

  it("preserves an empty penalty log for a confirmed (non-rejected) detection", () => {
    const slick = detectionToSlickFeature(
      detection({ classification: "oil", confidence: 0.81, confidence_raw: 0.81, penalties: [] }),
    );
    expect(slick.penalties).toEqual([]);
    expect(slick.classification).toBe("oil");
  });
});

describe("shipDetectionToShipPoint", () => {
  it("maps a dark vessel through unchanged in substance", () => {
    const ship: ShipDetection = {
      id: "shp_3",
      position: { type: "Point", coordinates: [75.82, 9.55] },
      dark_vessel: true,
      size_bucket: "small",
      size_note: "small radar cross-section; many small craft are AIS-exempt",
      estimated_length_m: [12, 28],
      heading_deg: 118.0,
      ais_match: null,
    };
    const point = shipDetectionToShipPoint(ship);
    expect(point).toEqual({
      id: "shp_3",
      position: [75.82, 9.55],
      dark: true,
      sizeBucket: "small",
    });
  });
});

function suspect(overrides: Partial<Suspect> = {}): Suspect {
  return {
    rank: 1,
    mmsi: "419001234",
    vessel_name: "SYNTHETIC VESSEL A",
    vessel_type: "tanker",
    posterior: 0.71,
    calibrated: true,
    inferred_release_utc: "2026-05-25T06:40:00Z",
    inferred_release_ci_minutes: 50,
    slick_age_hours: 7.3,
    slick_age_ci: [5.9, 8.8],
    factors: [],
    data_quality: { records_used: 412, records_excluded: 7, exclusion_reasons: {} },
    ...overrides,
  };
}

function track(mmsi: string, overrides: Partial<AisTrack> = {}): AisTrack {
  return {
    mmsi,
    vessel_name: `VESSEL ${mmsi}`,
    points: [
      { time_utc: "2026-05-25T04:00:00Z", lat: 10.3, lon: 75.1, data_quality: "ok" },
      { time_utc: "2026-05-25T04:40:00Z", lat: 9.98, lon: 75.48, data_quality: "ok" },
    ],
    ...overrides,
  };
}

describe("tracksFromApi", () => {
  it("joins a track to its matching suspect by MMSI", () => {
    const [result] = tracksFromApi([track("419001234")], [suspect()]);
    expect(result.status).toBe("suspect");
    expect(result.rank).toBe(1);
    expect(result.posterior).toBe(0.71);
    expect(result.type).toBe("tanker");
  });

  it("converts AIS points to [lon, lat] path tuples in order", () => {
    const [result] = tracksFromApi([track("419001234")], []);
    expect(result.path).toEqual([
      [75.1, 10.3],
      [75.48, 9.98],
    ]);
  });

  it("marks a track with no matching suspect as ordinary AIS traffic, not excluded", () => {
    // Absence of a suspect record means "not ranked", never "cleared" or
    // "excluded" — those would assert a finding the data doesn't support.
    const [result] = tracksFromApi([track("477995100")], [suspect()]);
    expect(result.status).toBe("ais");
    expect(result.rank).toBeUndefined();
    expect(result.posterior).toBeUndefined();
  });

  it("falls back to 'unknown' type when there is no suspect record to source it from", () => {
    const [result] = tracksFromApi([track("477995100")], []);
    expect(result.type).toBe("unknown");
  });

  it("handles multiple tracks independently", () => {
    const results = tracksFromApi(
      [track("419001234"), track("477995100")],
      [suspect({ mmsi: "419001234", rank: 1 })],
    );
    expect(results).toHaveLength(2);
    expect(results.find((r) => r.mmsi === "419001234")?.status).toBe("suspect");
    expect(results.find((r) => r.mmsi === "477995100")?.status).toBe("ais");
  });

  it("uses the MMSI itself as a name fallback when vessel_name is absent", () => {
    const [result] = tracksFromApi([track("999999999", { vessel_name: null })], []);
    expect(result.name).toBe("999999999");
  });
});
