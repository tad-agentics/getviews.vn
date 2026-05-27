/**
 * Formatting utilities for GetViews.vn
 * Vietnamese locale: dot separators for numbers, VND formatting
 */

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

/** Format timestamp to Vietnamese date: 08/04/2026 */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
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
 * Marketing corpus size for landing/login copy — floor to humility tier, never over-claim.
 * Uses indexed rows (content_class_id set) when available.
 */
export function formatCorpusMarketingCount(indexedCount: number | null | undefined): string {
  if (indexedCount == null || indexedCount < 100) return "1.500+";
  const step = indexedCount >= 5_000 ? 1_000 : 100;
  const floored = Math.floor(indexedCount / step) * step;
  return `${formatVN(floored)}+`;
}

/** Vietnam civil calendar for sidebar/history recency buckets. */
export const VN_TIME_ZONE = "Asia/Ho_Chi_Minh";

function dateKeyInTimeZone(when: Date, timeZone: string): string {
  return when.toLocaleDateString("en-CA", { timeZone });
}

/** Whole calendar days between ``iso`` and ``now`` in Vietnam (not UTC midnight). */
export function calendarDaysAgoInVn(iso: string, now = new Date()): number {
  const a = dateKeyInTimeZone(new Date(iso), VN_TIME_ZONE);
  const b = dateKeyInTimeZone(now, VN_TIME_ZONE);
  const [ay, am, ad] = a.split("-").map(Number);
  const [by, bm, bd] = b.split("-").map(Number);
  const utcA = Date.UTC(ay, am - 1, ad);
  const utcB = Date.UTC(by, bm - 1, bd);
  return Math.round((utcB - utcA) / 86_400_000);
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

/** Sidebar / history row — ISO timestamp → ``formatRecencyVI`` bucket (VN calendar). */
export function formatSessionRecencyFromIso(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const daysAgo = calendarDaysAgoInVn(iso, now);
  const bucket = formatRecencyVI(daysAgo);
  if (daysAgo === 0) {
    const time = new Date(iso).toLocaleTimeString("vi-VN", {
      timeZone: VN_TIME_ZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    return `Hôm nay · ${time}`;
  }
  return bucket;
}

/**
 * Format a breakout multiplier with Vietnamese decimal separator (comma).
 * Vietnamese uses ',' for decimals: "3,2x" not "3.2x"
 */
export function formatBreakoutVI(ratio: number): string {
  return `${ratio.toFixed(1).replace(".", ",")}x`;
}

/**
 * h3 section titles in video diagnosis — sentence case (not ALL CAPS kickers).
 * Leaves mixed-case BE/FE titles unchanged (e.g. "Khung giờ đăng trong ngách").
 */
export function formatDiagnosisSectionTitle(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return trimmed;

  const letters = [...trimmed].filter((ch) => /\p{L}/u.test(ch));
  if (letters.length === 0) return trimmed;

  const upperCount = letters.filter((ch) => {
    const lower = ch.toLocaleLowerCase("vi-VN");
    const upper = ch.toLocaleUpperCase("vi-VN");
    return ch === upper && ch !== lower;
  }).length;

  if (upperCount / letters.length < 0.85) return trimmed;

  const lower = trimmed.toLocaleLowerCase("vi-VN");
  return lower.charAt(0).toLocaleUpperCase("vi-VN") + lower.slice(1);
}

/** Natural Vietnamese relative time from `since` to `now` (minutes/hours/days). */
export function formatRelativeSinceVi(now: Date, since: Date | null): string {
  if (!since) return "—";
  const mins = Math.floor((now.getTime() - since.getTime()) / 60000);
  if (mins < 2) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
}
