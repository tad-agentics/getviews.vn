import { memo } from "react";
import { useNichePatternStats } from "@/hooks/useNichePatternStats";

/**
 * Trends — pattern-thesis hero (PR-T2).
 *
 * Replaces the niche-intel-snapshot ``TrendsHeroCompact`` with the
 * design pack's editorial thesis hero (``screens/trends.jsx`` lines
 * 331-348): ink-bg card with a week kicker, a single H1 stating the
 * pattern thesis (``"X video tuần qua → Y pattern lặp lại"``), and a
 * 3-stat strip below.
 *
 * Stats:
 *   • VIDEO ĐÃ PHÂN TÍCH — total corpus videos in the niche (30d window)
 *   • PATTERN PHÁT HIỆN — active patterns covering the niche
 *   • ĐỘ MỚI — fresh % (patterns with weekly_instance_count_prev = 0)
 *
 * Pattern stats come from ``useNichePatternStats(nicheId)`` —
 * fetched once and memoized via React Query. The hero stays empty
 * (returns null) when the caller hasn't picked a niche yet.
 */

export const TrendsPatternThesisHero = memo(function TrendsPatternThesisHero({
  nicheId,
  nicheLabel,
  weekKicker,
  corpusCount,
  topCreatorsLabel,
}: {
  nicheId: number | null;
  nicheLabel: string;
  /** "TUẦN 16 · 12.4—18.4" — caller computes for testability. */
  weekKicker: string;
  /** Total corpus videos in the niche; falls back to "—" when null. */
  corpusCount: number | null | undefined;
  /** Optional sub-label for VIDEO ĐÃ PHÂN TÍCH (e.g. "89 creator hàng đầu"). */
  topCreatorsLabel?: string;
}) {
  const { data: stats } = useNichePatternStats(nicheId);
  const videosLabel = formatCorpusCount(corpusCount);
  const patternsLabel = stats?.total != null ? String(stats.total) : "—";
  const freshLabel = stats?.fresh_pct ?? "—";

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
        {videosLabel} video tuần qua →{" "}
        <span className="text-[color:var(--gv-accent)]">
          {patternsLabel} pattern
        </span>{" "}
        lặp lại
      </h1>
      <div className="grid grid-cols-1 gap-5 border-t border-[color:var(--gv-ink-2)] pt-4 sm:grid-cols-3 sm:gap-6">
        <HeroStat
          label="VIDEO ĐÃ PHÂN TÍCH"
          value={videosLabel}
          sub={topCreatorsLabel ?? "Trong 30 ngày"}
        />
        <HeroStat
          label="PATTERN PHÁT HIỆN"
          value={patternsLabel}
          sub="6 đáng chú ý dưới đây"
        />
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

function formatCorpusCount(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  return n.toLocaleString("vi-VN");
}
