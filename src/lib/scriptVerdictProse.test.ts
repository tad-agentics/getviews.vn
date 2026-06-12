import { describe, expect, it } from "vitest";

import { scriptVerdictForDisplay, shotHasCorpusPacing } from "@/lib/scriptVerdictProse";

describe("scriptVerdictForDisplay", () => {
  it("strips @handle proof sentences when corpus strip is shown", () => {
    const raw =
      "Format này dựa trên @hi.vidayyy (27.461 view). Cấu trúc 6 cảnh giữ retention bằng cận mặt.";
    expect(scriptVerdictForDisplay(raw, true)).toBe(
      "Cấu trúc 6 cảnh giữ retention bằng cận mặt.",
    );
  });

  it("keeps full text when no corpus strip", () => {
    const raw = "Format này dựa trên @hi.vidayyy (27.461 view).";
    expect(scriptVerdictForDisplay(raw, false)).toBe(raw);
  });
});

describe("shotHasCorpusPacing", () => {
  it("is false without shot averages or scene intel", () => {
    expect(shotHasCorpusPacing({}, null)).toBe(false);
  });

  it("is true when shot has corpus_avg", () => {
    expect(shotHasCorpusPacing({ corpus_avg: 2.8 }, null)).toBe(true);
  });

  it("is true when scene intel row is present", () => {
    expect(shotHasCorpusPacing({}, { corpus_avg_duration: 2.8 })).toBe(true);
  });
});
