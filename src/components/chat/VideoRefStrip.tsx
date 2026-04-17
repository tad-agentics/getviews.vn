/**
 * VideoRefStrip — video reference citations in chat.
 *
 * 1 ref  → compact horizontal inline card (doesn't interrupt text flow)
 * 2+ refs → 2-col grid (3 refs → 3-col), fills container width
 */
import { useState, useEffect } from "react";
import { ExternalLink } from "lucide-react";
import { getVideoMeta, r2FrameUrl } from "@/lib/services/corpus-service";
import { formatVN } from "@/lib/formatters";
import { VideoRefCard, type VideoRefData } from "./VideoRefCard";

interface Props {
  refs: VideoRefData[];
}

// Compact inline citation — used when only 1 video_ref in a section
function VideoRefInline({ data }: { data: VideoRefData }) {
  const [thumbnail, setThumbnail] = useState<string | null>(data.thumbnail_url ?? null);
  const [imgFailed, setImgFailed] = useState(false);
  const [tiktokUrl, setTiktokUrl] = useState<string>(
    `https://www.tiktok.com/${data.handle.startsWith("@") ? data.handle : "@" + data.handle}/video/${data.video_id}`
  );

  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-floating-promises
    getVideoMeta(data.video_id).then((m) => {
      if (!thumbnail) setThumbnail(m?.thumbnail_url ?? r2FrameUrl(data.video_id));
      if (m?.tiktok_url) setTiktokUrl(m.tiktok_url);
    });
  }, [data.video_id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setImgFailed(false);
  }, [thumbnail]);

  return (
    <a
      href={tiktokUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="my-2 flex items-center gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-2 transition-colors duration-[120ms] hover:bg-[var(--surface)]"
    >
      {/* 9:16 thumbnail — 27×48px */}
      <div className="relative h-12 w-[27px] flex-shrink-0 overflow-hidden rounded-md bg-[var(--border)]">
        {thumbnail && !imgFailed ? (
          <img
            src={thumbnail}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <svg className="h-3 w-3 opacity-50" viewBox="0 0 24 24">
              <path fill="#69C9D0" d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"/>
              <path fill="#EE1D52" d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"/>
            </svg>
          </div>
        )}
      </div>

      {/* Metadata */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-semibold text-[var(--ink)]">{data.handle}</p>
        <p className="text-[11px] text-[var(--muted)]">{formatVN(data.views)} views</p>
      </div>

      <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-[var(--faint)]" />
    </a>
  );
}

export function VideoRefStrip({ refs }: Props) {
  if (!refs.length) return null;

  // Single ref: compact inline pill — doesn't interrupt text flow
  if (refs.length === 1) {
    return <VideoRefInline data={refs[0]} />;
  }

  // 2–3 refs: CSS grid filling container width
  if (refs.length <= 3) {
    const cols = refs.length === 3 ? "grid-cols-3" : "grid-cols-2";
    return (
      <div className={`my-3 grid ${cols} gap-2`}>
        {refs.map((ref) => (
          <VideoRefCard key={ref.video_id} data={ref} />
        ))}
      </div>
    );
  }

  // 4+ refs: horizontal scroll strip with fixed-width cards
  return (
    <div className="my-3 -mx-4 lg:-mx-5">
      <div
        className="flex gap-2.5 overflow-x-auto px-4 pb-2 lg:px-5"
        style={{ scrollSnapType: "x mandatory", WebkitOverflowScrolling: "touch" }}
      >
        {refs.map((ref) => (
          <div key={ref.video_id} style={{ scrollSnapAlign: "start", width: 140, flexShrink: 0 }}>
            <VideoRefCard data={ref} />
          </div>
        ))}
        <div className="flex-shrink-0" style={{ width: 16 }} aria-hidden />
      </div>
    </div>
  );
}
