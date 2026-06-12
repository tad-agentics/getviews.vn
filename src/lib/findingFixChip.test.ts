/**
 * Live audit 2026-06-12 — "Sửa: Tiếp tục sử dụng…" rendered a corrective
 * chip on keep-advice. Keep-verbs must flip the chip to "Giữ"/positive.
 */
import { describe, expect, it } from "vitest";

import { fixChipMeta } from "./findingFixChip";

describe("fixChipMeta", () => {
  it.each([
    "Tiếp tục sử dụng hook dạng câu hỏi ở 0-1s.",
    "tiếp tục giữ nhịp cắt 1.2s/cảnh.",
    "Giữ nguyên giọng đọc hiện tại.",
    "Giữ format talking head cho 3 video tới.",
    "Nhân bản cấu trúc 3 beat của video này.",
    "Duy trì tần suất 4 video/tuần.",
  ])("labels keep-advice as Giữ/positive: %s", (fix) => {
    expect(fixChipMeta(fix)).toEqual({ label: "Giữ", positive: true });
  });

  it.each([
    "Đổi hook sang câu hỏi đảo trong 1s đầu.",
    "Cắt cảnh tĩnh 0-3s, mở bằng chuyển động.",
    "Thêm text overlay ở giây thứ 2.",
  ])("labels corrective fixes as Sửa: %s", (fix) => {
    expect(fixChipMeta(fix)).toEqual({ label: "Sửa", positive: false });
  });

  it("does not match keep-verbs mid-sentence", () => {
    expect(fixChipMeta("Đổi hook, sau đó tiếp tục đăng đều.").label).toBe("Sửa");
  });

  it("defaults to Sửa for empty/null", () => {
    expect(fixChipMeta("").label).toBe("Sửa");
    expect(fixChipMeta(null).label).toBe("Sửa");
    expect(fixChipMeta(undefined).label).toBe("Sửa");
  });
});
