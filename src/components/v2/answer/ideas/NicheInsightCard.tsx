/**
 * Phase Wave-2 PR #4 — Layer 0 niche_insight surface.
 *
 * Renders `niche_insight.execution_tip` as a standalone "what to do
 * next" card below the 5-idea stack. This is the most-actionable
 * field Layer 0 produces and creators rated a "top-5-pay-for" feature
 * in the 2026-05 survey — but before Wave 2 PR #1 wired it through,
 * it was 11 rows sitting in `niche_insights` that no Answer-session
 * report ever read.
 *
 * Null-safe: renders nothing when the Layer 0 cron hasn't populated a
 * row for the niche, the row has been quality-flagged, or the row is
 * older than the freshness window (14 days by default). See the
 * usability gates in cloud-run/getviews_pipeline/niche_insight_fetcher.py.
 */

import type { NicheInsightData } from "@/lib/api-types";

export function NicheInsightCard({ insight }: { insight: NicheInsightData | null | undefined }) {
  const tip = insight?.execution_tip?.trim();
  if (!tip) return null;

  const formulaHook = insight?.top_formula_hook?.trim();
  const formulaFormat = insight?.top_formula_format?.trim();
  const formulaBadge = formulaHook && formulaFormat
    ? `${formulaHook} × ${formulaFormat}`
    : formulaHook || formulaFormat || "";

  return (
    <section>
      <p className="gv-kicker gv-kicker--dot mb-2 text-[color:var(--gv-accent-deep)]">
        Gợi ý ngách tuần này
      </p>
      <article className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
        <p className="gv-mono mb-2 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          Hành động ngay
        </p>
        <p className="gv-serif text-[18px] leading-[1.4] text-[color:var(--gv-ink)]">
          {tip}
        </p>
        {formulaBadge ? (
          <p className="gv-mono mt-3 inline-flex rounded border border-[color:var(--gv-rule)] px-2 py-0.5 text-[11px] text-[color:var(--gv-ink-3)]">
            Công thức thắng: {formulaBadge}
          </p>
        ) : null}
      </article>
    </section>
  );
}
