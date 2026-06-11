/**
 * Peer reference videos under v6 diagnosis sections — one card per video with
 * narrative context above the thumbnail (GetReels-style evidence layout).
 */

import { VideoThumbnail } from "@/components/VideoThumbnail";
import {
  formatCreatorHandle,
  referenceTileNarrative,
  type DiagnosisReferenceTile,
} from "@/lib/diagnosisReferenceTiles";
import { formatViews } from "@/lib/formatters";

function ReferenceVideoCard({ tile }: { tile: DiagnosisReferenceTile }) {
  const href = tile.video_url || undefined;
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
  if (!tiles.length) return null;

  return (
    <div className="mt-4 border-t border-[color:var(--gv-rule)] pt-4" aria-label={label}>
      <p className="mb-3 text-[11px] font-medium gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
        {label}
      </p>
      <div className="grid grid-cols-1 gap-3 min-[640px]:grid-cols-2 min-[1100px]:grid-cols-3">
        {tiles.map((tile, i) => (
          <ReferenceVideoCard key={tile.aweme_id || tile.video_url || i} tile={tile} />
        ))}
      </div>
    </div>
  );
}
