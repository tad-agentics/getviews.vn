/**
 * CreatorTileRow — a horizontal row of 2-3 UGC creator tiles.
 * Used in the competitive_landscape section of the channel diagnosis.
 */

import { VideoThumbnail } from "@/components/VideoThumbnail";
import type { ChannelUGCCreator } from "@/lib/api-types";

function formatFollowers(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

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
      <div className="rounded-xl overflow-hidden bg-[color:var(--gv-canvas-2)] border border-[color:var(--gv-border)]">
        {/* Thumbnail from sample video */}
        <div className="relative pb-[100%]">
          <VideoThumbnail
            thumbnailUrl={creator.thumbnail_url || null}
            className="absolute inset-0 w-full h-full"
            alt={`@${creator.handle}`}
          />
          {sampleUrl && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-6 h-6 rounded-full bg-black/50 flex items-center justify-center">
                <span className="text-white text-[10px] leading-none">▶</span>
              </div>
            </div>
          )}
        </div>
        {/* Creator info */}
        <div className="px-2 py-1.5">
          <p className="text-[11px] font-semibold text-[color:var(--gv-foreground)] truncate">
            @{creator.handle}
          </p>
          <p className="text-[10px] text-[color:var(--gv-muted)] mt-0.5">
            {formatFollowers(creator.followers)} followers
          </p>
          {creator.avg_views > 0 && (
            <p className="text-[10px] text-[color:var(--gv-muted)]">
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
        <p className="text-[11px] font-medium text-[color:var(--gv-muted)] uppercase tracking-wide mb-2">
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
