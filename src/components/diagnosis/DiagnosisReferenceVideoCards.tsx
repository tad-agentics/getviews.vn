/**
 * Peer reference videos under v6 diagnosis sections — narrative copy above each
 * 9:16 hover tile; handle + views overlay on the clip (Xu hướng parity).
 *
 * Inline playback (2026-06-11): tiles whose corpus row has an R2-hosted MP4
 * (`playback_url`) open the existing VideoPlayerModal in-app — the creator
 * studies the reference without bouncing to TikTok. Tiles without a clip
 * keep the external TikTok link. The modal is lazy-loaded so the answer
 * chunk doesn't pay for the player until a tile is actually opened.
 */

import { lazy, Suspense, useCallback, useMemo, useRef, useState } from "react";
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
  const clipSrc = tile.playback_url?.trim() ?? "";
  const canHoverClip = Boolean(clipSrc);

  const [hoverClip, setHoverClip] = useState(false);
  const clipRef = useRef<HTMLVideoElement>(null);

  const startHoverClip = useCallback(() => {
    if (!canHoverClip) return;
    const el = clipRef.current;
    if (!el) return;
    if (!el.getAttribute("src")) {
      el.src = clipSrc;
      el.load();
    }
    void el.play().catch(() => {});
    setHoverClip(true);
  }, [canHoverClip, clipSrc]);

  const stopHoverClip = useCallback(() => {
    setHoverClip(false);
    const el = clipRef.current;
    if (!el) return;
    el.pause();
    el.currentTime = 0;
  }, []);

  const tileLabel = `Video tham chiếu${handle ? ` ${handle}` : ""}${viewsLabel ? ` · ${viewsLabel}` : ""}${narrative ? `: ${narrative}` : ""}`;

  const videoTile = (
    <div
      className="relative w-full overflow-hidden rounded-lg bg-[color:var(--gv-canvas)]"
      style={{ aspectRatio: "9/16" }}
      onMouseEnter={startHoverClip}
      onMouseLeave={stopHoverClip}
    >
      {canHoverClip ? (
        <video
          ref={clipRef}
          muted
          loop
          playsInline
          preload="none"
          className={`pointer-events-none absolute inset-0 z-[5] h-full w-full object-cover transition-opacity duration-200 ease-out ${
            hoverClip ? "opacity-100" : "opacity-0"
          }`}
          aria-hidden
        />
      ) : null}
      <VideoThumbnail
        thumbnailUrl={tile.thumbnail_url}
        videoId={tile.aweme_id}
        alt=""
        loading="lazy"
        className={`absolute inset-0 z-10 h-full w-full transition-opacity duration-200 ease-out ${
          hoverClip && canHoverClip ? "opacity-0" : "opacity-100"
        }`}
        placeholderClassName="bg-[color:var(--gv-canvas-2)]"
      />
      <div
        className="pointer-events-none absolute inset-0 z-[15] bg-gradient-to-b from-transparent from-40% to-black/70"
        aria-hidden
      />
      <div className="pointer-events-none absolute bottom-2 left-2.5 right-2.5 z-20 text-white">
        <div className="flex items-center justify-between gap-2">
          {handle ? (
            <span className="min-w-0 truncate gv-kicker text-[11px] text-white">
              {handle}
            </span>
          ) : (
            <span aria-hidden />
          )}
          {viewsLabel ? (
            <span className="shrink-0 gv-mono text-[11px] font-semibold tabular-nums text-white">
              {viewsLabel}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );

  const cardShellClass =
    "flex h-full flex-col gap-2.5 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3 transition-colors duration-[120ms] group-hover:border-[color:var(--gv-ink)]";

  const inner = (
    <div className={cardShellClass}>
      {narrative ? (
        <p className="m-0 text-[13px] leading-[1.45] text-[color:var(--gv-ink)]">
          {narrative}
        </p>
      ) : null}
      {videoTile}
    </div>
  );

  if (playable) {
    return (
      <button
        type="button"
        onClick={onPlay}
        className="group block h-full w-full min-w-0 rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]"
        aria-label={tileLabel}
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
        className="group block h-full w-full min-w-0 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]"
        aria-label={tileLabel}
      >
        {inner}
      </a>
    );
  }

  return <div className="h-full w-full min-w-0">{inner}</div>;
}

export function DiagnosisReferenceVideoCards({
  tiles,
  label = "Video tham chiếu",
  showLabel = true,
  embedded = false,
}: {
  tiles: DiagnosisReferenceTile[];
  label?: string;
  /** When false, omit the kicker above the grid (parent supplies section chrome). */
  showLabel?: boolean;
  /** Inline in a parent section — no kicker/border chrome; spacing via ``mt-4`` when label hidden. */
  embedded?: boolean;
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
    <div
      className={embedded && showLabel ? undefined : "mt-4"}
      aria-label={showLabel ? undefined : label || "Video tham chiếu"}
    >
      {showLabel && label ? (
        <p className="gv-mono mb-3 text-[11px] gv-kicker tracking-[0.18em] text-[color:var(--gv-ink-3)]">
          {label}
        </p>
      ) : null}
      <div className="grid grid-cols-2 gap-3 min-[640px]:grid-cols-3 min-[1100px]:grid-cols-4">
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
