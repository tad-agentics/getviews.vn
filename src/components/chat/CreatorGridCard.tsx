import { useState, useEffect } from "react";
import { ExternalLink } from "lucide-react";
import { r2FrameUrl } from "@/lib/services/corpus-service";

export interface CreatorCardData {
  type: "creator_card";
  handle: string;
  avatar_video_id: string;
  /** Formatted string: "29K", "1.2M", or "?" */
  followers: string;
  /** Formatted string: "16.3%" */
  er: string;
  hook_style?: string;
}

export function CreatorGridCard({ data }: { data: CreatorCardData }) {
  const [imgFailed, setImgFailed] = useState(false);
  const thumbnail = r2FrameUrl(data.avatar_video_id);

  useEffect(() => {
    setImgFailed(false);
  }, [thumbnail]);

  const tiktokUrl = `https://www.tiktok.com/${data.handle.startsWith("@") ? data.handle : "@" + data.handle}`;
  const initial = data.handle.replace("@", "").slice(0, 1).toUpperCase();

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-alt)]">
      {/* Avatar — 16:9 crop of creator's best video thumbnail */}
      <div className="relative aspect-video w-full overflow-hidden bg-[var(--border)]">
        {thumbnail && !imgFailed ? (
          <img
            src={thumbnail}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-[var(--purple-light)]">
            <span className="text-xl font-bold text-[var(--purple)]">{initial}</span>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="p-3">
        <a
          href={tiktokUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-sm font-semibold text-[var(--ink)] hover:underline"
        >
          {data.handle}
          <ExternalLink className="h-3 w-3 flex-shrink-0 text-[var(--faint)]" />
        </a>
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-[var(--muted)]">
          {data.followers !== "?" ? <span>{data.followers} followers</span> : null}
          <span className="font-semibold text-[var(--purple)]">ER {data.er}</span>
        </div>
        {data.hook_style ? (
          <p className="mt-1.5 text-[11px] leading-snug text-[var(--faint)]">{data.hook_style}</p>
        ) : null}
      </div>
    </div>
  );
}
