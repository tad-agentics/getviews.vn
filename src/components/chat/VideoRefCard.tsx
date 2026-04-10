/**
 * VideoRefCard — thumbnail reference card for corpus video citations.
 *
 * Rendered when Gemini synthesis outputs a video_ref JSON block:
 * {"type":"video_ref","video_id":"xxx","handle":"@creator","views":1100000,"days_ago":6}
 *
 * Tap → inline video playback from R2 video_url
 * "Xem trên TikTok" → TikTok universal link (auto-opens app on Android)
 */
import { useState, useEffect } from "react";
import { ExternalLink, Play } from "lucide-react";
import { getVideoMeta, type VideoMeta } from "@/lib/services/corpus-service";
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
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getVideoMeta(data.video_id).then((m) => {
      if (!cancelled) setMeta(m);
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
  const thumbnail = meta?.thumbnail_url ?? null;
  const videoUrl = meta?.video_url ?? null;
  const tiktokUrl = handle
    ? `https://www.tiktok.com/${handle.startsWith("@") ? handle : "@" + handle}/video/${data.video_id}`
    : null;

  return (
    <div
      className="flex-shrink-0 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]"
      style={{ width: 140 }}
    >
      {/* Thumbnail area — 9:16 aspect */}
      <div
        className="relative w-full overflow-hidden bg-[var(--surface-alt)]"
        style={{ paddingBottom: "177.78%" /* 9:16 */ }}
      >
        {playing && videoUrl ? (
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
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="h-8 w-8 animate-pulse rounded-full bg-[var(--border)]" />
              </div>
            )}
            {/* Play overlay */}
            {videoUrl ? (
              <button
                type="button"
                onClick={() => setPlaying(true)}
                className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity duration-150 hover:opacity-100"
                aria-label="Xem video"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/80">
                  <Play className="h-5 w-5 text-[var(--ink)]" fill="currentColor" />
                </div>
              </button>
            ) : null}
          </>
        )}
      </div>

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
