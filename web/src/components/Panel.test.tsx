// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Panel, MetricRow } from "./Panel";

afterEach(cleanup);

describe("Panel", () => {
  it("renders the label and children when open by default", () => {
    render(
      <Panel label="Detections">
        <div>child content</div>
      </Panel>,
    );
    expect(screen.getByText("Detections")).toBeTruthy();
    expect(screen.getByText("child content")).toBeTruthy();
  });

  it("hides children when defaultOpen is false", () => {
    render(
      <Panel label="Detections" defaultOpen={false}>
        <div>child content</div>
      </Panel>,
    );
    expect(screen.queryByText("child content")).toBeNull();
  });

  it("toggles children visibility when the header is clicked", () => {
    render(
      <Panel label="Detections">
        <div>child content</div>
      </Panel>,
    );
    const header = screen.getByText("Detections").closest("header")!;
    fireEvent.click(header);
    expect(screen.queryByText("child content")).toBeNull();
    fireEvent.click(header);
    expect(screen.getByText("child content")).toBeTruthy();
  });

  it("renders the badge text when provided", () => {
    render(
      <Panel label="Suspects" badge="7 of 214">
        <div />
      </Panel>,
    );
    expect(screen.getByText("7 of 214")).toBeTruthy();
  });

  it("omits the badge when not provided", () => {
    render(
      <Panel label="Suspects">
        <div />
      </Panel>,
    );
    expect(screen.queryByText(/of/)).toBeNull();
  });

  it("caps height and enables vertical scrolling when scroll is true", () => {
    render(
      <Panel label="Detections" scroll>
        <div>child content</div>
      </Panel>,
    );
    const body = screen.getByText("child content").parentElement as HTMLElement;
    expect(body.style.maxHeight).toBe("280px");
    expect(body.style.overflowY).toBe("auto");
  });

  it("leaves height and overflow unset when scroll is false", () => {
    render(
      <Panel label="Detections">
        <div>child content</div>
      </Panel>,
    );
    const body = screen.getByText("child content").parentElement as HTMLElement;
    expect(body.style.maxHeight).toBe("");
    expect(body.style.overflowY).toBe("");
  });
});

describe("MetricRow", () => {
  it("renders the label and value", () => {
    render(<MetricRow label="Speed" value="12.4 kn" />);
    expect(screen.getByText("Speed")).toBeTruthy();
    expect(screen.getByText("12.4 kn")).toBeTruthy();
  });

  it("applies the mono class by default", () => {
    render(<MetricRow label="Speed" value="12.4 kn" />);
    expect(screen.getByText("12.4 kn").className).toBe("mono");
  });

  it("applies the tabular class when mono is false", () => {
    render(<MetricRow label="Speed" value="12.4 kn" mono={false} />);
    expect(screen.getByText("12.4 kn").className).toBe("tabular");
  });

  it("applies a custom tone color when provided", () => {
    render(<MetricRow label="Speed" value="12.4 kn" tone="var(--red4)" />);
    expect(screen.getByText("12.4 kn").style.color).toBe("var(--red4)");
  });
});
