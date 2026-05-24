import type { DouyinVideo } from "@/lib/api-types";

const LAST_VISIT_KEY = "gv-douyin-last-visit-at";

export function readDouyinLastVisitAt(): number {
  if (typeof window === "undefined") return 0;
  try {
    const raw = window.localStorage.getItem(LAST_VISIT_KEY);
    if (!raw) return 0;
    const t = new Date(raw).getTime();
    return Number.isFinite(t) ? t : 0;
  } catch {
    return 0;
  }
}

export function hasDouyinVisitBaseline(): boolean {
  return readDouyinLastVisitAt() > 0;
}

export function markDouyinFeedVisited(at: Date = new Date()): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(LAST_VISIT_KEY, at.toISOString());
  } catch {
    /* quota — ignore */
  }
}

/** First feed load — baseline so existing corpus is not counted as ``MỚI``. */
export function seedDouyinVisitBaselineIfAbsent(at: Date = new Date()): void {
  if (typeof window === "undefined") return;
  if (hasDouyinVisitBaseline()) return;
  markDouyinFeedVisited(at);
}

const DOUYIN_BADGE_CAP = 99;

/** Sidebar accent pill label; ``undefined`` when nothing to show. */
export function formatDouyinNewBadge(count: number): string | undefined {
  if (count <= 0) return undefined;
  const n = count > DOUYIN_BADGE_CAP ? `${DOUYIN_BADGE_CAP}+` : String(count);
  return `🇨🇳 ${n} MỚI`;
}

/** Videos indexed after the user's last Kho Douyin visit (sidebar badge). */
export function countDouyinNewVideos(
  videos: DouyinVideo[],
  lastVisitMs = readDouyinLastVisitAt(),
): number {
  if (videos.length === 0 || lastVisitMs <= 0) return 0;
  return videos.filter((v) => {
    if (!v.indexed_at) return false;
    const t = new Date(v.indexed_at).getTime();
    return Number.isFinite(t) && t > lastVisitMs;
  }).length;
}
