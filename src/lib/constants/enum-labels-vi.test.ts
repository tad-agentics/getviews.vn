/**
 * Regression guard for BUG-02 (QA audit 2026-04-22): raw enum codes
 * (TEXT_TITLE, STAT_BURST, face_to_camera, how_to, face_with_text,
 * face_enter) had leaked into the user-facing UI. Every new enum code
 * mapping added to the Vietnamese table should come with a test case
 * here so we can't silently ship an English word back into the app.
 */
import { describe, expect, it } from "vitest";

import {
  firstFrameVi,
  hookTimelineEventVi,
  overlayStyleVi,
  sceneTypeVi,
} from "./enum-labels-vi";

describe("overlayStyleVi", () => {
  it.each([
    ["TEXT_TITLE", "Tiêu đề lớn"],
    ["BOLD_CENTER", "Chữ in đậm ở giữa"],
    ["BOLD CENTER", "Chữ in đậm ở giữa"],
    ["SUB_CAPTION", "Phụ đề"],
    ["SUB-CAPTION", "Phụ đề"],
    ["QUESTION_XL", "Câu hỏi cỡ lớn"],
    ["STAT_BURST", "Số liệu nổi bật"],
    ["LABEL", "Nhãn"],
    ["NONE", "Không có chữ"],
  ])("translates %s → %s", (raw, vi) => {
    expect(overlayStyleVi(raw)).toBe(vi);
  });

  it("resolves case/space-variant keys through the normalizer", () => {
    expect(overlayStyleVi("bold-center")).toBe("Chữ in đậm ở giữa");
    expect(overlayStyleVi("question xl")).toBe("Câu hỏi cỡ lớn");
  });

  it("falls back to the raw value when the code is unmapped", () => {
    expect(overlayStyleVi("FUTURE_STYLE")).toBe("FUTURE_STYLE");
    expect(overlayStyleVi("FUTURE_STYLE", "(không rõ)")).toBe("(không rõ)");
  });

  it("returns empty string for null/undefined without a fallback", () => {
    expect(overlayStyleVi(null)).toBe("");
    expect(overlayStyleVi(undefined)).toBe("");
  });
});

describe("sceneTypeVi", () => {
  it.each([
    ["face_to_camera", "Cận mặt"],
    ["product_shot", "Cận sản phẩm"],
    ["screen_recording", "Quay màn hình"],
    ["broll", "B-roll"],
    ["demo", "Demo sản phẩm"],
  ])("translates %s → %s", (raw, vi) => {
    expect(sceneTypeVi(raw)).toBe(vi);
  });
});

describe("firstFrameVi", () => {
  it("translates face_with_text — the exact leak the QA audit caught", () => {
    expect(firstFrameVi("face_with_text")).toBe("Cận mặt + chữ");
  });
});

describe("hookTimelineEventVi", () => {
  it("translates face_enter — the exact leak the QA audit caught", () => {
    expect(hookTimelineEventVi("face_enter")).toBe("Khuôn mặt xuất hiện");
  });
});
