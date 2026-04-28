/**
 * BUG-06 regression: older Gemini payloads had ``prediction_pos = "~0"``
 * per the prompt's own suggestion. The headline was rendered as
 * "Video dừng ở 1.8M view nhưng đang ... kênh **~0** cần điều chỉnh..."
 * which read like broken template interpolation.
 */
import { describe, expect, it } from "vitest";

import { sanitizePredictionPos } from "@/lib/sanitizePredictionPos";

describe("sanitizePredictionPos", () => {
  it("drops the bare ~0 placeholder", () => {
    expect(sanitizePredictionPos("~0")).toBe("");
    expect(sanitizePredictionPos("~ 0")).toBe("");
  });

  it("drops tilde-dash / tilde-em-dash placeholders", () => {
    expect(sanitizePredictionPos("~—")).toBe("");
    expect(sanitizePredictionPos("~-")).toBe("");
  });

  it("drops a lone tilde", () => {
    expect(sanitizePredictionPos("~")).toBe("");
  });

  it("preserves real predictions", () => {
    expect(sanitizePredictionPos("~34K")).toBe("~34K");
    expect(sanitizePredictionPos(" ~12.5K ")).toBe(" ~12.5K ");
  });

  it("treats empty / null / undefined as empty", () => {
    expect(sanitizePredictionPos("")).toBe("");
    expect(sanitizePredictionPos(null)).toBe("");
    expect(sanitizePredictionPos(undefined)).toBe("");
    expect(sanitizePredictionPos("   ")).toBe("");
  });
});
