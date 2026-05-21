import { env } from "@/lib/env";

/**
 * Standalone R2 frame URL builder. Lives in its own module (no supabase
 * import) so that side-effect-free callers (like the prerendered landing
 * page's hook ticker) don't drag the supabase client chunk into their
 * critical-path bundle.
 *
 * ``corpus-service.ts`` re-exports this for back-compat with the existing
 * call sites that already import it from there.
 */

function r2PublicBase(): string | null {
  const base = env.VITE_R2_PUBLIC_URL;
  if (!base) return null;
  return base.replace(/\/$/, "");
}

/** Derive a stable R2 frame URL for a video_id (frame 0 = ~0s thumbnail). */
export function r2FrameUrl(videoId: string): string | null {
  const base = r2PublicBase();
  if (!base || !videoId) return null;
  return `${base}/frames/${videoId}/0.png`;
}

/** Permanent R2 thumbnail keys written by batch ingest (png from frame copy, jpg from CDN mirror). */
export function r2ThumbnailUrl(videoId: string, ext: "png" | "jpg" = "png"): string | null {
  const base = r2PublicBase();
  if (!base || !videoId) return null;
  return `${base}/thumbnails/${videoId}.${ext}`;
}

/**
 * Ordered ``<img src>`` candidates for corpus rows: DB URL first (may still
 * be a fresh TikTok CDN link), then R2 ``thumbnails/`` (both extensions),
 * then ``frames/0.png``. Deduped; empty when nothing to try.
 */
export function corpusThumbnailSrcCandidates(
  videoId: string | null | undefined,
  thumbnailUrl: string | null | undefined,
): string[] {
  const out: string[] = [];
  const trimmed = thumbnailUrl?.trim();
  if (trimmed) out.push(trimmed);

  if (!videoId) return out;

  for (const url of [
    r2ThumbnailUrl(videoId, "png"),
    r2ThumbnailUrl(videoId, "jpg"),
    r2FrameUrl(videoId),
  ]) {
    if (url && !out.includes(url)) out.push(url);
  }
  return out;
}
