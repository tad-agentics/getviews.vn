/**
 * Formatting utilities for GetViews.vn
 * Vietnamese locale: dot separators for numbers, VND formatting
 */

/** Format VND with dot separator: 1.490.000 đ */
export function formatVND(amount: number): string {
  return amount.toLocaleString("vi-VN") + " đ";
}

/** Format view count: 1.2M, 45K, 3.5K */
export function formatViews(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return count.toString();
}

/** Format follower count */
export function formatFollowers(count: number): string {
  return formatViews(count);
}

/** Format engagement rate: 4.2% */
export function formatER(rate: number): string {
  return `${rate.toFixed(1)}%`;
}

/** Format multiplier: 3.2x */
export function formatMultiplier(value: number): string {
  return `${value.toFixed(1)}x`;
}

/** Format timestamp to Vietnamese date: 08/04/2026 */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Format seconds to mm:ss for video timestamps */
export function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/**
 * Format a number with Vietnamese thousand separator (dot).
 * Vietnamese uses '.' for thousands: 1.100, 46.000, 1.623.886
 */
export function formatVN(n: number): string {
  return Math.round(n)
    .toLocaleString("en-US")
    .replace(/,/g, ".");
}

/**
 * Format a recency value (days ago) as natural Vietnamese.
 * "Hôm nay", "Hôm qua", "3 ngày trước", "Tuần trước", "2 tuần trước", "1 tháng trước"
 */
export function formatRecencyVI(daysAgo: number): string {
  if (daysAgo === 0) return "Hôm nay";
  if (daysAgo === 1) return "Hôm qua";
  if (daysAgo <= 7) return `${daysAgo} ngày trước`;
  if (daysAgo <= 14) return "Tuần trước";
  if (daysAgo <= 30) return `${Math.floor(daysAgo / 7)} tuần trước`;
  return `${Math.floor(daysAgo / 30)} tháng trước`;
}

/**
 * Format a breakout multiplier with Vietnamese decimal separator (comma).
 * Vietnamese uses ',' for decimals: "3,2x" not "3.2x"
 */
export function formatBreakoutVI(ratio: number): string {
  return `${ratio.toFixed(1).replace(".", ",")}x`;
}
