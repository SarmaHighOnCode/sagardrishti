import { describe, it, expect } from "vitest";
import {
  formatCoord,
  formatLat,
  formatLon,
  formatUTC,
  formatUTCTimeOnly,
  formatMMSI,
  formatIMO,
  formatHash,
  formatProbability,
  formatWithInterval,
  formatBearing,
  formatArea,
  formatDecibels,
  formatSpeed,
  formatHours,
} from "./format";

/**
 * These are the ONLY formatters allowed to touch the screen (see format.ts
 * header). An operator reads these values character by character, so the
 * exact string shape — hemisphere letters, padding, decimal places — is
 * the behaviour under test, not an implementation detail.
 */

describe("formatCoord", () => {
  it("renders a northeast position", () => {
    expect(formatCoord(12.4821, 74.9033)).toBe("12.482100° N, 74.903300° E");
  });

  it("renders a southwest position", () => {
    expect(formatCoord(-12.4821, -74.9033)).toBe("12.482100° S, 74.903300° W");
  });

  it("treats zero as the positive hemisphere for both axes", () => {
    expect(formatCoord(0, 0)).toBe("0.000000° N, 0.000000° E");
  });
});

describe("formatLat / formatLon", () => {
  it("labels northern latitude N and southern S", () => {
    expect(formatLat(9.75)).toBe("9.750000° N");
    expect(formatLat(-9.75)).toBe("9.750000° S");
  });

  it("labels eastern longitude E and western W", () => {
    expect(formatLon(75.6)).toBe("75.600000° E");
    expect(formatLon(-75.6)).toBe("75.600000° W");
  });
});

describe("formatUTC", () => {
  it("formats a Date to ISO 8601 UTC with explicit Z, no milliseconds", () => {
    expect(formatUTC(new Date("2026-05-25T06:40:00.000Z"))).toBe("2026-05-25T06:40:00Z");
  });

  it("accepts an ISO string as well as a Date", () => {
    expect(formatUTC("2026-05-25T06:40:00.123Z")).toBe("2026-05-25T06:40:00Z");
  });

  it("renders an em-dash for an invalid date", () => {
    expect(formatUTC("not-a-date")).toBe("—");
  });
});

describe("formatUTCTimeOnly", () => {
  it("strips the date, keeping HH:MM:SSZ", () => {
    expect(formatUTCTimeOnly("2026-05-25T06:40:00Z")).toBe("06:40:00Z");
  });

  it("passes through the em-dash for an invalid date", () => {
    expect(formatUTCTimeOnly("garbage")).toBe("—");
  });
});

describe("formatMMSI", () => {
  it("left-pads a short MMSI to 9 digits", () => {
    expect(formatMMSI("12345")).toBe("000012345");
  });

  it("accepts a numeric MMSI", () => {
    expect(formatMMSI(419001234)).toBe("419001234");
  });

  it("does not comma-group a full-length MMSI", () => {
    expect(formatMMSI("419001234")).toBe("419001234");
  });
});

describe("formatIMO", () => {
  it("left-pads to 7 digits", () => {
    expect(formatIMO("1234")).toBe("0001234");
  });

  it("renders an em-dash for null or undefined", () => {
    expect(formatIMO(null)).toBe("—");
    expect(formatIMO(undefined)).toBe("—");
  });

  it("accepts a numeric IMO", () => {
    expect(formatIMO(9074729)).toBe("9074729");
  });
});

describe("formatHash", () => {
  it("truncates a long hash with an ellipsis", () => {
    expect(formatHash("abcdef1234567890")).toBe("abcdef12…");
  });

  it("leaves a short hash untouched", () => {
    expect(formatHash("abc123")).toBe("abc123");
  });

  it("honours a custom truncation length", () => {
    expect(formatHash("abcdef1234567890", 4)).toBe("abcd…");
  });

  it("does not truncate a hash exactly at the boundary", () => {
    expect(formatHash("abcdefgh", 8)).toBe("abcdefgh");
  });
});

describe("formatProbability", () => {
  it("renders to two decimal places", () => {
    expect(formatProbability(0.7135)).toBe("0.71");
  });

  it("does not scale to a percentage", () => {
    expect(formatProbability(1)).toBe("1.00");
  });
});

describe("formatWithInterval", () => {
  it("renders the value with its confidence interval", () => {
    expect(formatWithInterval(4.2, [3.1, 5.4], "kn")).toBe("4.2 kn (3.1–5.4)");
  });

  it("honours a custom digit count", () => {
    expect(formatWithInterval(4.256, [3.1, 5.44], "kn", 2)).toBe("4.26 kn (3.10–5.44)");
  });
});

describe("formatBearing", () => {
  it("pads to three digits with a degree sign", () => {
    expect(formatBearing(7)).toBe("007°");
  });

  it("normalises a negative bearing into 0-359", () => {
    expect(formatBearing(-10)).toBe("350°");
  });

  it("wraps a bearing of 360 or more", () => {
    expect(formatBearing(370)).toBe("010°");
  });

  it("rounds to the nearest whole degree", () => {
    expect(formatBearing(247.3)).toBe("247°");
    expect(formatBearing(247.6)).toBe("248°");
  });
});

describe("formatArea", () => {
  it("renders two decimals with the km² unit", () => {
    expect(formatArea(12.4321)).toBe("12.43 km²");
  });
});

describe("formatDecibels", () => {
  it("renders one decimal with the dB unit", () => {
    expect(formatDecibels(8.44)).toBe("8.4 dB");
  });
});

describe("formatSpeed", () => {
  it("renders one decimal with the knots unit", () => {
    expect(formatSpeed(14.96)).toBe("15.0 kn");
  });
});

describe("formatHours", () => {
  it("renders sub-hour durations in whole minutes", () => {
    expect(formatHours(0.5)).toBe("30 min");
  });

  it("renders hour-or-longer durations in decimal hours", () => {
    expect(formatHours(2.25)).toBe("2.3 h");
  });

  it("treats exactly one hour as hours, not minutes", () => {
    expect(formatHours(1)).toBe("1.0 h");
  });
});
