/**
 * VideoRefCard — thumbnail reference card for corpus video citations.
 *
 * Rendered when Gemini synthesis outputs a video_ref JSON block:
 * {"type":"video_ref","video_id":"xxx","handle":"@creator","views":1100000,"days_ago":6}
 *
 * Thumbnail + overlay metadata is delegated to VideoThumb.
 * The card body below keeps only breakout badge and handle/link row for accessibility.
 */
import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { getVideoMeta, r2FrameUrl, type VideoMeta } from "@/lib/services/corpus-service";
import { formatBreakoutVI } from "@/lib/formatters";
import { VideoThumb } from "./VideoThumb";

export interface VideoRefData {
  type: "video_ref";
  video_id: string;
  handle: string;
  views: number;
  days_ago: number;
  breakout?: number; // ratio e.g. 3.2 → "3,2x"
  thumbnail_url?: string; // pre-fetched CDN or R2 URL from backend
}

interface Props {
  data: VideoRefData;
  className?: string;
}

export function VideoRefCard({ data, className = "" }: Props) {
  const [meta, setMeta] = useState<VideoMeta | null>(null);
  const [metaLoaded, setMetaLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getVideoMeta(data.video_id).then((m) => {
      if (!cancelled) {
        setMeta(m);
        setMetaLoaded(true);
      }
    });
    return () => { cancelled = true; };
  }, [data.video_id]);

  // Always use video_ref JSON as primary source — DB enrichment is thumbnail-only.
  const views = data.views || meta?.views || 0;
  const handle = data.handle || meta?.creator_handle || "";
  const daysAgo =
    data.days_ago != null
      ? data.days_ago
      : meta?.indexed_at
        ? Math.floor((Date.now() - new Date(meta.indexed_at).getTime()) / 86_400_000)
        : null;

  // Thumbnail resolution: block URL → DB URL → R2 frame fallback → null (shows TikTok icon)
  const thumbnail = data.thumbnail_url || meta?.thumbnail_url || r2FrameUrl(data.video_id);
  const videoUrl = meta?.video_url ?? null;
  const tiktokUrl = handle
    ? `https://www.tiktok.com/${handle.startsWith("@") ? handle : "@" + handle}/video/${data.video_id}`
    : null;

  // Show a skeleton until meta resolves, so the card doesn't flash with no thumbnail
  const thumbSrc = metaLoaded || data.thumbnail_url ? thumbnail : null;

  return (
    <div className={`overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] ${className}`}>
      <VideoThumb
        thumbnail={thumbSrc}
        handle={handle}
        views={views > 0 ? views : undefined}
        daysAgo={daysAgo}
        tiktokUrl={tiktokUrl}
        videoUrl={videoUrl}
      />

      {/* Card body — breakout badge + handle link (metadata is visible in overlay) */}
      <div className="px-2 py-1.5 space-y-1">
        {/* Breakout badge — not visible on thumbnail */}
        {data.breakout && data.breakout > 2 ? (
          <span className="inline-block rounded bg-[color:var(--gv-accent)]/80 px-1 py-0.5 text-[9px] font-semibold text-white">
            {formatBreakoutVI(data.breakout)}{data.breakout > 5 ? " ★" : ""}
          </span>
        ) : null}

        {/* Handle + TikTok link row — accessibility / copy */}
        {handle && tiktokUrl ? (
          <a
            href={tiktokUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 truncate text-[10px] text-[var(--muted)] hover:text-[var(--ink)]"
          >
            <span className="truncate">{handle}</span>
            <ExternalLink className="h-2.5 w-2.5 flex-shrink-0" />
          </a>
        ) : handle ? (
          <p className="truncate text-[10px] text-[var(--muted)]">{handle}</p>
        ) : null}
      </div>
    </div>
  );
}
