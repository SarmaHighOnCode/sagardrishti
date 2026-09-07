import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  NotImplementedError,
  getDetection,
  getHindcast,
  getSuspects,
  getVessel,
  listDetections,
  listShips,
} from "./api";

/** Build a Response-like object without pulling in a fetch polyfill. */
function jsonResponse(body: unknown, status = 200, statusText = "OK"): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText,
    json: async () => body,
  } as Response;
}

/**
 * Typed to match fetch's own signature. Declaring the parameters matters:
 * `vi.fn(async () => res)` infers a zero-argument function, so
 * `spy.mock.calls[0][0]` is a type error rather than the requested URL.
 */
function mockFetch(res: Response) {
  const spy = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => res);
  vi.stubGlobal("fetch", spy);
  return spy;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("list endpoints unwrap the Page envelope", () => {
  it("returns items, not the envelope", async () => {
    mockFetch(jsonResponse({ items: [{ id: "det_1" }], next_cursor: null }));
    const detections = await listDetections();
    expect(Array.isArray(detections)).toBe(true);
    expect(detections[0].id).toBe("det_1");
  });

  it("returns an empty array for an empty page", async () => {
    mockFetch(jsonResponse({ items: [], next_cursor: null }));
    expect(await listShips()).toEqual([]);
  });
});

describe("query parameters", () => {
  it("serialises provided filters", async () => {
    const spy = mockFetch(jsonResponse({ items: [], next_cursor: null }));
    await listDetections({ scene_id: "S1C_TEST", min_confidence: 0.5 });

    const url = new URL(String(spy.mock.calls[0][0]));
    expect(url.searchParams.get("scene_id")).toBe("S1C_TEST");
    expect(url.searchParams.get("min_confidence")).toBe("0.5");
  });

  it("omits undefined filters rather than sending 'undefined'", async () => {
    const spy = mockFetch(jsonResponse({ items: [], next_cursor: null }));
    await listShips(undefined);

    const url = new URL(String(spy.mock.calls[0][0]));
    expect(url.searchParams.has("scene_id")).toBe(false);
  });

  it("encodes path parameters", async () => {
    const spy = mockFetch(jsonResponse({ mmsi: "419001234" }));
    await getVessel("419 001234");

    expect(String(spy.mock.calls[0][0])).toContain("419%20001234");
  });
});

describe("501 is a distinct, expected state", () => {
  /**
   * The pipeline stages behind these endpoints do not exist yet. The UI
   * must be able to tell "not built" apart from "broken", so it can show
   * an honest panel instead of an empty chart implying zero drift.
   */
  it("throws NotImplementedError, not a generic ApiError", async () => {
    mockFetch(
      jsonResponse(
        {
          type: "about:blank",
          title: "Not Implemented",
          status: 501,
          detail: "M5 backward drift ensemble is not built yet",
        },
        501,
      ),
    );

    await expect(getHindcast("det_1")).rejects.toBeInstanceOf(NotImplementedError);
  });

  it("preserves the server's explanation", async () => {
    mockFetch(
      jsonResponse(
        {
          type: "about:blank",
          title: "Not Implemented",
          status: 501,
          detail: "M5 backward drift ensemble is not built yet",
        },
        501,
      ),
    );

    await expect(getHindcast("det_1")).rejects.toThrow(/M5 backward drift ensemble/);
  });

  it("NotImplementedError is still an ApiError, so a catch-all still works", async () => {
    mockFetch(jsonResponse({ title: "Not Implemented", status: 501 }, 501));
    await expect(getHindcast("det_1")).rejects.toBeInstanceOf(ApiError);
  });
});

describe("error handling", () => {
  it("surfaces the problem+json detail as the message", async () => {
    mockFetch(
      jsonResponse(
        {
          type: "about:blank",
          title: "Not Found",
          status: 404,
          detail: "no detection with id 'nope'",
        },
        404,
      ),
    );

    await expect(getDetection("nope")).rejects.toThrow(/no detection with id/);
  });

  it("exposes the status code for branching", async () => {
    mockFetch(jsonResponse({ title: "Not Found", status: 404 }, 404));

    const err = await getSuspects("nope").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(404);
  });

  it("does not invent a message when the body is not problem+json", async () => {
    // A proxy or gateway error returns HTML, not our shape. The client
    // must report what actually happened rather than pretending.
    mockFetch({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => {
        throw new SyntaxError("Unexpected token < in JSON");
      },
    } as unknown as Response);

    const err = await getDetection("det_1").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(502);
    expect((err as ApiError).message).toMatch(/non-JSON body/);
  });

  it("handles a JSON body of the wrong shape without masking it", async () => {
    mockFetch(jsonResponse({ oops: true }, 500, "Internal Server Error"));

    const err = await getDetection("det_1").catch((e: unknown) => e);
    expect((err as ApiError).status).toBe(500);
    expect((err as ApiError).message).toContain("oops");
  });
});

describe("successful responses pass through unchanged", () => {
  it("returns a detection with its penalty log intact", async () => {
    mockFetch(
      jsonResponse({
        id: "det_synthetic_002",
        confidence: 0.19,
        confidence_raw: 0.62,
        classification: "look_alike",
        penalties: [
          {
            check: "wind_window",
            delta: -0.28,
            reason: "wind speed 1.6 m/s below 2-12 m/s detection window",
          },
        ],
      }),
    );

    const det = await getDetection("det_synthetic_002");
    expect(det.confidence_raw).toBe(0.62);
    expect(det.penalties[0].reason).toMatch(/wind speed/);
  });

  it("returns suspects with negative contributions preserved", async () => {
    // Exculpatory factors must survive the client untouched — filtering
    // them here would defeat the point of showing them at all.
    mockFetch(
      jsonResponse([
        {
          rank: 1,
          mmsi: "419001234",
          factors: [
            { name: "drift_consistency", contribution: 2.14 },
            { name: "off_lane_distance", contribution: -0.22 },
          ],
        },
      ]),
    );

    const suspects = await getSuspects("det_1");
    const negative = suspects[0].factors.filter((f) => f.contribution < 0);
    expect(negative).toHaveLength(1);
  });
});
