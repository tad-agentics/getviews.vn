import { isStableR2ThumbnailUrl } from "@/lib/r2";

export const PATTERN_COLLAGE_LIMIT = 4;

export type PatternThumbRow = {
  video_id: string;
  thumbnail_url: string | null;
  views: number;
};

export function sortPatternVideosByViews<T extends PatternThumbRow>(
  rows: ReadonlyArray<T>,
): T[] {
  return [...rows].sort((a, b) => b.views - a.views);
}

/**
 * Pattern cards/modals only surface videos whose DB thumb is a stable R2 URL.
 * ``pool`` is the full sorted stable set — collage/modal swap here on load failure.
 */
export function pickPatternDisplayVideos<T extends PatternThumbRow>(
  rows: ReadonlyArray<T>,
  limit = PATTERN_COLLAGE_LIMIT,
): { display: T[]; pool: T[] } {
  const pool = sortPatternVideosByViews(
    rows.filter((row) => Boolean(row.video_id) && isStableR2ThumbnailUrl(row.thumbnail_url)),
  );
  return {
    display: pool.slice(0, limit),
    pool,
  };
}

/**
 * Swap a tile whose thumb failed to load. Tracks ``failedIds`` so we never
 * ping-pong back to a video that already failed in this strip/modal session.
 */
export function applyPatternThumbFailure<T extends PatternThumbRow>(
  prev: readonly T[],
  failedVideoId: string,
  pool: readonly T[],
  failedIds: Set<string>,
): T[] {
  failedIds.add(failedVideoId);
  const shown = new Set(prev.map((row) => row.video_id));
  const replacement = pool.find(
    (row) =>
      row.video_id !== failedVideoId &&
      !shown.has(row.video_id) &&
      !failedIds.has(row.video_id),
  );
  if (!replacement) {
    const next = prev.filter((row) => row.video_id !== failedVideoId);
    return next.length > 0 ? [...next] : [...prev];
  }
  return prev.map((row) => (row.video_id === failedVideoId ? replacement : row));
}
