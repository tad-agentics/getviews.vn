import { useEffect, useMemo, useState } from "react";
import { env } from "@/lib/env";
import { corpusThumbnailSrcCandidates } from "@/lib/r2";

/**
 * Single shared video-thumbnail renderer with proper error fallback.
 *
 * Replaces the ~6 raw ``<img src={thumbnail_url}>`` callsites that
 * had no ``onError`` handler — those rendered the browser's default
 * broken-image icon when the underlying URL went stale (TikTok CDN
 * URLs rotate every few weeks; older corpus rows hit this commonly).
 *
 * After the R2 hardening (May 2026), new ingests write a permanent R2 URL to
 * ``video_corpus.thumbnail_url`` derived from frame[0] (videos) or
 * slide[0] (carousels) as 360w WebP. The remaining cases — frame extraction
 * the CDN URL has already expired — render a clean placeholder via this
 * component, never a broken-icon.
 *
 * Observability: onError fires a one-shot POST to the
 * ``track-thumbnail-failure`` Edge Function so ops can see the failure
 * rate in the admin panel. Uses ``fetch(..., { keepalive: true,
 * credentials: 'omit' })`` — not ``sendBeacon`` — so CORS stays valid
 * with Supabase's gateway. De-duplicated per video_id per page load.
 *
 * Fallback: when ``videoId`` is set and ``VITE_R2_PUBLIC_URL`` is
 * configured, expired TikTok CDN URLs in ``thumbnailUrl`` fall through to
 * R2 ``thumbnails/{id}.webp`` then legacy ``.png`` / ``.jpg`` (same keys
 * batch ingest writes). Skips heavy ``frames/{id}/0.png``. Telemetry fires
 */

/** Session-scoped dedup: fire at most one beacon per video_id per page load. */
const _reported = new Set<string>();

function _reportThumbnailFailure(videoId: string | undefined, failedUrl: string): void {
  // De-duplicate when we have a stable video_id; skip dedup otherwise (still report).
  if (videoId) {
    if (_reported.has(videoId)) return;
    _reported.add(videoId);
  }
  if (import.meta.env.DEV) {
    console.warn("[VideoThumbnail] load failed", { videoId, failedUrl });
  }
  try {
    const endpoint = `${env.VITE_SUPABASE_URL}/functions/v1/track-thumbnail-failure`;
    const payload = JSON.stringify({ video_id: videoId, failed_url: failedUrl });
    void fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: env.VITE_SUPABASE_PUBLISHABLE_KEY,
      },
      body: payload,
      credentials: "omit",
      keepalive: true,
      mode: "cors",
    }).catch(() => {
      // Non-fatal — telemetry failure must not affect the component.
    });
  } catch {
    // Non-fatal — telemetry failure must not affect the component.
  }
}
export type VideoThumbnailProps = {
  /** The thumbnail URL to render. Null / empty / whitespace → placeholder. */
  thumbnailUrl: string | null | undefined;
  /**
   * The corpus video_id for the thumbnail. Used to de-duplicate failure
   * beacons — at most one report per video_id per page load. Optional:
   * if omitted the beacon is still fired but not de-duplicated.
   */
  videoId?: string | null;
  /** Sizing + layout classes. The component controls ``object-cover`` itself. */
  className?: string;
  /**
   * Placeholder classes used when ``thumbnailUrl`` is missing or the
   * image fails to load. Defaults to a neutral canvas-2 block. Pass
   * a custom palette (e.g. a creator-specific avatar gradient) when
   * the surrounding card already implies one.
   */
  placeholderClassName?: string;
  /** Optional inline placeholder background (hex / gradient / token). */
  placeholderStyle?: React.CSSProperties;
  /** Image alt text. Defaults to "" (decorative). */
  alt?: string;
  /** Lazy-load by default; pass "eager" for above-fold thumbs. */
  loading?: "lazy" | "eager";
  /** Browser fetch priority hint. ``high`` for above-fold. */
  fetchPriority?: "auto" | "high" | "low";
  /** ``cover`` fills frame (may crop); ``contain`` shows full frame (letterbox). */
  objectFit?: "cover" | "contain";
};

export function VideoThumbnail({
  thumbnailUrl,
  videoId,
  className = "",
  placeholderClassName = "bg-[color:var(--gv-canvas-2)]",
  placeholderStyle,
  alt = "",
  loading = "lazy",
  fetchPriority = "auto",
  objectFit = "cover",
}: VideoThumbnailProps) {
  const candidates = useMemo(
    () => corpusThumbnailSrcCandidates(videoId, thumbnailUrl),
    [videoId, thumbnailUrl],
  );
  const [candidateIndex, setCandidateIndex] = useState(0);

  useEffect(() => {
    setCandidateIndex(0);
  }, [candidates]);

  const url = candidates[candidateIndex] ?? null;
  const exhausted = candidates.length === 0 || candidateIndex >= candidates.length;

  if (url && !exhausted) {
    return (
      <img
        src={url}
        alt={alt}
        className={`${objectFit === "contain" ? "object-contain" : "object-cover"} ${className}`.trim()}
        loading={loading}
        fetchPriority={fetchPriority}
        onError={() => {
          const nextIndex = candidateIndex + 1;
          if (nextIndex < candidates.length) {
            setCandidateIndex(nextIndex);
            return;
          }
          setCandidateIndex(candidates.length);
          _reportThumbnailFailure(
            videoId ?? undefined,
            candidates[0] ?? thumbnailUrl?.trim() ?? url,
          );
        }}
      />
    );
  }
  return (
    <div
      className={`${placeholderClassName} ${className}`.trim()}
      style={placeholderStyle}
      aria-hidden
    />
  );
}
