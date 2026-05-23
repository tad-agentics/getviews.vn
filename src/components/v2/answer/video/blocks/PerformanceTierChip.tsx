/** Performance tier chip rendered alongside the kicker so the user
 * sees the verdict — hit / average / flop — before reading the report.
 * BE values come from classify_performance_tier_corpus + refine_performance_tier
 * (combines corpus benchmarks with channel context). Returns null when the BE
 * couldn't benchmark (tier="unknown"), so we don't render a placeholder chip. */
export function PerformanceTierChip({ tier }: { tier: string | undefined }) {
  if (!tier) return null;
  const lc = tier.toLowerCase();
  let label: string;
  let tone: "hit" | "average" | "flop";
  if (lc === "hit") {
    label = "HIT";
    tone = "hit";
  } else if (lc === "flop") {
    label = "FLOP";
    tone = "flop";
  } else if (lc === "average") {
    label = "TRUNG BÌNH";
    tone = "average";
  } else {
    return null;
  }
  const toneClass =
    tone === "hit"
      ? "bg-[color:var(--gv-pos)]/15 text-[color:var(--gv-pos)]"
      : tone === "flop"
        ? "bg-[color:var(--gv-accent)]/15 text-[color:var(--gv-accent)]"
        : "bg-[color:var(--gv-ink-4)]/15 text-[color:var(--gv-ink-3)]";
  return (
    <span
      className={`gv-mono rounded-[3px] px-[7px] py-[3px] text-[11px] font-bold uppercase tracking-[0.05em] ${toneClass}`}
      aria-label={`Phân loại hiệu suất: ${label}`}
    >
      {label}
    </span>
  );
}
