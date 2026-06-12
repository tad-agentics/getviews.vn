/** Performance benchmark chip rendered alongside the kicker.
 *
 * 2026-06-11 redesign: the chip shows the *number that generates* the tier
 * (views ÷ format corpus average, e.g. "0.3× TB FORMAT") instead of an
 * evaluative HIT/FLOP badge — per copy rules the data states the finding.
 * Tier still drives the color tone. Behavior matrix:
 *   - tier "early"            → neutral "MỚI ĐĂNG" chip (age-inconclusive, not a verdict)
 *   - benchmark sample < 10   → no verdict chip at all (thin corpus — no confident claim)
 *   - ratio present           → "N.N× TB FORMAT" toned by tier
 *   - ratio missing (legacy cached reports) → old word labels as fallback
 * BE values come from classify_performance_tier_corpus + refine_performance_tier.
 */

import { formatTierRatio as formatRatio } from "@/lib/videoKpis";

const MIN_BENCHMARK_N = 10;

export function PerformanceTierChip({
  tier,
  ratio,
  benchmarkN,
}: {
  tier: string | undefined;
  /** views ÷ format corpus avg — the number behind the tier. */
  ratio?: number | null;
  /** Corpus sample size behind the benchmark; gates the verdict when thin. */
  benchmarkN?: number | null;
}) {
  if (!tier) return null;
  const lc = tier.toLowerCase();

  if (lc === "early") {
    return (
      <span
        className="gv-mono rounded-[3px] bg-[color:var(--gv-ink-4)]/15 px-[7px] py-[3px] text-[11px] font-bold uppercase tracking-[0.05em] text-[color:var(--gv-ink-3)]"
        aria-label="Video mới đăng — số liệu chưa ổn định"
      >
        MỚI ĐĂNG
      </span>
    );
  }

  let tone: "hit" | "average" | "flop";
  let wordLabel: string;
  if (lc === "hit") {
    tone = "hit";
    wordLabel = "HIT";
  } else if (lc === "flop") {
    tone = "flop";
    wordLabel = "FLOP";
  } else if (lc === "average") {
    tone = "average";
    wordLabel = "TRUNG BÌNH";
  } else {
    return null;
  }

  // Thin benchmark — a confident verdict chip on an unreliable sample is
  // worse than none. (Legacy reports without benchmarkN keep the chip.)
  if (typeof benchmarkN === "number" && benchmarkN < MIN_BENCHMARK_N) {
    return null;
  }

  const numericRatio =
    typeof ratio === "number" && Number.isFinite(ratio) && ratio > 0 ? ratio : null;
  const label = numericRatio !== null ? `${formatRatio(numericRatio)} TB FORMAT` : wordLabel;
  const toneClass =
    tone === "hit"
      ? "bg-[color:var(--gv-pos)]/15 text-[color:var(--gv-pos)]"
      : tone === "flop"
        ? "bg-[color:var(--gv-accent)]/15 text-[color:var(--gv-accent)]"
        : "bg-[color:var(--gv-ink-4)]/15 text-[color:var(--gv-ink-3)]";
  return (
    <span
      className={`gv-mono rounded-[3px] px-[7px] py-[3px] text-[11px] font-bold uppercase tracking-[0.05em] ${toneClass}`}
      aria-label={
        numericRatio !== null
          ? `So với trung bình format: ${formatRatio(numericRatio)}`
          : `Phân loại hiệu suất: ${wordLabel}`
      }
    >
      {label}
    </span>
  );
}
