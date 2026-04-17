/**
 * VideoThumb — universal 9:16 thumbnail component for corpus video citations.
 *
 * Fixes two VideoRefCard bugs:
 *  1. imgFailed is React state (not DOM mutation), so the TikTok icon fallback renders correctly.
 *  2. Width is controlled by the parent via className — no hardcoded style.
 *
 * Renders gradient overlays so handle/views/recency are readable on the image itself.
 */
import { useState, useEffect } from "react";
import { Play } from "lucide-react";
import { formatVN, formatRecencyVI } from "@/lib/formatters";

export interface VideoThumbProps {
  thumbnail?: string | null;
  handle?: string;
  views?: number;
  daysAgo?: number | null;
  tiktokUrl?: string | null;
  videoUrl?: string | null;
  className?: string;
}

export function VideoThumb({
  thumbnail,
  handle,
  views,
  daysAgo,
  tiktokUrl,
  videoUrl,
  className = "",
}: VideoThumbProps) {
  const [imgFailed, setImgFailed] = useState(false);
  const [playing, setPlaying] = useState(false);

  // Reset on thumbnail change so switching to a different video retries the image.
  useEffect(() => {
    setImgFailed(false);
    setPlaying(false);
  }, [thumbnail]);

  const showImage = !!thumbnail && !imgFailed;
  const showOverlays = showImage && !playing;

  const inner = (
    <div
      className={`relative w-full overflow-hidden bg-[var(--surface-alt)] ${className}`}
      style={{ paddingBottom: "177.78%" /* 9:16 */ }}
    >
      {/* ── Video playback ── */}
      {playing && videoUrl ? (
        <video
          src={videoUrl}
          autoPlay
          controls
          playsInline
          className="absolute inset-0 h-full w-full object-cover"
          onClick={(e) => e.stopPropagation()}
        />
      ) : showImage ? (
        <img
          src={thumbnail!}
          alt={handle ?? ""}
          className="absolute inset-0 h-full w-full object-cover"
          loading="lazy"
          onError={() => setImgFailed(true)}
        />
      ) : (
        /* No thumbnail or load failed */
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-[var(--surface-alt)]">
          <svg className="h-7 w-7 opacity-60" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path fill="#69C9D0" d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"/>
            <path fill="#EE1D52" d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"/>
          </svg>
          <p className="text-center text-[9px] leading-tight text-[var(--faint)] px-1">Xem trên TikTok</p>
        </div>
      )}

      {/* ── Top gradient overlay ── */}
      {showOverlays && (
        <div className="pointer-events-none absolute inset-x-0 top-0 h-12 bg-gradient-to-b from-black/50 to-transparent">
          <div className="flex items-start justify-between px-1.5 pt-1.5">
            {handle ? (
              <span className="max-w-[70%] truncate text-[10px] font-semibold leading-tight text-white/90">
                {handle}
              </span>
            ) : <span />}
            {/* TikTok icon top-right */}
            <svg className="h-3.5 w-3.5 flex-shrink-0 opacity-80" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path fill="#69C9D0" d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"/>
              <path fill="#EE1D52" d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"/>
            </svg>
          </div>
        </div>
      )}

      {/* ── Bottom gradient overlay ── */}
      {showOverlays && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-black/60 to-transparent">
          <div className="flex items-end justify-between px-1.5 pb-1.5">
            {views != null && views > 0 ? (
              <span className="font-mono text-[10px] font-semibold tabular-nums text-white/90">
                {formatVN(views)} views
              </span>
            ) : <span />}
            {daysAgo != null ? (
              <span className="text-[10px] text-white/70">{formatRecencyVI(daysAgo)}</span>
            ) : null}
          </div>
        </div>
      )}

      {/* ── Play button overlay ── */}
      {!playing && videoUrl && (
        <button
          type="button"
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); setPlaying(true); }}
          className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity duration-150 hover:opacity-100"
          aria-label="Xem video"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/80">
            <Play className="h-5 w-5 text-[var(--ink)]" fill="currentColor" />
          </div>
        </button>
      )}
    </div>
  );

  if (tiktokUrl) {
    return (
      <a href={tiktokUrl} target="_blank" rel="noopener noreferrer" className="block">
        {inner}
      </a>
    );
  }
  return inner;
}
