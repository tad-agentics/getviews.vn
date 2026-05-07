import { memo } from "react";
import { useNichePatternStats } from "@/hooks/useNichePatternStats";

/**
 * Trends — pattern-thesis hero (PR-T2).
 *
 * Creator-first: the hero leads with **pattern** (format đang chạy), then
 * grounds trust with corpus video counts. H1 no longer implies a naive
 * ratio ``videos → patterns``; it states pattern activity (~7d) and corpus
 * context separately.
 *
 * Stats strip (pattern order):
 *   • PATTERN ~7 NGÀY — `patterns_active_this_week` ( có video mới gắn pattern )
 *   • TỔNG PATTERN — active patterns in niche ( `useNichePatternStats` total )
 *   • ĐỘ MỚI — fresh % trên cùng tập pattern đó
 */

const PATTERN_WEEK_SUB =
  "Công thức có thêm video trong ngách trong ~7 ngày (pattern đã gom từ phân tích)";
const PATTERN_TOTAL_SUB = "Tổng pattern đang hoạt động trong ngách (để bạn bắt trend có cơ sở)";

export const TrendsPatternThesisHero = memo(function TrendsPatternThesisHero({
  nicheId,
  nicheLabel,
  weekKicker,
  weekAnalyzedCount,
  totalAnalyzedInNiche,
}: {
  nicheId: number | null;
  nicheLabel: string;
  /** "TUẦN 16 · 12.4—18.4" — caller computes for testability. */
  weekKicker: string;
  /** Videos indexed in the last 7 days for the niche (corpus line in H1). */
  weekAnalyzedCount: number | null | undefined;
  /** All analyzed videos in the niche (corpus line in H1). */
  totalAnalyzedInNiche: number | null | undefined;
}) {
  const { data: stats } = useNichePatternStats(nicheId);
  const headlineVideos = formatStatCount(weekAnalyzedCount);
  const totalVideosLabel = formatStatCount(totalAnalyzedInNiche);
  const headlinePatternsThisWeek = formatStatCount(stats?.patterns_active_this_week);
  const patternsTotalLabel = stats?.total != null ? String(stats.total) : "—";
  const freshLabel = stats?.fresh_pct ?? "—";

  const corpusBits: string[] = [];
  if (headlineVideos !== "—") corpusBits.push(`${headlineVideos} video mới vào kho (~7 ngày)`);
  if (totalVideosLabel !== "—") corpusBits.push(`tổng kho ${totalVideosLabel} video`);
  const corpusSentence = corpusBits.length ? `${corpusBits.join(" · ")}.` : "";

  return (
    <section
      aria-label={`Tổng quan pattern ngách ${nicheLabel}`}
      className="mb-7 rounded-[12px] bg-[color:var(--gv-ink)] px-6 py-7 text-[color:var(--gv-canvas)] sm:px-9 sm:py-8"
    >
      <p className="gv-mono mb-2.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        {weekKicker} · NGÁCH {nicheLabel.toUpperCase()}
      </p>
      <h1
        className="gv-tight m-0 mb-[18px] text-[clamp(28px,4vw,46px)] font-semibold leading-[1.05] tracking-[-0.03em] text-[color:var(--gv-canvas)]"
        style={{ textWrap: "pretty" }}
      >
        <span className="text-[color:var(--gv-accent)]">
          {headlinePatternsThisWeek} pattern
        </span>{" "}
        đang có nhịp trong ngách (~7 ngày).
        {corpusSentence ? ` ${corpusSentence}` : ""}
      </h1>
      <div className="grid grid-cols-1 gap-5 border-t border-[color:var(--gv-ink-2)] pt-4 sm:grid-cols-3 sm:gap-6">
        <HeroStat
          label="PATTERN ~7 NGÀY"
          value={headlinePatternsThisWeek}
          sub={PATTERN_WEEK_SUB}
        />
        <HeroStat label="TỔNG PATTERN" value={patternsTotalLabel} sub={PATTERN_TOTAL_SUB} />
        <HeroStat
          label="ĐỘ MỚI"
          value={freshLabel}
          sub="Pattern còn cửa khai thác"
        />
      </div>
    </section>
  );
});

function HeroStat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div>
      <p className="gv-mono mb-1.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        {label}
      </p>
      <p className="gv-tight m-0 mb-1 text-[28px] font-semibold leading-none tracking-[-0.02em] text-[color:var(--gv-canvas)]">
        {value}
      </p>
      <p className="m-0 text-[11px] leading-[1.4] text-[color:var(--gv-ink-3)]">
        {sub}
      </p>
    </div>
  );
}

function formatStatCount(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString("vi-VN");
}
