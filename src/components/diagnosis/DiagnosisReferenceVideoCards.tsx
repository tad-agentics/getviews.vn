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

/**
 * Colored fallback panels for thumb-404 — same pattern as BreakoutGrid
 * (fix 81aa59c): when every thumbnail candidate fails, the tile keeps a
 * deliberate avatar-palette surface instead of an empty gradient box.
 */
const FALLBACK_PANEL = [
  "bg-[color:var(--gv-avatar-2)]",
  "bg-[color:var(--gv-avatar-6)]",
  "bg-[color:var(--gv-avatar-4)]",
] as const;

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
  idx,
  onPlay,
  hideNarrative = false,
  thumbOnly = false,
}: {
  tile: DiagnosisReferenceTile;
  idx: number;
  onPlay?: () => void;
  /** Omit narrative paragraph — parent renders prose in the finding body. */
  hideNarrative?: boolean;
  /** Thumbnail-only tile inside a finding card (parity with evidence clip). */
  thumbOnly?: boolean;
}) {
  const href = tile.video_url || undefined;
  const isDouyin = tile.source === "douyin";
  const playable = Boolean(tile.playback_url) && onPlay != null;
  const handle = formatCreatorHandle(tile.author_handle);
  const narrative = referenceTileNarrative(tile);
  const viewsLabel =
    tile.views > 0 ? `${formatViews(tile.views)} view` : null;
  const clipSrc = tile.playback_url?.trim() ?? "";
  const canHoverClip = Boolean(clipSrc);

  const [hoverClip, setHoverClip] = useState(false);
  const [thumbFailed, setThumbFailed] = useState(false);
  const clipRef = useRef<HTMLVideoElement>(null);

  const panelClass =
    FALLBACK_PANEL[idx % FALLBACK_PANEL.length] ?? "bg-[color:var(--gv-canvas-2)]";
  const tileSurfaceClass =
    thumbFailed || !tile.thumbnail_url ? panelClass : "bg-[color:var(--gv-canvas)]";

  const startHoverClip = useCallback(() => {
    if (!canHoverClip) return;
    const el = clipRef.current;
    if (!el) return;
    if (!el.getAttribute("src")) {
      el.src = clipSrc;
      el.load();
    }
    el.currentTime =
      tile.peer_hook_start_sec != null &&
      Number.isFinite(tile.peer_hook_start_sec) &&
      tile.peer_hook_start_sec > 0
        ? tile.peer_hook_start_sec
        : 0;
    void el.play()
      .then(() => setHoverClip(true))
      .catch(() => setHoverClip(false));
  }, [canHoverClip, clipSrc, tile.peer_hook_start_sec]);

  const stopHoverClip = useCallback(() => {
    setHoverClip(false);
    const el = clipRef.current;
    if (!el) return;
    el.pause();
    el.currentTime = 0;
  }, []);

  const handleHoverClipError = useCallback(() => {
    setHoverClip(false);
  }, []);

  const tileLabel = `Video tham chiếu${handle ? ` ${handle}` : ""}${viewsLabel ? ` · ${viewsLabel}` : ""}${narrative ? `: ${narrative}` : ""}`;

  const videoTile = (
    <div
      className={`relative w-full overflow-hidden rounded-lg ${tileSurfaceClass}`}
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
          onError={handleHoverClipError}
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
        placeholderClassName={panelClass}
        onAllCandidatesFailed={() => setThumbFailed(true)}
      />
      {isDouyin ? (
        <span
          className="gv-mono pointer-events-none absolute left-2 top-2 z-[18] rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-[0.05em] text-white"
          style={{ background: "var(--gv-accent-deep)" }}
          aria-label="Xu hướng Douyin Trung Quốc"
        >
          CN
        </span>
      ) : null}
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

  const cardShellClass = thumbOnly
    ? "block w-full max-w-[168px]"
    : "flex h-full flex-col gap-2.5 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3 transition-colors duration-[120ms] group-hover:border-[color:var(--gv-ink)]";

  const inner = (
    <div className={cardShellClass}>
      {!hideNarrative && narrative ? (
        <p className="m-0 text-[15px] leading-relaxed text-[color:var(--gv-ink-2)]">
          {narrative}
        </p>
      ) : null}
      {videoTile}
    </div>
  );

  const interactiveClass = thumbOnly
    ? "group block w-full max-w-[168px] rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]"
    : "group block h-full w-full min-w-0 rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]";

  if (playable) {
    return (
      <button
        type="button"
        onClick={onPlay}
        className={interactiveClass}
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
        className={interactiveClass}
        aria-label={
          isDouyin
            ? `${tileLabel} — Mở trên Douyin`
            : tileLabel
        }
      >
        {inner}
      </a>
    );
  }

  return <div className={thumbOnly ? "w-full max-w-[168px]" : "h-full w-full min-w-0"}>{inner}</div>;
}

export function DiagnosisReferenceVideoCards({
  tiles,
  label = "Video tham chiếu",
  showLabel = true,
  embedded = false,
  inlineInFinding = false,
}: {
  tiles: DiagnosisReferenceTile[];
  label?: string;
  /** When false, omit the kicker above the grid (parent supplies section chrome). */
  showLabel?: boolean;
  /** Inline in a parent section — no kicker/border chrome; spacing via ``mt-4`` when label hidden. */
  embedded?: boolean;
  /** Compact thumb row inside a gap finding card — prose lives on the finding body. */
  inlineInFinding?: boolean;
}) {
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  // Player list = the playable tiles of this card set, so prev/next moves
  // between this section's references (parity with Explore's modal).
  const playerVideos = useMemo(
    () => tiles.filter((t) => t.playback_url).map(tileToPlayerVideo),
    [tiles],
  );

  if (!tiles.length) return null;

  const playingTile =
    playingIndex != null && tiles[playingIndex]?.playback_url
      ? tiles[playingIndex]
      : null;
  const playing = playingTile ? tileToPlayerVideo(playingTile) : null;
  const playingStartSec =
    playingTile?.peer_hook_start_sec != null &&
    Number.isFinite(playingTile.peer_hook_start_sec) &&
    playingTile.peer_hook_start_sec > 0
      ? playingTile.peer_hook_start_sec
      : undefined;

  return (
    <div
      className={
        inlineInFinding
          ? "mt-3 flex flex-wrap gap-2"
          : embedded && showLabel
            ? undefined
            : "mt-4"
      }
      aria-label={showLabel ? undefined : label || "Video tham chiếu"}
    >
      {showLabel && label && !inlineInFinding ? (
        <p className="gv-mono mb-3 text-[11px] gv-kicker tracking-[0.18em] text-[color:var(--gv-ink-3)]">
          {label}
        </p>
      ) : null}
      <div
        className={
          inlineInFinding
            ? "contents"
            : "grid grid-cols-2 gap-3 min-[640px]:grid-cols-3 min-[1100px]:grid-cols-4"
        }
      >
        {tiles.map((tile, i) => (
          <ReferenceVideoCard
            key={tile.aweme_id || tile.video_url || i}
            tile={tile}
            idx={i}
            hideNarrative={inlineInFinding}
            thumbOnly={inlineInFinding}
            onPlay={tile.playback_url ? () => setPlayingIndex(i) : undefined}
          />
        ))}
      </div>
      {playing ? (
        <Suspense fallback={null}>
          <VideoPlayerModal
            video={playing}
            allVideos={playerVideos}
            startSec={playingStartSec}
            onClose={() => setPlayingIndex(null)}
          />
        </Suspense>
      ) : null}
    </div>
  );
}
