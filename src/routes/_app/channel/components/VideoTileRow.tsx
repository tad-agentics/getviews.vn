/**
 * VideoTileRow — a horizontal row of 3-4 TikTok video tiles in 9:16 ratio.
 * Used in the what_worked / what_falling sections of the channel diagnosis.
 */

import { VideoThumbnail } from "@/components/VideoThumbnail";
import type { ChannelPerformerTile } from "@/lib/api-types";

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

interface VideoTileProps {
  tile: ChannelPerformerTile;
}

function VideoTile({ tile }: VideoTileProps) {
  const href = tile.video_url || undefined;

  const inner = (
    <div className="relative flex-shrink-0 w-24 min-[393px]:w-28 rounded-lg overflow-hidden bg-[color:var(--gv-canvas-2)]">
      {/* 9:16 aspect via padding-bottom */}
      <div className="relative pb-[177.78%]">
        <VideoThumbnail
          thumbnailUrl={tile.thumbnail_url}
          className="absolute inset-0 w-full h-full"
          alt={tile.caption_snippet || "Video"}
        />
        {/* View-count overlay */}
        <div className="absolute bottom-0 left-0 right-0 px-1.5 py-1 bg-gradient-to-t from-black/70 to-transparent">
          <span className="font-mono text-[10px] font-semibold text-white leading-none">
            {formatViews(tile.views)}
          </span>
        </div>
      </div>
      {/* Caption snippet */}
      {tile.caption_snippet && (
        <div className="px-1.5 py-1">
          <p className="text-[10px] text-[color:var(--muted)] line-clamp-2 leading-tight">
            {tile.caption_snippet}
          </p>
        </div>
      )}
    </div>
  );

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="block"
        aria-label={`Xem video: ${tile.caption_snippet || tile.content_format}`}
      >
        {inner}
      </a>
    );
  }

  return inner;
}

interface VideoTileRowProps {
  tiles: ChannelPerformerTile[];
  /** Optional section label shown above the row */
  label?: string;
}

export function VideoTileRow({ tiles, label }: VideoTileRowProps) {
  if (!tiles || tiles.length === 0) return null;

  const visible = tiles.slice(0, 4);

  return (
    <div className="mt-3 mb-1">
      {label && (
        <p className="text-[11px] font-medium text-[color:var(--muted)] uppercase tracking-wide mb-2">
          {label}
        </p>
      )}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {visible.map((tile, i) => (
          <VideoTile key={tile.video_url || i} tile={tile} />
        ))}
      </div>
    </div>
  );
}
