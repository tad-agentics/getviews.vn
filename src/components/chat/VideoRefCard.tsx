/**
 * VideoRefCard — thumbnail reference card for corpus video citations.
 *
 * Rendered when Gemini synthesis outputs a video_ref JSON block:
 * {"type":"video_ref","video_id":"xxx","handle":"@creator","views":1100000,"days_ago":6}
 *
 * Tap thumbnail → open TikTok link (whole thumbnail area is clickable)
 * Play button → inline video playback from R2 video_url (when available)
 */
import { useState, useEffect } from "react";
import { ExternalLink, Play } from "lucide-react";
import { getVideoMeta, r2FrameUrl, type VideoMeta } from "@/lib/services/corpus-service";
import { formatVN, formatRecencyVI, formatBreakoutVI } from "@/lib/formatters";

export interface VideoRefData {
  type: "video_ref";
  video_id: string;
  handle: string;
  views: number;
  days_ago: number;
  breakout?: number; // ratio e.g. 3.2 → "3,2x"
}

interface Props {
  data: VideoRefData;
}

export function VideoRefCard({ data }: Props) {
  const [meta, setMeta] = useState<VideoMeta | null>(null);
  const [metaLoaded, setMetaLoaded] = useState(false);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getVideoMeta(data.video_id).then((m) => {
      if (!cancelled) {
        setMeta(m);
        setMetaLoaded(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [data.video_id]);

  const daysAgo = data.days_ago ?? (meta?.indexed_at
    ? Math.floor((Date.now() - new Date(meta.indexed_at).getTime()) / 86_400_000)
    : null);

  const views = data.views || meta?.views || 0;
  const handle = data.handle || meta?.creator_handle || "";
  // Thumbnail resolution: DB URL → R2 frame fallback → null (shows TikTok icon)
  const thumbnail = meta?.thumbnail_url ?? r2FrameUrl(data.video_id);
  const videoUrl = meta?.video_url ?? null;
  const tiktokUrl = handle
    ? `https://www.tiktok.com/${handle.startsWith("@") ? handle : "@" + handle}/video/${data.video_id}`
    : null;

  // ── Thumbnail content (shared between <a> and fallback <div>) ────────────
  const thumbnailInner = playing && videoUrl ? (
    <video
      src={videoUrl}
      autoPlay
      controls
      playsInline
      className="absolute inset-0 h-full w-full object-cover"
      onClick={(e) => e.stopPropagation()}
    />
  ) : (
    <>
      {thumbnail ? (
        <img
          src={thumbnail}
          alt={handle}
          className="absolute inset-0 h-full w-full object-cover"
          loading="lazy"
        />
      ) : metaLoaded ? (
        /* Video not in corpus or thumbnail expired — show TikTok icon placeholder */
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-[var(--surface-alt)]">
          <svg className="h-7 w-7 opacity-60" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path fill="#69C9D0" d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"/>
            <path fill="#EE1D52" d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"/>
          </svg>
          <p className="text-center text-[9px] leading-tight text-[var(--faint)] px-1">Xem trên TikTok</p>
        </div>
      ) : (
        /* Still loading */
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-8 w-8 animate-pulse rounded-full bg-[var(--border)]" />
        </div>
      )}
      {/* Play overlay — only when R2 video is available */}
      {videoUrl ? (
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
      ) : null}
    </>
  );

  return (
    <div
      className="flex-shrink-0 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]"
      style={{ width: 140 }}
    >
      {/* Thumbnail area — 9:16 aspect. Whole area is a TikTok link when URL is known. */}
      {tiktokUrl ? (
        <a
          href={tiktokUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Xem video của ${handle} trên TikTok`}
          className="relative block w-full overflow-hidden bg-[var(--surface-alt)]"
          style={{ paddingBottom: "177.78%" /* 9:16 */ }}
        >
          {thumbnailInner}
        </a>
      ) : (
        <div
          className="relative w-full overflow-hidden bg-[var(--surface-alt)]"
          style={{ paddingBottom: "177.78%" /* 9:16 */ }}
        >
          {thumbnailInner}
        </div>
      )}

      {/* Card body */}
      <div className="flex flex-col gap-1 p-2.5">
        {/* View count — JetBrains Mono, purple */}
        {views > 0 ? (
          <p
            className="font-mono text-xs font-semibold leading-tight text-[var(--purple)]"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            {formatVN(views)} views
          </p>
        ) : null}

        {/* Recency */}
        {daysAgo != null ? (
          <p className="text-xs text-[var(--ink4,var(--muted))]">{formatRecencyVI(daysAgo)}</p>
        ) : null}

        {/* Breakout badge */}
        {data.breakout && data.breakout > 2 ? (
          <span
            className="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold text-[var(--purple)]"
            style={{ background: "var(--purple-light)" }}
          >
            {formatBreakoutVI(data.breakout)}
            {data.breakout > 5 ? " ⭐" : ""}
          </span>
        ) : null}

        {/* Handle + TikTok link */}
        {handle ? (
          <p className="truncate text-xs font-medium text-[var(--muted)]">{handle}</p>
        ) : null}
        {tiktokUrl ? (
          <a
            href={tiktokUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-0.5 text-[10px] text-[var(--purple)] hover:underline"
          >
            TikTok <ExternalLink className="h-2.5 w-2.5" />
          </a>
        ) : null}
      </div>
    </div>
  );
}
