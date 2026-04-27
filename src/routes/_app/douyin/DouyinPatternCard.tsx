import { memo } from "react";
import { TrendingUp } from "lucide-react";

import type { DouyinPattern } from "@/lib/api-types";

import { formatRisePct } from "./douyinFormatters";

/**
 * D5e (2026-06-05) — Kho Douyin · single pattern card.
 *
 * Per design pack ``screens/douyin.jsx`` § I — "Pattern signals".
 * One card per row in the weekly batch (rank 1-3). Compact dark-on-
 * canvas card with the pattern name as the H3, the fill-in-the-blank
 * hook template as the headline, and the format signature + signal
 * strength as the secondary lines.
 *
 * Click target is the whole card; the parent decides what happens
 * (D5e ships a no-op since the §II video grid is the source of
 * truth for drilldown — sample_video_ids let us highlight matching
 * videos in a follow-up PR).
 */

export type DouyinPatternCardProps = {
  pattern: DouyinPattern;
};

export const DouyinPatternCard = memo(function DouyinPatternCard({
  pattern,
}: DouyinPatternCardProps) {
  const rise = formatRisePct(pattern.cn_rise_pct_avg);
  return (
    <article
      data-rank={pattern.rank}
      data-niche-id={pattern.niche_id}
      className="flex flex-col gap-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-4 transition-colors hover:border-[color:var(--gv-ink-4)]"
    >
      <header className="flex items-baseline justify-between gap-2">
        <span
          className="gv-mono inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[10px] font-semibold text-[color:var(--gv-ink-3)]"
          aria-label={`Pattern hạng ${pattern.rank}`}
        >
          {pattern.rank}
        </span>
        {rise ? (
          <span
            className="gv-mono inline-flex items-center gap-1 text-[10px] font-medium"
            style={{ color: "var(--gv-pos-deep)" }}
            aria-label={`Tăng trung bình ${rise} so với 14 ngày trước`}
          >
            <TrendingUp className="h-3 w-3" strokeWidth={2} aria-hidden />
            {rise}
          </span>
        ) : null}
      </header>

      <h3
        className="gv-tight m-0 text-[15px] font-medium leading-snug text-[color:var(--gv-ink)]"
      >
        {pattern.name_vn}
      </h3>

      {/* Hook template — fill-in-the-blank, the design's "money line".
          The literal "___" blank is preserved so the user sees the
          adaptable shape of the hook. */}
      <p className="rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-2 text-[12.5px] italic leading-snug text-[color:var(--gv-ink-2)]">
        &quot;{pattern.hook_template_vi}&quot;
      </p>

      {/* Format signature */}
      <p className="line-clamp-3 text-[11.5px] leading-snug text-[color:var(--gv-ink-3)]">
        {pattern.format_signal_vi}
      </p>

      <footer className="mt-auto flex items-center justify-between gap-2 text-[10px] text-[color:var(--gv-ink-4)]">
        <span className="gv-mono">
          {pattern.sample_video_ids.length} video mẫu
        </span>
        {pattern.name_zh ? (
          <span className="gv-mono italic" lang="zh">
            {pattern.name_zh}
          </span>
        ) : null}
      </footer>
    </article>
  );
});
