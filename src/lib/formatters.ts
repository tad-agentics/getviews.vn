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
