import { memo } from "react";
import { useTopPatterns, type TopPattern } from "@/hooks/useTopPatterns";

/**
 * Trends — pattern-thesis hero (L2.2 Sprint 7c reshape).
 *
 * Was: led with "0 pattern đang có nhịp" — visually demoralising AND
 * structurally always 0 because ``video_patterns.weekly_instance_count``
 * is not maintained. The other two stats (139 total, 100% "độ mới")
 * were analyst vanity, not creator value.
 *
 * Now: a creator-facing summary of what the Pattern grid below is
 * actually showing. Reuses ``useTopPatterns`` (same query the grid
 * already fires; React Query dedupes) so the hero, Pattern grid, and
 * suggestions all stay consistent. Headline + stats describe **what's
 * working in your niche this week**, not how big the corpus is.
 *
 * Copy is plain Vietnamese — no "lift" jargon. Multipliers are read
 * out as "ăn gấp X lần view trung bình ngách" so the meaning is
 * obvious without analyst training.
 */

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
  /** Videos indexed in the last 7 days for the niche (small caption). */
  weekAnalyzedCount: number | null | undefined;
  /** All analyzed videos in the niche (small caption). */
  totalAnalyzedInNiche: number | null | undefined;
}) {
  // Pull the same data the §I grid renders. React Query dedupes the
  // request so this is a free read.
  const { data: patterns = [] } = useTopPatterns(nicheId);

  const strongCount = patterns.filter((p) => p.tier === "strong").length;
  const earlyCount = patterns.filter((p) => p.tier === "early").length;
  const top = patterns[0] ?? null;
  const corpusCaption = buildCorpusCaption(weekAnalyzedCount, totalAnalyzedInNiche);

  return (
    <section
      aria-label={`Tổng quan công thức trong ngách ${nicheLabel}`}
      className="mb-7 rounded-[12px] bg-[color:var(--gv-ink)] px-6 py-7 text-[color:var(--gv-canvas)] sm:px-9 sm:py-8"
    >
      <p className="gv-mono mb-2.5 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        {weekKicker} · NGÁCH {nicheLabel.toUpperCase()}
      </p>

      <h1
        className="gv-tight m-0 text-[clamp(26px,3.6vw,40px)] font-semibold leading-[1.1] tracking-[-0.025em] text-[color:var(--gv-canvas)]"
        style={{ textWrap: "pretty" }}
      >
        <Headline strongCount={strongCount} earlyCount={earlyCount} />
      </h1>

      {top ? (
        <TopPatternRow pattern={top} />
      ) : (
        <p className="mt-3 max-w-2xl text-[14px] leading-[1.55] text-[color:var(--gv-ink-3)]">
          Đang theo dõi các công thức tiềm năng trong ngách. Khi có công thức
          được nhiều video xác nhận, sẽ hiện ở đây.
        </p>
      )}

      {corpusCaption ? (
        <p className="gv-mono mt-5 text-[10.5px] uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
          {corpusCaption}
        </p>
      ) : null}
    </section>
  );
});

function Headline({
  strongCount,
  earlyCount,
}: {
  strongCount: number;
  earlyCount: number;
}) {
  if (strongCount > 0) {
    const both = earlyCount > 0 ? ` (+${earlyCount} dấu hiệu sớm)` : "";
    return (
      <>
        <span className="text-[color:var(--gv-accent)]">
          {strongCount} công thức
        </span>{" "}
        đang ăn tốt hơn ngách tuần này{both}.
      </>
    );
  }
  if (earlyCount > 0) {
    return (
      <>
        <span className="text-[color:var(--gv-accent)]">{earlyCount} dấu hiệu sớm</span>{" "}
        — chưa đủ video xác nhận, đáng theo dõi.
      </>
    );
  }
  return (
    <>
      Tuần này chưa thấy công thức nổi bật trong ngách.
    </>
  );
}

/**
 * One-row spotlight on the highest-ranked pattern. The Pattern grid
 * below renders the full list — this is the headline-grade preview.
 *
 * Copy is plain Vietnamese: lift is described as "ăn gấp X lần view
 * trung bình ngách", not "↑ X×". Strong-tier vs early-tier framing
 * differs slightly in tone (confident vs cautious).
 */
function TopPatternRow({ pattern }: { pattern: TopPattern }) {
  const hookLine = (pattern.structure?.[0] ?? pattern.display_name)
    .replace(/^(?:Mở|Hook)\s*[:：]\s*/i, "")
    .trim();
  const liftPhrase = formatLiftPhrase(pattern.lift_vs_niche, pattern.tier);
  const handle = pattern.videos[0]?.creator_handle ?? null;

  return (
    <div className="mt-4 max-w-3xl">
      <p className="gv-mono mb-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        Đứng đầu
      </p>
      <p
        className="gv-tight m-0 text-[16px] leading-[1.45] text-[color:var(--gv-canvas)] sm:text-[17px]"
        style={{ textWrap: "pretty" }}
      >
        &ldquo;{hookLine}&rdquo;
      </p>
      {liftPhrase || handle ? (
        <p className="mt-1.5 text-[12.5px] leading-[1.45] text-[color:var(--gv-ink-3)]">
          {liftPhrase}
          {liftPhrase && handle ? " · " : ""}
          {handle ? (
            <>
              tham chiếu <span className="text-[color:var(--gv-canvas)]">@{handle.replace(/^@/, "")}</span>
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}

/** "Ăn gấp 13 lần view trung bình ngách" — plain Vietnamese, no jargon. */
function formatLiftPhrase(
  lift: number | null,
  tier: TopPattern["tier"],
): string {
  if (lift == null || !Number.isFinite(lift) || lift <= 0) return "";
  // Round 1.86 → "1.9", 4.6 → "5". Avoid pretending precision we don't have.
  const liftLabel =
    lift >= 3 ? `${Math.round(lift)} lần` : `${lift.toFixed(1)} lần`;
  if (tier === "strong") {
    return `Ăn gấp ${liftLabel} view trung bình ngách`;
  }
  return `Ăn gấp ${liftLabel} view trung bình ngách (mẫu nhỏ, đang theo dõi)`;
}

function buildCorpusCaption(
  weekCount: number | null | undefined,
  totalCount: number | null | undefined,
): string {
  const fmt = (n: number | null | undefined): string | null =>
    n != null && Number.isFinite(n) ? n.toLocaleString("vi-VN") : null;
  const total = fmt(totalCount);
  const week = fmt(weekCount);
  if (!total && !week) return "";
  if (total && week) return `Cơ sở dữ liệu · ${total} video ngách · ${week} mới tuần này`;
  if (total) return `Cơ sở dữ liệu · ${total} video ngách`;
  return `${week} video ngách mới tuần này`;
}
