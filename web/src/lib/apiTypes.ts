/**
 * TypeScript mirrors of `services/api/app/schemas.py`.
 *
 * These ARE docs/api/API_CONTRACT.md on the client side. The contract
 * freezes 15 October; after that a field rename here is a breaking change
 * needing the integration lead's sign-off, same as on the server.
 *
 * Kept hand-written rather than generated from the OpenAPI schema. A
 * generator is the right answer once the contract stops moving, but today
 * it would add a build step and a checked-in artefact to a surface small
 * enough to read in one sitting — and hand-writing it forced an actual
 * read of the server models, which is how the naming mismatch noted below
 * was caught in the first place.
 *
 * WHEN YOU CHANGE THESE: change `schemas.py` in the same commit, or write
 * down why they now legitimately differ. Silent drift between the two is
 * the specific failure this comment exists to prevent — the API's
 * `BaselineGapProfile` once independently invented `typical_gap_minutes_p50`
 * against a database column called `median_gap_seconds`, and nothing
 * failed loudly.
 */

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

/** `[longitude, latitude]`, WGS84. Longitude first — GeoJSON order. */
export type LonLat = [number, number];

export interface GeoPoint {
  type: "Point";
  coordinates: LonLat;
}

export interface GeoPolygon {
  type: "Polygon";
  /** Array of linear rings; the first is the exterior. */
  coordinates: LonLat[][];
}

/** RFC 7807. Every non-2xx response from this API has this shape. */
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
}

/** List envelope. `next_cursor` is null when there are no further pages. */
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}

// ---------------------------------------------------------------------------
// Scenes
// ---------------------------------------------------------------------------

export type SceneStatus = "ingested" | "preprocessing" | "analysed";

export interface Scene {
  id: string;
  sensor: string;
  /** ISO 8601 UTC with a literal trailing `Z`. Never an offset. */
  acquired_utc: string;
  footprint: GeoPolygon;
  product_hash: string;
  status: SceneStatus;
}

// ---------------------------------------------------------------------------
// Detections
// ---------------------------------------------------------------------------

export type Classification = "oil" | "look_alike";
export type ThicknessClass = "sheen" | "thick_film";

/**
 * One Stage C context check that reduced a detection's confidence.
 *
 * `reason` is rendered directly to the analyst — it is the content of the
 * rejection panel, the demo's strongest 30 seconds. `evidence` is the
 * machine-readable backing the dossier cites.
 */
export interface Penalty {
  check: string;
  delta: number;
  reason: string;
  evidence?: Record<string, unknown> | null;
}

export interface DetectionAttributes {
  area_km2: number;
  major_axis_bearing_deg: number;
  damping_ratio_db: number;
  edge_sharpness: number;
  thickness_class: ThicknessClass;
}

export interface Detection {
  id: string;
  scene_id: string;
  geometry: GeoPolygon;
  /** Post-Stage-C confidence. */
  confidence: number;
  /** Pre-filter value. The UI strikes this through rather than hiding it. */
  confidence_raw: number;
  classification: Classification;
  attributes: DetectionAttributes;
  penalties: Penalty[];
}

// ---------------------------------------------------------------------------
// Suspects
// ---------------------------------------------------------------------------

export type FactorConfidence = "high" | "medium" | "low";

export interface SuspectFactor {
  name: string;
  value: number;
  weight: number;
  /**
   * weight × value. **May be negative** — exculpatory factors are
   * first-class and must never be filtered out of the UI. See
   * docs/SCORING_MODEL.md §7.
   */
  contribution: number;
  confidence: FactorConfidence;
  /**
   * Present where the bare value would mislead — notably
   * `ais_gap_anomaly`, where a number means nothing without knowing it
   * was measured against this vessel's own baseline.
   */
  note?: string | null;
}

export interface DataQualitySummary {
  records_used: number;
  records_excluded: number;
  /** `{ "impossible_speed": 5, "null_island": 2 }` */
  exclusion_reasons: Record<string, number>;
}

export interface Suspect {
  rank: number;
  mmsi: string;
  imo?: string | null;
  vessel_name: string;
  vessel_type: string;
  posterior: number;
  /** False means the score is ordinal only — do not present it as a probability. */
  calibrated: boolean;

  // Always present as a pair. A release time without its interval is a
  // schema violation server-side, so the client can rely on both.
  inferred_release_utc: string;
  inferred_release_ci_minutes: number;

  // Likewise. Age is INFERRED from the drift solve, never measured.
  slick_age_hours: number;
  slick_age_ci: [number, number];

  factors: SuspectFactor[];
  data_quality: DataQualitySummary;
}

// ---------------------------------------------------------------------------
// AIS and ships
// ---------------------------------------------------------------------------

export type AisDataQuality = "ok" | "unreliable";

export interface AisTrackPoint {
  time_utc: string;
  lat: number;
  lon: number;
  sog_knots?: number | null;
  cog_degrees?: number | null;
  /** `unreliable` records are marked, never dropped, and must not be
   *  rendered as if they were confident positions. */
  data_quality: AisDataQuality;
  quality_reason?: string | null;
}

export interface AisTrack {
  mmsi: string;
  vessel_name?: string | null;
  points: AisTrackPoint[];
}

/**
 * Field names and units mirror the `ais_baseline_profiles` table
 * (seconds, not minutes) rather than inventing client-side names.
 */
export interface BaselineGapProfile {
  sample_count: number;
  median_gap_seconds: number;
  p95_gap_seconds: number;
  /** Refresh job hasn't computed real stats yet. */
  stale: boolean;
  /**
   * Derived server-side from `sample_count`. `false` means the UI must
   * mark the AIS-gap factor low-confidence — an unknown vessel is
   * unknown, never silently treated as average.
   */
  has_sufficient_history: boolean;
}

export interface VesselStatic {
  mmsi: string;
  imo?: string | null;
  vessel_name?: string | null;
  vessel_type?: string | null;
  /** Null when the vessel has no recorded history at all. */
  baseline_gap_profile?: BaselineGapProfile | null;
}

export type SizeBucket = "small" | "medium" | "large";

export interface ShipDetection {
  id: string;
  position: GeoPoint;
  dark_vessel: boolean;
  /**
   * A soft flag for analyst context, **never a filter**. Many small craft
   * are legally AIS-exempt; a small dark vessel is not an evader.
   * See docs/PRD.md §7.6.
   */
  size_bucket: SizeBucket;
  size_note: string;
  estimated_length_m: [number, number];
  heading_deg?: number | null;
  /** MMSI, or null when genuinely uncorrelated (dark). */
  ais_match?: string | null;
}

// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export interface AuditStage {
  stage: string;
  before: number;
  after: number;
  dropped: number;
}

/** The 214 → 7 filter cascade. Every drop reason is logged. */
export interface AuditTrail {
  detection_id: string;
  stages: AuditStage[];
  final_candidate_count: number;
}
