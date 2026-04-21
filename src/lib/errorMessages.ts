/**
 * Translate the named analysis errors thrown by Cloud Run hooks into
 * the Vietnamese copy shown on /app/video, /app/channel, /app/script,
 * and anywhere else a cloud-run analysis can fail.
 *
 * Hooks throw `new Error("insufficient_credits")` with
 * `err.name = "InsufficientCredits"` (and similar for
 * `DailyFreeLimit`). The name is the reliable branch key — message
 * strings in Vietnamese render directly and should stay out of
 * `throw new Error(...)` to avoid i18n coupling.
 *
 * Anything this helper doesn't recognize falls through to the original
 * `error.message`, preserving existing behaviour for unclassified
 * failures.
 */
export function analysisErrorCopy(error: unknown): string {
  if (!(error instanceof Error)) return "Lỗi không xác định";

  if (error.name === "InsufficientCredits" || error.message === "insufficient_credits") {
    return "Không đủ credit. Kiểm tra số dư ở Cài đặt hoặc dùng thao tác miễn phí.";
  }

  if (error.name === "DailyFreeLimit" || error.message === "daily_free_limit") {
    return "Đã hết lượt miễn phí hôm nay. Quota sẽ reset lúc 00:00 UTC, hoặc dùng credit trả phí.";
  }

  return error.message || "Lỗi không xác định";
}
