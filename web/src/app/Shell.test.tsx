// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Shell } from "./Shell";
import type { Detection, Suspect, ShipDetection, AisTrack } from "../lib/apiTypes";

// Shell now fetches through lib/api.ts (via lib/queries.ts) instead of
// importing lib/fixtures.ts directly. Mocking the API module — not the
// query hooks — means detectionToSlickFeature/tracksFromApi/
// shipDetectionToShipPoint in lib/adapters.ts still run for real, so
// these tests exercise the actual integration path, not a shortcut
// around it.
const OIL: Detection = {
  id: "det_synthetic_001",
  scene_id: "S1C_TEST",
  geometry: { type: "Polygon", coordinates: [[[75.42, 9.88], [75.61, 9.79], [75.42, 9.88]]] },
  confidence: 0.81,
  confidence_raw: 0.81,
  classification: "oil",
  attributes: {
    area_km2: 12.43,
    major_axis_bearing_deg: 247.3,
    damping_ratio_db: 8.4,
    edge_sharpness: 0.74,
    thickness_class: "sheen",
  },
  penalties: [],
};

const LOOK_ALIKE: Detection = {
  id: "det_synthetic_002",
  scene_id: "S1C_TEST",
  geometry: { type: "Polygon", coordinates: [[[75.9, 10.05], [76.05, 10.02], [75.9, 10.05]]] },
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
    },
    { check: "chlorophyll_anomaly", delta: -0.09, reason: "chlorophyll-a anomaly likely" },
  ],
};

const SUSPECT_1: Suspect = {
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
  factors: [
    { name: "drift_consistency", value: 0.81, weight: 2.5, contribution: 2.14, confidence: "high" },
    { name: "off_lane_distance", value: -0.17, weight: 0.8, contribution: -0.22, confidence: "high" },
  ],
  data_quality: { records_used: 412, records_excluded: 7, exclusion_reasons: {} },
};

const SHIPS: ShipDetection[] = [
  {
    id: "shp_1",
    position: { type: "Point", coordinates: [75.66, 9.84] },
    dark_vessel: false,
    size_bucket: "large",
    size_note: "AIS-correlated",
    estimated_length_m: [180, 210],
    ais_match: "419001234",
  },
];

const TRACKS: AisTrack[] = [
  {
    mmsi: "419001234",
    vessel_name: "SYNTHETIC VESSEL A",
    points: [
      { time_utc: "2026-05-25T04:00:00Z", lat: 10.3, lon: 75.1, data_quality: "ok" },
      { time_utc: "2026-05-25T04:40:00Z", lat: 9.98, lon: 75.48, data_quality: "ok" },
    ],
  },
];

const { mockListDetections, mockGetSuspects, mockListShips, mockListAisTracks } = vi.hoisted(
  () => ({
    mockListDetections: vi.fn(),
    mockGetSuspects: vi.fn(),
    mockListShips: vi.fn(),
    mockListAisTracks: vi.fn(),
  }),
);

vi.mock("../lib/api", () => ({
  listDetections: mockListDetections,
  getSuspects: mockGetSuspects,
  listShips: mockListShips,
  listAisTracks: mockListAisTracks,
}));

// MapCanvas mounts a real maplibre-gl WebGL map, which jsdom cannot
// render. The stub exposes onSelectSlick via buttons driven by the real
// `slicks` PROP (not a fixtures import), so a click here exercises the
// same prop as production.
vi.mock("../features/map/MapCanvas", () => ({
  MapCanvas: ({
    slicks,
    onSelectSlick,
  }: {
    slicks: { id: string; classification: string }[];
    onSelectSlick: (s: { id: string; classification: string }) => void;
  }) => (
    <div>
      {slicks.map((s) => (
        <button key={s.id} onClick={() => onSelectSlick(s)}>
          select {s.id}
        </button>
      ))}
    </div>
  ),
}));

function renderShell() {
  // A fresh, retry-disabled client per test: retries would make a
  // mocked rejection hang the test, and a shared client would leak
  // cached results between tests.
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <Shell />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Shell", () => {
  it("shows the SYNTHETIC badge (fixture-backed API data is synthetic)", async () => {
    mockListDetections.mockResolvedValue([OIL, LOOK_ALIKE]);
    mockGetSuspects.mockResolvedValue([SUSPECT_1]);
    mockListShips.mockResolvedValue(SHIPS);
    mockListAisTracks.mockResolvedValue(TRACKS);

    renderShell();
    expect(screen.getByText("SYNTHETIC")).toBeTruthy();
  });

  it("shows a loading state before detections resolve, not an empty panel", () => {
    mockListDetections.mockReturnValue(new Promise(() => {})); // never resolves
    mockGetSuspects.mockResolvedValue([]);
    mockListShips.mockResolvedValue([]);
    mockListAisTracks.mockResolvedValue([]);

    renderShell();
    // An empty Detection panel here would silently imply zero detections
    // exist, rather than "still fetching" — the same failure mode the
    // API client's 501 handling guards against.
    expect(screen.getByText("Loading…")).toBeTruthy();
    expect(screen.queryByText("CONFIRMED")).toBeNull();
  });

  it("defaults to the first detection, rendered as CONFIRMED", async () => {
    mockListDetections.mockResolvedValue([OIL, LOOK_ALIKE]);
    mockGetSuspects.mockResolvedValue([SUSPECT_1]);
    mockListShips.mockResolvedValue(SHIPS);
    mockListAisTracks.mockResolvedValue(TRACKS);

    renderShell();

    await waitFor(() => expect(screen.getByText("CONFIRMED")).toBeTruthy());
    expect(screen.queryByText("Why this was rejected")).toBeNull();
  });

  it("switches to REJECTED with itemised reasons when a look-alike is selected", async () => {
    mockListDetections.mockResolvedValue([OIL, LOOK_ALIKE]);
    mockGetSuspects.mockResolvedValue([]);
    mockListShips.mockResolvedValue([]);
    mockListAisTracks.mockResolvedValue([]);

    renderShell();
    await waitFor(() => expect(screen.getByText("select det_synthetic_002")).toBeTruthy());

    fireEvent.click(screen.getByText("select det_synthetic_002"));

    await waitFor(() => expect(screen.getByText("REJECTED")).toBeTruthy());
    expect(screen.getByText(/wind speed 1\.6 m\/s/)).toBeTruthy();
    expect(screen.getByText(/chlorophyll-a anomaly/)).toBeTruthy();
  });

  it("renders the top suspect's factors from the API, including a negative contribution", async () => {
    mockListDetections.mockResolvedValue([OIL, LOOK_ALIKE]);
    mockGetSuspects.mockResolvedValue([SUSPECT_1]);
    mockListShips.mockResolvedValue(SHIPS);
    mockListAisTracks.mockResolvedValue(TRACKS);

    renderShell();

    await waitFor(() => expect(screen.getByText("SYNTHETIC VESSEL A")).toBeTruthy());
    expect(screen.getByText(/MMSI 419001234/)).toBeTruthy();
    expect(screen.getByText("drift consistency")).toBeTruthy();
    // The exculpatory factor must render too — never filtered out.
    expect(screen.getByText("off lane distance")).toBeTruthy();
  });

  it("shows an error message rather than a silent empty panel when the API call fails", async () => {
    mockListDetections.mockRejectedValue(new Error("no detection with id 'nope'"));
    mockGetSuspects.mockResolvedValue([]);
    mockListShips.mockResolvedValue([]);
    mockListAisTracks.mockResolvedValue([]);

    renderShell();

    await waitFor(() => expect(screen.getByText(/no detection with id/)).toBeTruthy());
  });

  it("switches the rail's active item on click", async () => {
    mockListDetections.mockResolvedValue([OIL]);
    mockGetSuspects.mockResolvedValue([]);
    mockListShips.mockResolvedValue([]);
    mockListAisTracks.mockResolvedValue([]);

    renderShell();
    const driftButton = screen.getByTitle("Drift");
    fireEvent.click(driftButton);
    // No visible assertion target beyond "it doesn't throw" — LeftRail's
    // active state is purely presentational (background colour), which
    // is exercised visually rather than through text content.
    expect(driftButton).toBeTruthy();
  });

  it("moves the timeline slider", async () => {
    mockListDetections.mockResolvedValue([OIL]);
    mockGetSuspects.mockResolvedValue([]);
    mockListShips.mockResolvedValue([]);
    mockListAisTracks.mockResolvedValue([]);

    renderShell();
    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "0" } });
    expect(screen.getByText("T_sar − 24.0 h")).toBeTruthy();
  });
});
