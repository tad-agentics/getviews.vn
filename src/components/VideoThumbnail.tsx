import { useState } from "react";

/**
 * Single shared video-thumbnail renderer with proper error fallback.
 *
 * Replaces the ~6 raw ``<img src={thumbnail_url}>`` callsites that
 * had no ``onError`` handler — those rendered the browser's default
 * broken-image icon when the underlying URL went stale (TikTok CDN
 * URLs rotate every few weeks; older corpus rows hit this commonly).
 *
 * After PR #282, new ingests write a permanent R2 URL to
 * ``video_corpus.thumbnail_url`` derived from frame[0]. After the
 * legacy backfill (PR-B), every recoverable row will also have an
 * R2 URL. The remaining cases — frame extraction failed AND the CDN
 * URL has already expired — render a clean placeholder via this
 * component, never a broken-icon.
 *
 * Architectural note: the component **trusts** ``thumbnailUrl``. We
 * don't try a fallback chain on the FE (R2 derived URL guesswork).
 * The data layer is the right place to make ``thumbnail_url``
 * reliable; the FE just renders it or its placeholder.
 */
export type VideoThumbnailProps = {
  /** The thumbnail URL to render. Null / empty / whitespace → placeholder. */
  thumbnailUrl: string | null | undefined;
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
        onError={() => setFailed(true)}
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
