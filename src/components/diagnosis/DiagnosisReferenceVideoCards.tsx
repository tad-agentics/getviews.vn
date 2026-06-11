/**
 * Peer reference videos under v6 diagnosis sections — one card per video with
 * narrative context above the thumbnail (GetReels-style evidence layout).
 *
 * Inline playback (2026-06-11): tiles whose corpus row has an R2-hosted MP4
 * (`playback_url`) open the existing VideoPlayerModal in-app — the creator
 * studies the reference without bouncing to TikTok. Tiles without a clip
 * keep the external TikTok link. The modal is lazy-loaded so the answer
 * chunk doesn't pay for the player until a tile is actually opened.
 */

import { lazy, Suspense, useMemo, useState } from "react";
import { Play } from "lucide-react";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import {
  formatCreatorHandle,
  referenceTileNarrative,
  type DiagnosisReferenceTile,
} from "@/lib/diagnosisReferenceTiles";
import { formatViews } from "@/lib/formatters";

const VideoPlayerModal = lazy(() =>
  import("@/components/explore/VideoPlayerModal").then((m) => ({
    default: m.VideoPlayerModal,
  })),
);

/** Adapt a diagnosis tile to the ExploreGridVideo shape the player expects. */
function tileToPlayerVideo(tile: DiagnosisReferenceTile) {
  const vid = tile.aweme_id || tile.video_url || "";
  return {
    id: vid,
    video_id: vid,
    views: tile.views > 0 ? formatViews(tile.views) : "",
    time: "",
    img: tile.thumbnail_url || "",
    text: tile.caption_snippet || "",
    handle: formatCreatorHandle(tile.author_handle) || "",
    caption: tile.caption_snippet || "",
    likes: "",
    comments: "",
    shares: "",
    videoUrl: tile.playback_url || "",
    tiktok_url: tile.video_url || null,
  };
}

function ReferenceVideoCard({
  tile,
  onPlay,
}: {
  tile: DiagnosisReferenceTile;
  onPlay?: () => void;
}) {
  const href = tile.video_url || undefined;
  const playable = Boolean(tile.playback_url) && onPlay != null;
  const handle = formatCreatorHandle(tile.author_handle);
  const narrative = referenceTileNarrative(tile);
  const viewsLabel =
    tile.views > 0 ? `${formatViews(tile.views)} view` : null;

  const inner = (
    <article className="flex h-full flex-col rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3 shadow-[0_1px_0_rgba(0,0,0,0.04)]">
      <p className="gv-kicker m-0 text-[10px] font-semibold tracking-wide text-[color:var(--gv-accent)]">
        Sao chép cách này
      </p>
      <p className="m-0 mt-1.5 flex-1 text-[13px] leading-[1.45] text-[color:var(--gv-ink)]">
        {narrative}
      </p>
      <div className="relative mx-auto mt-3 w-full max-w-[140px] overflow-hidden rounded-lg bg-[color:var(--gv-canvas-2)]">
        <div className="relative pb-[177.78%]">
          <VideoThumbnail
            thumbnailUrl={tile.thumbnail_url}
            videoId={tile.aweme_id}
            className="absolute inset-0 h-full w-full"
            alt={tile.caption_snippet || "Video tham chiếu"}
          />
          {playable ? (
            <span
              aria-hidden="true"
              className="absolute inset-0 flex items-center justify-center"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-black/45">
                <Play className="ml-0.5 h-5 w-5 text-white" fill="currentColor" />
              </span>
            </span>
          ) : null}
        </div>
      </div>
      <footer className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-[color:var(--gv-rule)] pt-2.5">
        {viewsLabel ? (
          <span className="gv-mono text-[12px] font-semibold text-[color:var(--gv-ink)]">
            {viewsLabel}
          </span>
        ) : null}
        {handle ? (
          <span className="text-[12px] font-medium text-[color:var(--gv-ink-3)]">
            {handle}
          </span>
        ) : null}
      </footer>
    </article>
  );

  if (playable) {
    return (
      <button
        type="button"
        onClick={onPlay}
        className="block h-full w-full min-w-0 rounded-[12px] text-left transition-colors hover:border-[color:var(--gv-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]"
        aria-label={`Phát video tham chiếu${handle ? ` của ${handle}` : ""}`}
      >
        {inner}
      </button>
    );
  }

  if (href) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="block h-full min-w-0 rounded-[12px] transition-colors hover:border-[color:var(--gv-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]"
        aria-label={`Xem video tham chiếu${handle ? ` của ${handle}` : ""}`}
      >
        {inner}
      </a>
    );
  }

  return <div className="h-full min-w-0">{inner}</div>;
}

export function DiagnosisReferenceVideoCards({
  tiles,
  label = "Video tham chiếu",
}: {
  tiles: DiagnosisReferenceTile[];
  label?: string;
}) {
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  // Player list = the playable tiles of this card set, so prev/next moves
  // between this section's references (parity with Explore's modal).
  const playerVideos = useMemo(
    () => tiles.filter((t) => t.playback_url).map(tileToPlayerVideo),
    [tiles],
  );

  if (!tiles.length) return null;

  const playing =
    playingIndex != null && tiles[playingIndex]?.playback_url
      ? tileToPlayerVideo(tiles[playingIndex])
      : null;

  return (
    <div className="mt-4 border-t border-[color:var(--gv-rule)] pt-4" aria-label={label}>
      <p className="mb-3 text-[11px] font-medium gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
        {label}
      </p>
      <div className="grid grid-cols-1 gap-3 min-[640px]:grid-cols-2 min-[1100px]:grid-cols-3">
        {tiles.map((tile, i) => (
          <ReferenceVideoCard
            key={tile.aweme_id || tile.video_url || i}
            tile={tile}
            onPlay={tile.playback_url ? () => setPlayingIndex(i) : undefined}
          />
        ))}
      </div>
      {playing ? (
        <Suspense fallback={null}>
          <VideoPlayerModal
            video={playing}
            allVideos={playerVideos}
            onClose={() => setPlayingIndex(null)}
          />
        </Suspense>
      ) : null}
    </div>
  );
}
