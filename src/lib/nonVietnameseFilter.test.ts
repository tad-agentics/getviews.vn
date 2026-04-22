/**
 * BUG-14 regression: Chinese / Korean / Japanese captions leaking into the
 * Vietnamese-market niche feed because the backend mis-tagged them as
 * ``language='vi'``. The client-side heuristic is a stopgap until the
 * analyse pipeline is tightened.
 */
import { describe, expect, it } from "vitest";

import { countCjkCharacters, looksLikeNonVietnameseCaption } from "./nonVietnameseFilter";

describe("countCjkCharacters", () => {
  it("counts Han ideographs", () => {
    expect(countCjkCharacters("沉浸式早八")).toBe(5);
  });

  it("counts Hangul + Hiragana + Katakana", () => {
    expect(countCjkCharacters("淡颜韩系日常妆")).toBe(7);
    expect(countCjkCharacters("おはよう")).toBe(4);
    expect(countCjkCharacters("メイク")).toBe(3);
    expect(countCjkCharacters("한글테스트")).toBe(5);
  });

  it("returns 0 for Vietnamese text", () => {
    expect(countCjkCharacters("Chào buổi sáng các bạn")).toBe(0);
    expect(countCjkCharacters("Đang làm video skincare cho da dầu")).toBe(0);
  });

  it("handles null / undefined / empty", () => {
    expect(countCjkCharacters(null)).toBe(0);
    expect(countCjkCharacters(undefined)).toBe(0);
    expect(countCjkCharacters("")).toBe(0);
  });
});

describe("looksLikeNonVietnameseCaption", () => {
  it("flags the exact caption from the QA audit", () => {
    expect(looksLikeNonVietnameseCaption("沉浸式早八 淡颜韩系日常妆")).toBe(true);
  });

  it("flags pure Chinese / Korean content", () => {
    expect(looksLikeNonVietnameseCaption("这是一个测试视频")).toBe(true);
    expect(looksLikeNonVietnameseCaption("안녕하세요 테스트")).toBe(true);
  });

  it("leaves pure Vietnamese captions alone", () => {
    expect(looksLikeNonVietnameseCaption("Hướng dẫn make up hàn quốc cho gái Việt")).toBe(false);
    expect(looksLikeNonVietnameseCaption("POV: lần đầu thử son Hàn")).toBe(false);
  });

  it("leaves borderline bilingual captions visible", () => {
    // Mostly Vietnamese with a small CJK loan — stays in the feed.
    expect(looksLikeNonVietnameseCaption("vlog 東京 travel ngày 3")).toBe(false);
  });

  it("returns false for null / empty input", () => {
    expect(looksLikeNonVietnameseCaption(null)).toBe(false);
    expect(looksLikeNonVietnameseCaption("")).toBe(false);
    expect(looksLikeNonVietnameseCaption(undefined)).toBe(false);
  });

  it("threshold is tunable", () => {
    // At the default 25% threshold "vlog 東京" is below (2/9 = 22%).
    expect(looksLikeNonVietnameseCaption("vlog 東京 travel")).toBe(false);
    // At 15% threshold it's above.
    expect(looksLikeNonVietnameseCaption("vlog 東京 travel", 0.15)).toBe(true);
  });
});
