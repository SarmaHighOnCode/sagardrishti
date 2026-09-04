// @vitest-environment jsdom
import { describe, it, expect, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ConfidenceBar, FactorBar } from "./ConfidenceBar";

afterEach(cleanup);

describe("ConfidenceBar", () => {
  it("renders the formatted probability value by default", () => {
    render(<ConfidenceBar value={0.5} />);
    expect(screen.getByRole("meter")).toBeTruthy();
    expect(screen.getByText("0.50")).toBeTruthy();
  });

  it("hides the value when showValue is false", () => {
    render(<ConfidenceBar value={0.5} showValue={false} />);
    expect(screen.queryByText("0.50")).toBeNull();
  });

  it("sets aria-valuenow/min/max on the meter", () => {
    render(<ConfidenceBar value={0.9} />);
    const meter = screen.getByRole("meter");
    expect(meter.getAttribute("aria-valuenow")).toBe("0.9");
    expect(meter.getAttribute("aria-valuemin")).toBe("0");
    expect(meter.getAttribute("aria-valuemax")).toBe("1");
  });

  it("clamps values above 1 to 1", () => {
    render(<ConfidenceBar value={1.5} />);
    const meter = screen.getByRole("meter");
    expect(meter.getAttribute("aria-valuenow")).toBe("1");
    expect(screen.getByText("1.00")).toBeTruthy();
  });

  it("clamps values below 0 to 0", () => {
    render(<ConfidenceBar value={-0.5} />);
    const meter = screen.getByRole("meter");
    expect(meter.getAttribute("aria-valuenow")).toBe("0");
    expect(screen.getByText("0.00")).toBeTruthy();
  });

  it("uses the low-confidence fill color under 0.4", () => {
    render(<ConfidenceBar value={0.1} />);
    const meter = screen.getByRole("meter");
    const fill = meter.firstElementChild as HTMLElement;
    expect(fill.style.background).toBe("var(--gray2)");
  });

  it("uses the medium-confidence fill color between 0.4 and 0.7", () => {
    render(<ConfidenceBar value={0.5} />);
    const meter = screen.getByRole("meter");
    const fill = meter.firstElementChild as HTMLElement;
    expect(fill.style.background).toBe("var(--orange3)");
  });

  it("uses the high-confidence fill color at 0.7 and above", () => {
    render(<ConfidenceBar value={0.7} />);
    const meter = screen.getByRole("meter");
    const fill = meter.firstElementChild as HTMLElement;
    expect(fill.style.background).toBe("var(--red3)");
  });
});

describe("FactorBar", () => {
  it("renders the factor name and a plus-prefixed magnitude for positive contributions", () => {
    render(<FactorBar name="AIS gap" contribution={1.2} />);
    expect(screen.getByText("AIS gap")).toBeTruthy();
    expect(screen.getByText("+1.20")).toBeTruthy();
  });

  it("renders a minus-prefixed magnitude for negative contributions", () => {
    render(<FactorBar name="Known operator" contribution={-0.8} />);
    expect(screen.getByText("−0.80")).toBeTruthy();
  });

  it("appends a low-confidence label and title when confidence is low", () => {
    render(<FactorBar name="Weather" contribution={0.3} confidence="low" />);
    expect(screen.getByText("(low conf.)")).toBeTruthy();
    expect(screen.getByText("Weather", { exact: false }).closest("div")?.title).toBe(
      "low confidence — thin supporting evidence",
    );
  });

  it("omits the low-confidence label for high confidence", () => {
    render(<FactorBar name="Weather" contribution={0.3} confidence="high" />);
    expect(screen.queryByText("(low conf.)")).toBeNull();
  });
});
