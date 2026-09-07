/**
 * Typed client for the SAGARDRISHTI API.
 *
 * Two things this layer exists to get right, beyond plumbing:
 *
 * 1. **A `501` is not an error to swallow.** Several contract endpoints
 *    (hindcast, forecast, evidence, analyse) deliberately return 501
 *    because the pipeline behind them does not exist yet. The UI must
 *    say "not available yet, here's why" — NOT render an empty chart,
 *    which would imply zero drift rather than no drift model. An empty
 *    state that looks like data is a lie, so `NotImplementedError` is a
 *    distinct type callers are expected to branch on.
 *
 * 2. **Errors carry the server's reason.** Every non-2xx response is
 *    RFC 7807 problem+json with a `detail` explaining what is missing.
 *    Throwing away that string and showing "Request failed" would
 *    discard the most useful thing the server said.
 *
 * Not yet consumed by Shell.tsx — that swap is a separate, mechanical
 * change (see docs/HANDOVER.md task B). Kept apart deliberately so the
 * type-correctness work here is reviewable on its own.
 */

import type {
  AisTrack,
  AuditTrail,
  Detection,
  Page,
  ProblemDetail,
  Scene,
  ShipDetection,
  Suspect,
  VesselStatic,
} from "./apiTypes";

export const API_BASE: string =
  (import.meta.env?.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000/api/v1";

/** A non-2xx response, carrying the server's problem+json body. */
export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetail;

  constructor(problem: ProblemDetail) {
    super(problem.detail ?? problem.title);
    this.name = "ApiError";
    this.status = problem.status;
    this.problem = problem;
  }
}

/**
 * The endpoint exists in the contract but its pipeline is not built.
 * Distinct from ApiError so the UI can render an honest "coming in
 * Phase N" panel rather than an error toast — this is an expected state
 * today, not a failure.
 */
export class NotImplementedError extends ApiError {
  constructor(problem: ProblemDetail) {
    super(problem);
    this.name = "NotImplementedError";
  }
}

/** Parse a problem+json body, tolerating a server that returned something else. */
async function problemFrom(res: Response): Promise<ProblemDetail> {
  try {
    const body = (await res.json()) as Partial<ProblemDetail>;
    if (typeof body?.status === "number" && typeof body?.title === "string") {
      return body as ProblemDetail;
    }
    // Shape we did not expect — surface it rather than inventing a message.
    return {
      type: "about:blank",
      title: res.statusText || "Request failed",
      status: res.status,
      detail: JSON.stringify(body),
    };
  } catch {
    // Non-JSON body (proxy error page, empty 502). Still report honestly.
    return {
      type: "about:blank",
      title: res.statusText || "Request failed",
      status: res.status,
      detail: `Server returned ${res.status} with a non-JSON body`,
    };
  }
}

async function request<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }

  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const problem = await problemFrom(res);
    throw problem.status === 501 ? new NotImplementedError(problem) : new ApiError(problem);
  }
  return (await res.json()) as T;
}

/** Unwrap the `Page` envelope. Pagination is not yet exercised — every
 *  list endpoint is fixture-backed and returns a single page. */
async function requestList<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T[]> {
  const page = await request<Page<T>>(path, params);
  return page.items;
}

// ---------------------------------------------------------------------------
// Scenes
// ---------------------------------------------------------------------------

export function listScenes(params?: {
  bbox?: string;
  start?: string;
  end?: string;
  sensor?: string;
  limit?: number;
}): Promise<Scene[]> {
  return requestList<Scene>("/scenes", params);
}

export function getScene(sceneId: string): Promise<Scene> {
  return request<Scene>(`/scenes/${encodeURIComponent(sceneId)}`);
}

// ---------------------------------------------------------------------------
// Detections
// ---------------------------------------------------------------------------

export function listDetections(params?: {
  scene_id?: string;
  min_confidence?: number;
  limit?: number;
}): Promise<Detection[]> {
  return requestList<Detection>("/detections", params);
}

export function getDetection(detectionId: string): Promise<Detection> {
  return request<Detection>(`/detections/${encodeURIComponent(detectionId)}`);
}

/** Ranked candidates. Returns factors including negative contributions —
 *  render all of them. */
export function getSuspects(detectionId: string): Promise<Suspect[]> {
  return request<Suspect[]>(`/detections/${encodeURIComponent(detectionId)}/suspects`);
}

/** The 214 → 7 cascade with per-stage drop counts. */
export function getAudit(detectionId: string): Promise<AuditTrail> {
  return request<AuditTrail>(`/detections/${encodeURIComponent(detectionId)}/audit`);
}

/** Throws `NotImplementedError` until M5 exists. Branch on it, don't catch-all. */
export function getHindcast(detectionId: string): Promise<never> {
  return request<never>(`/detections/${encodeURIComponent(detectionId)}/hindcast`);
}

/** Throws `NotImplementedError` until M5 exists. */
export function getForecast(detectionId: string, hours = 48): Promise<never> {
  return request<never>(`/detections/${encodeURIComponent(detectionId)}/forecast`, { hours });
}

// ---------------------------------------------------------------------------
// AIS and ships
// ---------------------------------------------------------------------------

export function listAisTracks(params?: {
  bbox?: string;
  start?: string;
  end?: string;
  mmsi?: string;
  limit?: number;
}): Promise<AisTrack[]> {
  return requestList<AisTrack>("/ais/tracks", params);
}

export function getVessel(mmsi: string): Promise<VesselStatic> {
  return request<VesselStatic>(`/ais/vessels/${encodeURIComponent(mmsi)}`);
}

export function listShips(sceneId?: string): Promise<ShipDetection[]> {
  return requestList<ShipDetection>("/ships", { scene_id: sceneId });
}

export function getShip(shipId: string): Promise<ShipDetection> {
  return request<ShipDetection>(`/ships/${encodeURIComponent(shipId)}`);
}
