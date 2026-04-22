/**
 * BUG-15 regression: the two unpopulated "Bước tiếp theo" CTAs (Soi kênh
 * đối thủ, Theo dõi trend) were rendering "Dự kiến: — view (kênh TB —)".
 * The whole forecast row should vanish when both values are blank.
 */
import { describe, expect, it } from "vitest";

import { renderForecastLine } from "./forecastLine";

describe("renderForecastLine", () => {
  it("drops the line when both values are em-dashes", () => {
    expect(renderForecastLine({ expected_range: "—", baseline: "—" })).toBeNull();
  });

  it("drops the line when both are null/undefined/empty", () => {
    expect(renderForecastLine({ expected_range: null, baseline: null })).toBeNull();
    expect(renderForecastLine({ expected_range: "", baseline: "" })).toBeNull();
    expect(renderForecastLine(undefined)).toBeNull();
  });

  it("drops the line when only a baseline is present (range is the headline)", () => {
    expect(renderForecastLine({ expected_range: null, baseline: "6.2K" })).toBeNull();
  });

  it("renders the range alone when baseline is missing", () => {
    expect(renderForecastLine({ expected_range: "8K–15K", baseline: null })).toBe(
      "Dự kiến: 8K–15K view",
    );
  });

  it("renders the full line when both are populated", () => {
    expect(renderForecastLine({ expected_range: "8K–15K", baseline: "6.2K" })).toBe(
      "Dự kiến: 8K–15K view (kênh TB 6.2K)",
    );
  });

  it("respects a custom unit (timing cards use no unit)", () => {
    expect(
      renderForecastLine({ expected_range: "20:00 thứ Ba", baseline: "18:00" }, { unit: "" }),
    ).toBe("Dự kiến: 20:00 thứ Ba (kênh TB 18:00)");
  });
});
