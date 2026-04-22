/**
 * Translate the named analysis errors thrown by Cloud Run hooks into
 * the Vietnamese copy shown on /app/video, /app/channel, /app/script,
 * /app/answer and anywhere else a cloud-run analysis can fail.
 *
 * Hooks throw `new Error("insufficient_credits")` with
 * `err.name = "InsufficientCredits"` (and similar for
 * `DailyFreeLimit`). The name is the reliable branch key — message
 * strings in Vietnamese render directly and should stay out of
 * `throw new Error(...)` to avoid i18n coupling.
 *
 * Accepts either an `Error` instance (4-hook pattern) or a raw string
 * error code (AnswerScreen stores codes in local state). Anything the
 * helper doesn't recognise falls through to the original `error.message`
 * / raw code, preserving existing behaviour for unclassified failures.
 */
export function analysisErrorCopy(error: unknown): string {
  // Normalise: accept either `Error` objects (from the four analysis
  // hooks) or raw error-code strings (AnswerScreen state is a string).
  const name = error instanceof Error ? error.name : "";
  const code =
    error instanceof Error
      ? error.message
      : typeof error === "string"
        ? error
        : "";

  if (!name && !code) return "Lỗi không xác định";

  if (name === "InsufficientCredits" || code === "insufficient_credits") {
    return "Không đủ credit. Kiểm tra số dư ở Cài đặt hoặc dùng thao tác miễn phí.";
  }

  if (name === "DailyFreeLimit" || code === "daily_free_limit") {
    return "Đã hết lượt miễn phí hôm nay. Quota sẽ reset lúc 00:00 UTC, hoặc dùng credit trả phí.";
  }

  if (name === "FetchTimeout" || code === "fetch_timeout") {
    return "Yêu cầu quá lâu — hệ thống đang chậm. Thử lại sau ít giây.";
  }

  if (name === "SessionExpired" || code === "session_expired") {
    return "Phiên đăng nhập đã hết hạn — tự động đăng xuất sau giây lát.";
  }

  // AnswerScreen codes — these are stored as raw strings in state and
  // rendered via `analysisErrorCopy(error)`.
  if (code === "start_failed") {
    return "Không tạo được phiên nghiên cứu. Kiểm tra kết nối rồi thử lại.";
  }
  if (code === "follow_up_failed") {
    return "Câu hỏi tiếp theo chưa gửi được. Thử lại sau vài giây.";
  }
  if (code === "stream_failed") {
    return "Kết nối streaming bị ngắt. Thử gửi lại câu hỏi.";
  }
  if (code === "stream_timeout") {
    return "Server im lặng quá lâu — có thể đang quá tải. Thử lại sau ít giây.";
  }
  if (code === "session_not_found") {
    return "Phiên không tồn tại hoặc đã bị xoá. Mở phiên khác từ Lịch sử.";
  }
  if (code === "no_cloud_run") {
    return "Dịch vụ phân tích chưa cấu hình (VITE_CLOUD_RUN_API_URL).";
  }
  if (code === "aborted") {
    return "Yêu cầu đã bị huỷ.";
  }
  if (code === "auth") {
    return "Chưa đăng nhập. Đăng nhập lại để tiếp tục.";
  }
  // http_<status> codes from the SSE path.
  if (code.startsWith("http_")) {
    const status = code.slice(5);
    return `Server trả lỗi (HTTP ${status}). Thử lại sau ít giây.`;
  }

  // Error-instance inputs keep the historical fall-through — hooks
  // often throw Vietnamese messages directly and we want those to
  // render. Raw string inputs that didn't match a known code are
  // almost certainly English/server junk; suppress them.
  if (error instanceof Error) {
    return error.message || "Lỗi không xác định";
  }
  return "Lỗi không xác định";
}
