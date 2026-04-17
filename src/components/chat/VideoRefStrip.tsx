/**
 * VideoRefStrip — video reference citations in chat.
 *
 * 1 ref  → compact horizontal inline card (doesn't interrupt text flow)
 * 2+ refs → horizontal scroll strip (existing behaviour)
 */
import { useState, useEffect } from "react";
import { ExternalLink } from "lucide-react";
import { getVideoMeta, r2FrameUrl, type VideoMeta } from "@/lib/services/corpus-service";
import { formatVN } from "@/lib/formatters";
import { VideoRefCard, type VideoRefData } from "./VideoRefCard";

interface Props {
  refs: VideoRefData[];
}

// Compact inline citation — used when only 1 video_ref in a section
function VideoRefInline({ data }: { data: VideoRefData }) {
  const [meta, setMeta] = useState<VideoMeta | null>(null);
  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getVideoMeta(data.video_id).then((m) => {
      if (!cancelled) setMeta(m);
    });
    return () => {
      cancelled = true;
    };
  }, [data.video_id]);

  const thumbnail = data.thumbnail_url || meta?.thumbnail_url || r2FrameUrl(data.video_id);

  useEffect(() => {
    setImgFailed(false);
  }, [thumbnail]);

  const handle = data.handle || meta?.creator_handle || "";
  const views = data.views || meta?.views || 0;
  const tiktokUrl = handle
    ? `https://www.tiktok.com/${handle.startsWith("@") ? handle : "@" + handle}/video/${data.video_id}`
    : null;

  return (
    <div className="my-2 flex items-center gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-2">
      {/* Small thumbnail */}
      <div
        className="relative flex-shrink-0 overflow-hidden rounded-lg bg-[var(--surface-alt)]"
        style={{ width: 36, height: 50 }}
      >
        {thumbnail && !imgFailed ? (
          <img
            src={thumbnail}
            alt={handle}
            className="absolute inset-0 h-full w-full object-cover"
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <svg className="h-4 w-4 opacity-40" viewBox="0 0 24 24">
              <path fill="#69C9D0" d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"/>
            </svg>
          </div>
        )}
      </div>

      {/* Metadata */}
      <div className="min-w-0 flex-1">
        {views > 0 && (
          <p className="mb-0.5 font-mono text-xs font-semibold leading-none tabular-nums text-[var(--purple)]">
            {formatVN(views)} views
          </p>
        )}
        {handle && (
          <p className="truncate text-xs text-[var(--muted)]">{handle}</p>
        )}
      </div>

      {/* TikTok link */}
      {tiktokUrl && (
        <a
          href={tiktokUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-shrink-0 items-center gap-1 text-[10px] text-[var(--purple)] hover:underline"
        >
          TikTok <ExternalLink className="h-2.5 w-2.5" />
        </a>
      )}
    </div>
  );
}

export function VideoRefStrip({ refs }: Props) {
  if (!refs.length) return null;

  // Single ref: compact horizontal inline card (doesn't interrupt text flow)
  if (refs.length === 1) {
    return <VideoRefInline data={refs[0]} />;
  }

  // Multiple refs: horizontal scroll strip (existing behaviour)
  return (
    <div className="my-3 -mx-4 lg:-mx-5">
      <div
        className="flex gap-2.5 overflow-x-auto px-4 pb-2 lg:px-5"
        style={{ scrollSnapType: "x mandatory", WebkitOverflowScrolling: "touch" }}
      >
        {refs.map((ref) => (
          <div key={ref.video_id} style={{ scrollSnapAlign: "start" }}>
            <VideoRefCard data={ref} />
          </div>
        ))}
        <div className="flex-shrink-0" style={{ width: 16 }} aria-hidden />
      </div>
    </div>
  );
}
