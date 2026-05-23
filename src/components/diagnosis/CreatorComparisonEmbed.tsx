/**
 * Hit/flop channel peer videos — embedded under `channel_pattern` v6 prose (like VideoTileRow).
 */

import type { CreatorComparison, CreatorComparisonVideo } from "@/lib/api-types";

function fmtViews(v: number): string {
  return v >= 1_000_000
    ? `${(v / 1_000_000).toFixed(1)}M`
    : v >= 1_000
      ? `${Math.round(v / 1_000)}K`
      : v.toLocaleString("vi-VN");
}

function CreatorComparisonEvidenceCell({
  label,
  video,
  accent,
}: {
  label: string;
  video: CreatorComparisonVideo;
  accent: "hit" | "flop";
}) {
  const borderCls =
    accent === "hit" ? "border-[color:var(--gv-pos)]" : "border-[color:var(--gv-rule)]";
  const labelCls =
    accent === "hit" ? "text-[color:var(--gv-pos)]" : "text-[color:var(--gv-ink-3)]";
  const url = video.tiktok_url?.trim();
  const captionHint = video.hook_type?.trim();

  return (
    <div
      className={`flex flex-col gap-2 rounded-lg border ${borderCls} bg-[color:var(--gv-paper)] p-3`}
    >
      <span
        className={`gv-kicker ${labelCls}`}
      >
        {label}
      </span>
      {video.thumbnail_url ? (
        <div className="relative mx-auto aspect-[9/16] w-full max-w-[120px] overflow-hidden rounded-md bg-[color:var(--gv-canvas-2)]">
          <img
            src={video.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
          />
        </div>
      ) : null}
      <span className="gv-mono text-[22px] font-bold leading-none text-[color:var(--gv-ink)]">
        {fmtViews(video.views)}
      </span>
      <span className="text-[11px] text-[color:var(--gv-ink-3)]">lượt xem</span>
      {captionHint ? (
        <p className="m-0 line-clamp-2 text-[11px] leading-snug text-[color:var(--gv-ink-2)]">
          {captionHint}
        </p>
      ) : null}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto pt-1 text-[11px] font-semibold text-[color:var(--gv-accent)] underline underline-offset-2 hover:opacity-90"
        >
          Xem video →
        </a>
      ) : (
        <p className="m-0 mt-auto pt-1 text-[11px] text-[color:var(--gv-ink-3)]">
          Chưa có link TikTok cho video này.
        </p>
      )}
    </div>
  );
}

export function CreatorComparisonEmbed({ data }: { data: CreatorComparison }) {
  return (
    <div
      className="mt-4 border-t border-[color:var(--gv-rule)] pt-4"
      aria-label={`So sánh trong kênh ${data.creator_handle}`}
    >
      <p className="mb-3 text-[11px] font-medium gv-kicker tracking-wide text-[color:var(--muted)]">
        So sánh trong kênh · {data.creator_handle}
      </p>

      <div className="grid grid-cols-2 gap-3">
        <CreatorComparisonEvidenceCell
          label="Video có views cao nhất"
          video={data.hit}
          accent="hit"
        />
        <CreatorComparisonEvidenceCell
          label="Video có views thấp nhất"
          video={data.flop}
          accent="flop"
        />
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-3 py-2.5">
        <span className="min-w-0 text-[12px] leading-snug text-[color:var(--gv-ink-2)]">
          Tỉ lệ views cao nhất so với thấp nhất trong mẫu
        </span>
        <span className="gv-mono shrink-0 text-sm font-bold text-[color:var(--gv-ink)]">
          {data.delta.toLocaleString("vi-VN")}×
        </span>
      </div>

      <p className="mt-2 text-[11px] text-[color:var(--gv-ink-3)]">
        Video này đang ở{" "}
        <span className="font-medium text-[color:var(--gv-ink)]">{data.target_percentile}</span> so
        với{" "}
        <span className="font-medium text-[color:var(--gv-ink)]">
          {data.total_posts_analyzed} video
        </span>{" "}
        gần nhất của {data.creator_handle} (median: {fmtViews(data.median_views)} views).
      </p>
    </div>
  );
}
