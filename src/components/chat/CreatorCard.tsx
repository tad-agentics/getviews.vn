import { useState, useEffect } from "react";
import { getVideoMeta, r2FrameUrl } from "@/lib/services/corpus-service";

export interface CreatorCardData {
  type: "creator_card";
  handle: string;
  avatar_video_id: string;
  followers: number;
  er: number;
  reason: string;
}

export function CreatorCard({ data }: { data: CreatorCardData }) {
  const [thumbUrl, setThumbUrl] = useState<string | null>(null);
  const [imgFailed, setImgFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getVideoMeta(data.avatar_video_id).then((meta) => {
      if (!cancelled) {
        setThumbUrl(meta?.thumbnail_url ?? r2FrameUrl(data.avatar_video_id));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [data.avatar_video_id]);

  useEffect(() => {
    setImgFailed(false);
  }, [thumbUrl]);

  const tiktokUrl = `https://www.tiktok.com/${data.handle.startsWith("@") ? data.handle : "@" + data.handle}`;

  return (
    <div className="flex gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
      {/* Avatar — circular crop of video thumbnail */}
      <a href={tiktokUrl} target="_blank" rel="noopener noreferrer" className="flex-shrink-0">
        <div className="h-12 w-12 overflow-hidden rounded-full bg-[var(--surface-alt)] border-2 border-[var(--border)]">
          {thumbUrl && !imgFailed ? (
            <img
              src={thumbUrl}
              alt={data.handle}
              className="h-full w-full object-cover"
              onError={() => setImgFailed(true)}
            />
          ) : (
            <div className="h-full w-full flex items-center justify-center text-xs font-bold text-[var(--muted)]">
              {data.handle[1]?.toUpperCase()}
            </div>
          )}
        </div>
      </a>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <a
            href={tiktokUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-[var(--ink)] hover:underline"
          >
            {data.handle}
          </a>
          <span className="font-mono text-xs text-[var(--purple)] font-semibold tabular-nums">
            ER {data.er.toFixed(1)}%
          </span>
        </div>
        <p className="text-xs text-[var(--muted)] mb-1.5">
          {(data.followers / 1000).toFixed(0)}K followers
        </p>
        <p className="text-xs leading-snug text-[var(--ink-soft)]">{data.reason}</p>
      </div>
    </div>
  );
}
