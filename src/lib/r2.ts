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

export function r2PublicBase(): string | null {
  const base = env.VITE_R2_PUBLIC_URL;
  if (!base) return null;
  return base.replace(/\/$/, "");
}

/** True when ``thumbnail_url`` is a non-empty permanent R2 public URL (not TikTok CDN). */
export function isStableR2ThumbnailUrl(thumbnailUrl: string | null | undefined): boolean {
  const trimmed = thumbnailUrl?.trim();
  if (!trimmed) return false;
  const base = r2PublicBase();
  if (!base) return false;
  return trimmed.startsWith(base);
}

/** Derive a stable R2 frame URL for a video_id (frame 0 = ~0s thumbnail). */
export function r2FrameUrl(videoId: string): string | null {
  const base = r2PublicBase();
  if (!base || !videoId) return null;
  return `${base}/frames/${videoId}/0.png`;
}

/** Permanent R2 thumbnail keys — WebP (default), legacy png/jpg fallbacks. */
export function r2ThumbnailUrl(
  videoId: string,
  ext: "webp" | "png" | "jpg" = "webp",
): string | null {
  const base = r2PublicBase();
  if (!base || !videoId) return null;
  return `${base}/thumbnails/${videoId}.${ext}`;
}

/** Permanent R2 hosted MP4 for hover preview (may 404 if clip not banked yet). */
export function r2VideoPlaybackUrl(videoId: string): string | null {
  const base = r2PublicBase();
  if (!base || !videoId) return null;
  return `${base}/videos/${videoId}.mp4`;
}

/**
 * Ordered ``<img src>`` candidates for corpus rows: R2 WebP first (360w,
 * ~15–45 KB), then DB ``thumbnail_url`` (CDN or legacy R2 png), then
 * legacy R2 png/jpg. Skips ``frames/0.png`` — same 720px PNG as legacy
 * thumbnails and too heavy for card grids.
 */
export function corpusThumbnailSrcCandidates(
  videoId: string | null | undefined,
  thumbnailUrl: string | null | undefined,
): string[] {
  const out: string[] = [];
  const push = (url: string | null | undefined) => {
    if (url && !out.includes(url)) out.push(url);
  };

  const trimmed = thumbnailUrl?.trim();

  if (videoId) {
    push(r2ThumbnailUrl(videoId, "webp"));
  }
  push(trimmed);
  if (videoId) {
    push(r2ThumbnailUrl(videoId, "png"));
    push(r2ThumbnailUrl(videoId, "jpg"));
  }
  return out;
}
