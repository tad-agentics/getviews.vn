/**
 * VideoGridBlock — 2-column thumbnail grid for chat responses (LightReel style).
 *
 * Rendered when Gemini outputs a video_grid JSON block:
 * {"type":"video_grid","ids":["id1","id2"],"labels":["label1","label2"]}
 *
 * Each cell: 9:16 thumbnail with view-count gradient overlay, label text below.
 * Tapping thumbnail opens TikTok URL.
 */
import { useState, useEffect } from "react";
import { getVideoMeta, r2FrameUrl, type VideoMeta } from "@/lib/services/corpus-service";
import { formatVN } from "@/lib/formatters";

interface VideoGridCellProps {
  videoId: string;
  label: string;
}

function VideoGridCell({ videoId, label }: VideoGridCellProps) {
  const [meta, setMeta] = useState<VideoMeta | null>(null);
  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getVideoMeta(videoId).then((m) => {
      if (!cancelled) setMeta(m);
    });
    return () => {
      cancelled = true;
    };
  }, [videoId]);

  const thumbnail = meta?.thumbnail_url ?? r2FrameUrl(videoId);
  const tiktokUrl =
    meta?.tiktok_url ??
    (meta?.creator_handle
      ? `https://www.tiktok.com/${meta.creator_handle.startsWith("@") ? meta.creator_handle : "@" + meta.creator_handle}/video/${videoId}`
      : null);

  useEffect(() => {
    setImgFailed(false);
  }, [thumbnail]);

  const thumbnailEl = (
    <div
      className="relative w-full overflow-hidden rounded-xl bg-[var(--surface-alt)]"
      style={{ paddingBottom: "177.78%" /* 9:16 */ }}
    >
      {thumbnail && !imgFailed ? (
        <img
          src={thumbnail}
          alt={label}
          className="absolute inset-0 h-full w-full object-cover"
          loading="lazy"
          onError={() => setImgFailed(true)}
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-8 w-8 animate-pulse rounded-full bg-[var(--border)]" />
        </div>
      )}
      {meta?.views ? (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent px-2 py-1.5">
          <p
            className="font-mono text-[11px] font-semibold leading-none text-white"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            {formatVN(meta.views)}
          </p>
        </div>
      ) : null}
    </div>
  );

  return (
    <div className="flex flex-col gap-1.5">
      {tiktokUrl ? (
        <a
          href={tiktokUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="block transition-opacity hover:opacity-90"
          aria-label={label || "Xem video trên TikTok"}
        >
          {thumbnailEl}
        </a>
      ) : (
        thumbnailEl
      )}
      {label ? (
        <p className="text-xs leading-snug text-[var(--ink)]">{label}</p>
      ) : null}
    </div>
  );
}

export interface VideoGridData {
  type: "video_grid";
  ids: string[];
  labels: string[];
}

interface Props {
  ids: string[];
  labels: string[];
}

export function VideoGridBlock({ ids, labels }: Props) {
  if (!ids.length) return null;
  const colsClass =
    ids.length === 1 ? "grid-cols-1"
    : ids.length === 3 ? "grid-cols-3"
    : "grid-cols-2";
  return (
    <div className={`my-2 grid ${colsClass} gap-3`}>
      {ids.map((id, i) => (
        <VideoGridCell key={id} videoId={id} label={labels[i] ?? ""} />
      ))}
    </div>
  );
}
