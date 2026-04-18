import { motion } from "motion/react";
import { Flame, TrendingUp, ArrowRightLeft } from "lucide-react";

export type PatternSpreadNiche = { id: number; label: string };

export type TrendPattern = {
  display_name: string;
  instance_count_week: number;
  instance_count_prev_week: number;
  weekly_delta: number;
  niche_spread_count: number;
  niche_spread: PatternSpreadNiche[];
  signature?: Record<string, unknown>;
};

function formatVN(n: number): string {
  return n.toLocaleString("vi-VN");
}

function deltaLabel(delta: number, prev: number): string {
  if (prev === 0) return delta > 0 ? "mới tuần này" : "—";
  const pct = Math.round((delta / prev) * 100);
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct}% so với tuần trước`;
}

function deltaColor(delta: number): string {
  if (delta > 0) return "text-emerald-600";
  if (delta < 0) return "text-rose-600";
  return "text-[var(--muted)]";
}

/**
 * PatternSpreadStrip — renders the top-delta patterns behind a trend_spike
 * response. Each card answers the "this pattern jumped from skincare →
 * fitness → mẹ bỉm" doomscroll-replacement claim by showing:
 *
 *   • the pattern's display name (rule-based today, Gemini later)
 *   • weekly instance count + delta vs last week
 *   • niche-spread chips (up to 6 shown, "+N" chip for overflow)
 *
 * Backed by patterns[] in structured_output — empty array hides the strip.
 */
export function PatternSpreadStrip({ patterns }: { patterns: TrendPattern[] }) {
  if (!patterns || patterns.length === 0) return null;

  return (
    <div className="my-3">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
        <Flame className="h-3 w-3" strokeWidth={2.2} />
        Pattern lan rộng tuần này
      </p>
      <div className="flex flex-col gap-2">
        {patterns.map((p, i) => (
          <PatternSpreadCard key={`${p.display_name}-${i}`} pattern={p} index={i} />
        ))}
      </div>
    </div>
  );
}

function PatternSpreadCard({
  pattern,
  index,
}: {
  pattern: TrendPattern;
  index: number;
}) {
  const hasSpread = pattern.niche_spread && pattern.niche_spread.length > 0;
  const visibleNiches = hasSpread ? pattern.niche_spread.slice(0, 6) : [];
  const overflow = hasSpread ? Math.max(0, pattern.niche_spread.length - 6) : 0;
  const spreadCount = pattern.niche_spread_count ?? pattern.niche_spread?.length ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay: index * 0.05, ease: "easeOut" }}
      className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3"
    >
      {/* Header: name + weekly instance count + delta */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-[var(--ink)]">
          {pattern.display_name}
        </p>
        <div className="flex flex-shrink-0 items-center gap-1 text-xs">
          <TrendingUp className={`h-3.5 w-3.5 ${deltaColor(pattern.weekly_delta)}`} strokeWidth={2.2} />
          <span className="text-[var(--ink)]">{formatVN(pattern.instance_count_week)} video</span>
        </div>
      </div>
      <p className={`mt-0.5 text-[11px] ${deltaColor(pattern.weekly_delta)}`}>
        {deltaLabel(pattern.weekly_delta, pattern.instance_count_prev_week)}
      </p>

      {/* Niche spread — chips with overflow indicator */}
      {hasSpread ? (
        <div className="mt-2.5">
          <p className="mb-1 flex items-center gap-1 text-[11px] text-[var(--muted)]">
            <ArrowRightLeft className="h-3 w-3" strokeWidth={2} />
            Đã lan sang {spreadCount} ngách
          </p>
          <div className="flex flex-wrap gap-1.5">
            {visibleNiches.map((n) => (
              <span
                key={n.id}
                className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[11px] font-medium text-[var(--ink)]"
              >
                {n.label}
              </span>
            ))}
            {overflow > 0 ? (
              <span className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-2 py-0.5 text-[11px] font-medium text-[var(--muted)]">
                +{overflow}
              </span>
            ) : null}
          </div>
        </div>
      ) : null}
    </motion.div>
  );
}
