import { useState } from "react";
import { env } from "@/lib/env";

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
 * slide[0] (carousels). The remaining cases — frame extraction failed AND
 * the CDN URL has already expired — render a clean placeholder via this
 * component, never a broken-icon.
 *
 * Observability: onError fires a one-shot beacon to the
 * ``track-thumbnail-failure`` Edge Function so ops can see the failure
 * rate in the admin panel. De-duplicated per video_id per page load
 * via a module-level Set so remounts don't double-count.
 *
 * Architectural note: the component **trusts** ``thumbnailUrl``. We
 * don't try a fallback chain on the FE (R2 derived URL guesswork).
 * The data layer is the right place to make ``thumbnail_url``
 * reliable; the FE just renders it or its placeholder.
 */

/** Session-scoped dedup: fire at most one beacon per video_id per page load. */
const _reported = new Set<string>();

function _reportThumbnailFailure(videoId: string | undefined, failedUrl: string): void {
  // De-duplicate when we have a stable video_id; skip dedup otherwise (still report).
  if (videoId) {
    if (_reported.has(videoId)) return;
    _reported.add(videoId);
  }
  console.warn("[VideoThumbnail] load failed", { videoId, failedUrl });
  try {
    const endpoint = `${env.VITE_SUPABASE_URL}/functions/v1/track-thumbnail-failure`;
    const payload = JSON.stringify({ video_id: videoId, failed_url: failedUrl });
    // sendBeacon is fire-and-forget; does not block navigation.
    if (typeof navigator !== "undefined" && navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([payload], { type: "application/json" }));
    }
  } catch {
    // Non-fatal — beacon failure must not affect the component.
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
}: VideoThumbnailProps) {
  const [failed, setFailed] = useState(false);
  const url = thumbnailUrl?.trim() || null;

  if (url && !failed) {
    return (
      <img
        src={url}
        alt={alt}
        className={`object-cover ${className}`.trim()}
        loading={loading}
        fetchPriority={fetchPriority}
        onError={() => {
          setFailed(true);
          _reportThumbnailFailure(videoId ?? undefined, url);
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
