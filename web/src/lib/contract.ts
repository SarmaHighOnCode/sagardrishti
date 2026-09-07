/**
 * A runtime-readable mirror of every wire type in `apiTypes.ts`.
 *
 * TypeScript interfaces vanish at compile time, so nothing can check them
 * against the server at runtime — which is exactly how `apiTypes.ts` and
 * `schemas.py` could drift apart silently. This module makes the field
 * lists real values, and `contract.test.ts` diffs them against the
 * server's published `docs/api/openapi.json`.
 *
 * The trick that makes this trustworthy rather than another hand-written
 * mirror that also drifts: `FieldSpec<T>` is COMPUTED from the interface.
 * You cannot add a key that is not in the type, omit one that is, or call
 * a required field optional — each is a compile error. So `tsc` keeps
 * these manifests honest against `apiTypes.ts`, and the test keeps
 * `apiTypes.ts` honest against the server. Neither half can slip.
 *
 * WHEN A TEST HERE FAILS, the answer is almost never to edit this file
 * until it passes. It is to work out which side is wrong:
 *
 *   - Field on the server, missing here → the API gained a field. Add it
 *     to `apiTypes.ts` (and here), or decide the client does not need it.
 *   - Field here, missing on the server → you invented it. It will be
 *     `undefined` at runtime. Remove it, or add it to `schemas.py` first.
 *   - Optionality differs → the more dangerous case. A field the client
 *     calls required but the server may omit is a crash waiting for the
 *     one record that omits it.
 */

import type {
  AisTrack,
  AisTrackPoint,
  AuditStage,
  AuditTrail,
  BaselineGapProfile,
  DataQualitySummary,
  Detection,
  DetectionAttributes,
  GeoPoint,
  GeoPolygon,
  Penalty,
  ProblemDetail,
  Scene,
  ShipDetection,
  Suspect,
  SuspectFactor,
  VesselStatic,
} from "./apiTypes";

export type Optionality = "required" | "optional";

/**
 * Every key of `T`, mapped to whether the type says it may be absent.
 *
 * `-?` strips optionality from the mapped keys so every field must be
 * listed explicitly — an omission is a compile error rather than a
 * silently unchecked field. `undefined extends T[K]` then recovers what
 * the original declaration said, so the value cannot disagree with the
 * type it describes.
 */
export type FieldSpec<T> = {
  [K in keyof T]-?: undefined extends T[K] ? "optional" : "required";
};

// ---------------------------------------------------------------------------
// Manifests. Keep the key order matching apiTypes.ts — these are read by
// humans during review as much as by the test.
// ---------------------------------------------------------------------------

const GeoPointFields = {
  type: "required",
  coordinates: "required",
} satisfies FieldSpec<GeoPoint>;

const GeoPolygonFields = {
  type: "required",
  coordinates: "required",
} satisfies FieldSpec<GeoPolygon>;

const ProblemDetailFields = {
  type: "required",
  title: "required",
  status: "required",
  detail: "optional",
  instance: "optional",
} satisfies FieldSpec<ProblemDetail>;

const SceneFields = {
  id: "required",
  sensor: "required",
  acquired_utc: "required",
  footprint: "required",
  product_hash: "required",
  status: "required",
} satisfies FieldSpec<Scene>;

const PenaltyFields = {
  check: "required",
  delta: "required",
  reason: "required",
  evidence: "optional",
} satisfies FieldSpec<Penalty>;

const DetectionAttributesFields = {
  area_km2: "required",
  major_axis_bearing_deg: "required",
  damping_ratio_db: "required",
  edge_sharpness: "required",
  thickness_class: "required",
} satisfies FieldSpec<DetectionAttributes>;

const DetectionFields = {
  id: "required",
  scene_id: "required",
  geometry: "required",
  confidence: "required",
  confidence_raw: "required",
  classification: "required",
  attributes: "required",
  penalties: "required",
} satisfies FieldSpec<Detection>;

const SuspectFactorFields = {
  name: "required",
  value: "required",
  weight: "required",
  contribution: "required",
  confidence: "required",
  note: "optional",
} satisfies FieldSpec<SuspectFactor>;

const DataQualitySummaryFields = {
  records_used: "required",
  records_excluded: "required",
  exclusion_reasons: "required",
} satisfies FieldSpec<DataQualitySummary>;

const SuspectFields = {
  rank: "required",
  mmsi: "required",
  imo: "optional",
  vessel_name: "required",
  vessel_type: "required",
  posterior: "required",
  calibrated: "required",
  // Uncertainty pairs. Both halves required on both sides of the wire —
  // a release time without its interval is a schema violation, not a
  // convenience. See schemas.py's module docstring, rule 1.
  inferred_release_utc: "required",
  inferred_release_ci_minutes: "required",
  slick_age_hours: "required",
  slick_age_ci: "required",
  factors: "required",
  data_quality: "required",
} satisfies FieldSpec<Suspect>;

const AisTrackPointFields = {
  time_utc: "required",
  lat: "required",
  lon: "required",
  sog_knots: "optional",
  cog_degrees: "optional",
  data_quality: "required",
  quality_reason: "optional",
} satisfies FieldSpec<AisTrackPoint>;

const AisTrackFields = {
  mmsi: "required",
  vessel_name: "optional",
  points: "required",
} satisfies FieldSpec<AisTrack>;

const BaselineGapProfileFields = {
  sample_count: "required",
  median_gap_seconds: "required",
  p95_gap_seconds: "required",
  stale: "required",
  has_sufficient_history: "required",
} satisfies FieldSpec<BaselineGapProfile>;

const VesselStaticFields = {
  mmsi: "required",
  imo: "optional",
  vessel_name: "optional",
  vessel_type: "optional",
  baseline_gap_profile: "optional",
} satisfies FieldSpec<VesselStatic>;

const ShipDetectionFields = {
  id: "required",
  position: "required",
  dark_vessel: "required",
  size_bucket: "required",
  size_note: "required",
  estimated_length_m: "required",
  heading_deg: "optional",
  ais_match: "optional",
} satisfies FieldSpec<ShipDetection>;

const AuditStageFields = {
  stage: "required",
  before: "required",
  after: "required",
  dropped: "required",
} satisfies FieldSpec<AuditStage>;

const AuditTrailFields = {
  detection_id: "required",
  stages: "required",
  final_candidate_count: "required",
} satisfies FieldSpec<AuditTrail>;

/**
 * Keys are the schema names in `docs/api/openapi.json`. A client type
 * whose name does not appear there has nothing to check it against —
 * which the test treats as a failure, not a pass.
 */
export const CONTRACT: Record<string, Record<string, Optionality>> = {
  GeoPoint: GeoPointFields,
  GeoPolygon: GeoPolygonFields,
  ProblemDetail: ProblemDetailFields,
  Scene: SceneFields,
  Penalty: PenaltyFields,
  DetectionAttributes: DetectionAttributesFields,
  Detection: DetectionFields,
  SuspectFactor: SuspectFactorFields,
  DataQualitySummary: DataQualitySummaryFields,
  Suspect: SuspectFields,
  AisTrackPoint: AisTrackPointFields,
  AisTrack: AisTrackFields,
  BaselineGapProfile: BaselineGapProfileFields,
  VesselStatic: VesselStaticFields,
  ShipDetection: ShipDetectionFields,
  AuditStage: AuditStageFields,
  AuditTrail: AuditTrailFields,
};

/**
 * Server-side schemas the console deliberately does not mirror.
 *
 * `Page_*` are FastAPI's generated names for the parameterised list
 * envelope; the client models that as `Page<T>`. The `*ValidationError`
 * pair is FastAPI's own 422 body, which this API never returns — every
 * error goes through `problem()`.
 *
 * Anything NOT listed here and not in CONTRACT fails the test: a new
 * server type appearing unnoticed is precisely the drift being guarded
 * against, so it must be either mirrored or consciously excluded.
 */
export const NOT_MIRRORED = [/^Page_.+_$/, /^HTTPValidationError$/, /^ValidationError$/];
