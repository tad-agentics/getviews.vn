/**
 * CreatorTileRow — a horizontal row of 2-3 UGC creator tiles.
 * Used in the competitive_landscape section of the channel diagnosis.
 */

import { VideoThumbnail } from "@/components/VideoThumbnail";
import type { ChannelUGCCreator } from "@/lib/api-types";
import { formatFollowers, formatViews } from "@/lib/formatters";

interface CreatorTileProps {
  creator: ChannelUGCCreator;
}

function CreatorTile({ creator }: CreatorTileProps) {
  const profileUrl = `https://tiktok.com/@${creator.handle}`;
  const sampleUrl = creator.sample_video_url || undefined;

  return (
    <a
      href={profileUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="flex-shrink-0 w-32 min-[393px]:w-36 block"
      aria-label={`Xem kênh @${creator.handle}`}
    >
      <div className="rounded-xl overflow-hidden bg-[color:var(--gv-canvas-2)] border border-[color:var(--border)]">
        {/* Thumbnail from sample video */}
        <div className="relative pb-[100%]">
          <VideoThumbnail
            thumbnailUrl={creator.thumbnail_url || null}
            videoId={(creator.sample_video_url || "").match(/(\d{15,})/)?.[1]}
            className="absolute inset-0 w-full h-full"
            alt={`@${creator.handle}`}
          />
          {sampleUrl && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-6 h-6 rounded-full bg-black/50 flex items-center justify-center">
                <span className="text-white text-[11px] leading-none">▶</span>
              </div>
            </div>
          )}
        </div>
        {/* Creator info */}
        <div className="px-2 py-1.5">
          <p className="text-[11px] font-semibold text-[color:var(--foreground)] truncate">
            @{creator.handle}
          </p>
          <p className="text-[11px] text-[color:var(--muted)] mt-0.5">
            {creator.followers != null ? `${formatFollowers(creator.followers)} followers` : "N/A"}
          </p>
          {creator.avg_views > 0 && (
            <p className="text-[11px] text-[color:var(--muted)]">
              avg {formatViews(creator.avg_views)} views
            </p>
          )}
        </div>
      </div>
    </a>
  );
}

interface CreatorTileRowProps {
  creators: ChannelUGCCreator[];
  label?: string;
}

export function CreatorTileRow({ creators, label }: CreatorTileRowProps) {
  if (!creators || creators.length === 0) return null;

  const visible = creators.slice(0, 3);

  return (
    <div className="mt-3 mb-1">
      {label && (
        <p className="text-[11px] font-medium text-[color:var(--muted)] gv-kicker tracking-wide mb-2">
          {label}
        </p>
      )}
      <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-hide">
        {visible.map((creator) => (
          <CreatorTile key={creator.handle} creator={creator} />
        ))}
      </div>
    </div>
  );
}
