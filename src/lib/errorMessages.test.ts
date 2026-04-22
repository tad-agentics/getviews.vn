/**
 * analysisErrorCopy — Cloud Run analysis error → Vietnamese copy.
 *
 * Protects the branch keys the hooks actually throw so a rename of
 * `err.name` in a future hook refactor fails this test rather than
 * shipping a generic "HTTP 402" banner to a user who's out of credits.
 */
import { describe, expect, it } from "vitest";
import { analysisErrorCopy } from "./errorMessages";

describe("analysisErrorCopy", () => {
  it("returns the credits-specific copy for err.name InsufficientCredits", () => {
    const e = new Error("insufficient_credits");
    e.name = "InsufficientCredits";
    expect(analysisErrorCopy(e)).toMatch(/Không đủ credit/);
  });

  it("returns the credits copy when the message matches even without the name", () => {
    // Back-compat with older throw sites that set only the message.
    const e = new Error("insufficient_credits");
    expect(analysisErrorCopy(e)).toMatch(/Không đủ credit/);
  });

  it("returns the daily-free-limit copy for err.name DailyFreeLimit", () => {
    const e = new Error("daily_free_limit");
    e.name = "DailyFreeLimit";
    expect(analysisErrorCopy(e)).toMatch(/hết lượt miễn phí/);
  });

  it("falls through to the raw message for unclassified errors", () => {
    const e = new Error("HTTP 502");
    expect(analysisErrorCopy(e)).toBe("HTTP 502");
  });

  it("handles non-Error values defensively", () => {
    expect(analysisErrorCopy("something")).toBe("Lỗi không xác định");
    expect(analysisErrorCopy(null)).toBe("Lỗi không xác định");
    expect(analysisErrorCopy(undefined)).toBe("Lỗi không xác định");
  });

  it("falls through to 'Lỗi không xác định' when message is empty", () => {
    const e = new Error("");
    expect(analysisErrorCopy(e)).toBe("Lỗi không xác định");
  });

  it.each([
    ["start_failed", /Không tạo được phiên/],
    ["follow_up_failed", /Câu hỏi tiếp theo chưa gửi được/],
    ["stream_failed", /Kết nối streaming bị ngắt/],
    ["stream_timeout", /Server im lặng quá lâu/],
    ["session_not_found", /Phiên không tồn tại/],
    ["no_cloud_run", /VITE_CLOUD_RUN_API_URL/],
    ["aborted", /đã bị huỷ/],
    ["auth", /Chưa đăng nhập/],
    ["http_500", /HTTP 500/],
    ["http_503", /HTTP 503/],
  ])("translates the AnswerScreen error code %s to Vietnamese", (code, re) => {
    expect(analysisErrorCopy(code)).toMatch(re);
  });

  it("passes raw code through when wrapped in Error, but not when a bare string", () => {
    // Unknown Error wraps fall through (matches legacy hook behaviour —
    // some hooks throw Vietnamese messages directly).
    expect(analysisErrorCopy(new Error("xin chào"))).toBe("xin chào");
    // Unknown raw strings are suppressed so English/server junk never
    // leaks to the user.
    expect(analysisErrorCopy("random_code")).toBe("Lỗi không xác định");
  });
});
