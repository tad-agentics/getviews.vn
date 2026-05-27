import { describe, expect, it } from "vitest";

import {
  iterationToolsComplete,
  resolveIterationStatusText,
} from "./ResearchStrip";

describe("resolveIterationStatusText", () => {
  it("keeps present tense while any tool card is still running", () => {
    const out = resolveIterationStatusText("Đang tìm video...", [
      { done: true },
      { done: false },
    ]);
    expect(out.complete).toBe(false);
    expect(out.text).toBe("Đang tìm video...");
  });

  it("switches header to past tense when all tool cards in the iteration are done", () => {
    const out = resolveIterationStatusText("Đang tìm video...", [{ done: true }]);
    expect(out.complete).toBe(true);
    expect(out.text).toBe("Đã tìm video");
  });

  it("converts other Đang… step_status strings", () => {
    expect(resolveIterationStatusText("Đang viết chẩn đoán...", [{ done: true }]).text).toBe(
      "Đã viết chẩn đoán",
    );
  });

  it("leaves status unchanged when there are no tool cards yet", () => {
    const out = resolveIterationStatusText("Đang tìm video...", []);
    expect(out.complete).toBe(false);
    expect(out.text).toBe("Đang tìm video...");
  });
});

describe("iterationToolsComplete", () => {
  it("requires at least one card", () => {
    expect(iterationToolsComplete([])).toBe(false);
    expect(iterationToolsComplete([{ done: true }])).toBe(true);
  });
});
