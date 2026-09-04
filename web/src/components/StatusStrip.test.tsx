// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { StatusStrip } from "./StatusStrip";

afterEach(cleanup);

const baseProps = {
  sceneId: "S1A-2026-001",
  sceneHash: "abcdef1234567890",
  modelName: "detector-v3",
  modelHash: "1234567890abcdef",
  forcing: "HYCOM+GFS",
};

describe("StatusStrip", () => {
  it("renders scene, model and forcing fields with shortened hashes", () => {
    render(<StatusStrip {...baseProps} />);
    expect(screen.getByText(/S1A-2026-001/)).toBeTruthy();
    expect(screen.getByText(/detector-v3/)).toBeTruthy();
    expect(screen.getByText(/HYCOM\+GFS/)).toBeTruthy();
    // formatHash shortens the full hash, so the raw full hash should not appear verbatim.
    expect(screen.queryByText(baseProps.sceneHash)).toBeNull();
  });

  it("does not show the synthetic-data warning by default", () => {
    render(<StatusStrip {...baseProps} />);
    expect(screen.queryByText(/SYNTHETIC DATA/)).toBeNull();
  });

  it("shows the synthetic-data warning when synthetic is true", () => {
    render(<StatusStrip {...baseProps} synthetic />);
    expect(screen.getByText(/SYNTHETIC DATA — NOT A REAL ASSESSMENT/)).toBeTruthy();
  });
});
