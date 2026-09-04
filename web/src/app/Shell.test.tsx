// @vitest-environment jsdom
import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Shell } from "./Shell";
import { SAMPLE_SLICKS } from "../lib/fixtures";
import type { SlickFeature } from "../lib/fixtures";

// MapCanvas mounts a real maplibre-gl WebGL map, which jsdom cannot render.
// Shell only needs the onSelectSlick callback plumbed through, so a stub
// that exposes it via a button is enough to exercise Shell's own logic.
vi.mock("../features/map/MapCanvas", () => ({
  MapCanvas: ({ onSelectSlick }: { onSelectSlick: (s: SlickFeature) => void }) => (
    <div>
      {SAMPLE_SLICKS.map((s) => (
        <button key={s.id} onClick={() => onSelectSlick(s)}>
          select {s.id}
        </button>
      ))}
    </div>
  ),
}));

afterEach(cleanup);

describe("Shell", () => {
  it("shows the SYNTHETIC badge (fixtures are synthetic data)", () => {
    render(<Shell />);
    expect(screen.getByText("SYNTHETIC")).toBeTruthy();
  });

  it("defaults to the first sample slick, rendered as CONFIRMED", () => {
    render(<Shell />);
    expect(screen.getByText("CONFIRMED")).toBeTruthy();
    expect(screen.queryByText("Why this was rejected")).toBeNull();
  });

  it("switches the analysis panel to REJECTED with reasons when a look-alike is selected", () => {
    render(<Shell />);
    fireEvent.click(screen.getByText("select det_synthetic_002"));
    expect(screen.getByText("REJECTED")).toBeTruthy();
    expect(screen.getByText("Why this was rejected")).toBeTruthy();
    expect(
      screen.getByText("wind speed 1.6 m/s below 2–12 m/s detection window"),
    ).toBeTruthy();
  });

  it("switches the left rail active item on click", () => {
    render(<Shell />);
    const drift = screen.getByTitle("Drift");
    const detections = screen.getByTitle("Detections");
    expect(detections.style.background).toBe("var(--fill-active)");
    fireEvent.click(drift);
    expect(drift.style.background).toBe("var(--fill-active)");
    expect(detections.style.background).toBe("transparent");
  });

  it("moves the timeline offset label when the slider changes", () => {
    render(<Shell />);
    const slider = screen.getByRole("slider") as HTMLInputElement;
    expect(screen.getByText("T_sar − 9.6 h")).toBeTruthy();
    fireEvent.change(slider, { target: { value: "0" } });
    expect(screen.getByText("T_sar − 24.0 h")).toBeTruthy();
  });

  it("lists suspect vessels with their MMSI in the Suspects panel", () => {
    render(<Shell />);
    expect(screen.getByText("419001234")).toBeTruthy();
    expect(screen.getByText("563889000")).toBeTruthy();
  });
});
