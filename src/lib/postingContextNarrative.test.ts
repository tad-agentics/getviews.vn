import { describe, expect, it } from "vitest";

import { buildDiagnosisPostingNarrative } from "./postingContextNarrative";

const basePayload = {
  grid: Array.from({ length: 7 }, () => Array(8).fill(3)),
  variance_note: {
    kind: "strong",
    label: "Heatmap CÓ ý nghĩa",
    detail: "Cửa sổ mạnh nhất gấp 2.0× trung vị — tín hiệu ổn định.",
  },
  top_3_windows: [
    { day: "Thứ 3", hours: "18–20", lift_multiplier: 2.1, sample: 12 },
    { day: "Thứ 6", hours: "20–22", lift_multiplier: 1.8, sample: 9 },
  ],
  sample_size: 112,
  window_days: 14,
  niche_label: "Công nghệ",
  user_post_window_vi: "Bài đang phân tích đăng: Thứ 2, khung 20–22 (giờ Việt Nam).",
};

describe("buildDiagnosisPostingNarrative", () => {
  it("weaves sample, variance, user window, and top slots", () => {
    const text = buildDiagnosisPostingNarrative(basePayload);
    expect(text).toContain("112 video");
    expect(text).toContain("Công nghệ");
    expect(text).toContain("Cửa sổ mạnh nhất gấp 2.0×");
    expect(text).toContain("\n\n");
    expect(text).toContain("Thứ 2, khung 20–22");
    expect(text).toContain("Thứ 3 18–20");
    expect(text).toContain("2.1× trung vị ngách");
  });

  it("handles sparse variance without top windows", () => {
    const text = buildDiagnosisPostingNarrative({
      ...basePayload,
      variance_note: { kind: "sparse", label: "Heatmap CHƯA ổn định", detail: "" },
      top_3_windows: [],
      user_post_window_vi: null,
    });
    expect(text).toContain("khung giờ chưa đủ ổn định");
    expect(text).not.toContain("Ba cửa sổ");
  });
});
