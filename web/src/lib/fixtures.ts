/**
 * ============================ SYNTHETIC ============================
 * Placeholder data for interface development ONLY.
 *
 * None of this is a real detection, a real vessel, or a real assessment.
 * Vessel identities are invented. It exists so the console can be built
 * and reviewed before the pipeline produces real output, and it must be
 * deleted the moment the API serves live data.
 *
 * Never screenshot this for a slide without the SYNTHETIC label visible.
 * See SECURITY.md — a document naming a real vessel as a pollution
 * suspect is a different artefact from raw position data.
 * ===================================================================
 */

export const IS_SYNTHETIC = true;

export interface SlickFeature {
  id: string;
  polygon: [number, number][];
  confidence: number;
  confidenceRaw: number;
  classification: "oil" | "look_alike";
  areaKm2: number;
  bearingDeg: number;
  dampingDb: number;
  penalties: { check: string; delta: number; reason: string }[];
}

export const SAMPLE_SLICKS: SlickFeature[] = [
  {
    id: "det_synthetic_001",
    polygon: [
      [75.42, 9.88],
      [75.61, 9.79],
      [75.74, 9.68],
      [75.7, 9.62],
      [75.55, 9.71],
      [75.38, 9.83],
    ],
    confidence: 0.81,
    confidenceRaw: 0.81,
    classification: "oil",
    areaKm2: 12.43,
    bearingDeg: 247.3,
    dampingDb: 8.4,
    penalties: [],
  },
  {
    id: "det_synthetic_002",
    polygon: [
      [75.9, 10.05],
      [76.05, 10.02],
      [76.08, 9.94],
      [75.92, 9.96],
    ],
    confidence: 0.19,
    confidenceRaw: 0.62,
    classification: "look_alike",
    areaKm2: 5.1,
    bearingDeg: 103.0,
    dampingDb: 3.1,
    // The 1:50 demo beat — a rejection with itemised reasons.
    penalties: [
      {
        check: "wind_window",
        delta: -0.28,
        reason: "wind speed 1.6 m/s below 2–12 m/s detection window",
      },
      {
        check: "chlorophyll_anomaly",
        delta: -0.09,
        reason: "chlorophyll-a anomaly +2.1σ, biogenic film likely",
      },
      {
        check: "recurrence",
        delta: -0.06,
        reason: "dark formation at this location in 4 of last 12 scenes",
      },
    ],
  },
];

export interface VesselTrack {
  mmsi: string;
  name: string;
  type: string;
  path: [number, number][];
  status: "suspect" | "ais" | "excluded";
  rank?: number;
  posterior?: number;
}

export const SAMPLE_TRACKS: VesselTrack[] = [
  {
    mmsi: "419001234",
    name: "SYNTHETIC VESSEL A",
    type: "tanker",
    status: "suspect",
    rank: 1,
    posterior: 0.71,
    path: [
      [75.1, 10.3],
      [75.3, 10.12],
      [75.48, 9.98],
      [75.66, 9.84],
      [75.88, 9.7],
    ],
  },
  {
    mmsi: "563889000",
    name: "SYNTHETIC VESSEL B",
    type: "container",
    status: "suspect",
    rank: 2,
    posterior: 0.44,
    path: [
      [75.2, 9.5],
      [75.45, 9.6],
      [75.7, 9.72],
      [75.95, 9.85],
    ],
  },
  {
    mmsi: "477995100",
    name: "SYNTHETIC VESSEL C",
    type: "bulk carrier",
    status: "ais",
    path: [
      [75.0, 9.9],
      [75.25, 9.95],
      [75.5, 10.02],
    ],
  },
];

export interface ShipPoint {
  id: string;
  position: [number, number];
  dark: boolean;
  sizeBucket: "small" | "medium" | "large";
}

export const SAMPLE_SHIPS: ShipPoint[] = [
  { id: "shp_1", position: [75.66, 9.84], dark: false, sizeBucket: "large" },
  { id: "shp_2", position: [75.5, 10.02], dark: false, sizeBucket: "medium" },
  // Dark vessel — small craft, likely AIS-exempt. Shown as context, not accusation.
  { id: "shp_3", position: [75.82, 9.55], dark: true, sizeBucket: "small" },
];
