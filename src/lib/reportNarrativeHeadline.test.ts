import { describe, expect, it } from "vitest";

import { reportHeadlineVi } from "./reportNarrativeHeadline";

describe("reportHeadlineVi", () => {
  it("prefers narrative_vi.headline_vi for pattern", () => {
    expect(
      reportHeadlineVi({
        kind: "pattern",
        report: {
          narrative_vi: { headline_vi: "Headline từ BE" },
          tldr: { thesis: "Kết luận nhanh: legacy" },
        } as never,
      }),
    ).toBe("Headline từ BE");
  });

  it("falls back to generic first paragraph", () => {
    expect(
      reportHeadlineVi({
        kind: "generic",
        report: {
          narrative: { paragraphs: ["Đoạn mở đầu"] },
        } as never,
      }),
    ).toBe("Đoạn mở đầu");
  });
});
