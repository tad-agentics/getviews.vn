import { describe, expect, it } from "vitest";
import { frictionFromFormatAxis, rowMatchesEnergyMode } from "./productionFriction";

describe("frictionFromFormatAxis", () => {
  it("maps vlog and unboxing to low", () => {
    expect(frictionFromFormatAxis("vlog_daily")).toBe("low");
    expect(frictionFromFormatAxis("review_unboxing")).toBe("low");
  });

  it("maps montage and skit to high", () => {
    expect(frictionFromFormatAxis("montage_highlights")).toBe("high");
    expect(frictionFromFormatAxis("skit_scripted")).toBe("high");
  });
});

describe("rowMatchesEnergyMode", () => {
  const axes = new Map<number, string>([
    [1, "vlog_daily"],
    [2, "montage_highlights"],
  ]);

  it("low energy keeps only low-friction classes", () => {
    expect(rowMatchesEnergyMode(1, axes, "low")).toBe(true);
    expect(rowMatchesEnergyMode(2, axes, "low")).toBe(false);
  });

  it("high energy keeps all", () => {
    expect(rowMatchesEnergyMode(2, axes, "high")).toBe(true);
  });
});
