import { memo } from "react";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { formatViews } from "@/lib/formatters";
import { useCrossNicheBreakouts, type CrossNicheBreakout } from "@/hooks/useCrossNicheBreakouts";

function Tile({ v }: { v: CrossNicheBreakout }) {
  return (
    <a
      href={v.tiktok_url}
      target="_blank"
      rel="noreferrer"
      className="block overflow-hidden rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]"
    >
      <div className="relative aspect-[4/5] bg-[color:var(--gv-ink)]">
        <VideoThumbnail
          thumbnailUrl={v.thumbnail_url}
          videoId={v.video_id}
          className="h-full w-full"
        />
        {v.breakout_multiplier != null ? (
          <span className="absolute left-2 top-2 rounded bg-[color:var(--gv-ink)]/80 px-2 py-0.5 font-[family-name:var(--gv-font-mono)] text-[11px] text-[color:var(--gv-paper)]">
            {v.breakout_multiplier.toFixed(1)}×
          </span>
        ) : null}
      </div>
      <div className="p-2.5">
        <p className="truncate text-xs font-medium text-[color:var(--gv-ink)]">
          @{v.creator_handle}
        </p>
        <p className="font-[family-name:var(--gv-font-mono)] text-[11px] text-[color:var(--gv-ink-3)]">
          {formatViews(v.views)} view
        </p>
      </div>
    </a>
  );
}

/** Cross-niche breakout lane — max 3 tiles outside user junction. */
export const CrossNicheBreakoutLane = memo(function CrossNicheBreakoutLane({
  excludeClassIds,
}: {
  excludeClassIds: number[];
}) {
  const { data: tiles = [] } = useCrossNicheBreakouts(excludeClassIds);

  if (tiles.length === 0) return null;

  return (
    <section className="mb-8" data-testid="cross-niche-breakout-lane">
      <p className="gv-mono mb-1 text-[11px] font-semibold gv-kicker tracking-[0.12em] text-[color:var(--gv-ink-3)]">
        Format đang nổi ở ngách khác
      </p>
      <p className="mb-3 text-sm text-[color:var(--gv-ink-2)]">
        3 video breakout khác ngách/format so với junction của bạn — tham khảo góc quay, không phải rail 7 ngày trong ngách.
      </p>
      <div className="grid grid-cols-3 gap-3">
        {tiles.map((v) => (
          <Tile key={v.video_id} v={v} />
        ))}
      </div>
    </section>
  );
});
