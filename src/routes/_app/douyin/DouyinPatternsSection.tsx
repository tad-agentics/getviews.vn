import { memo, useMemo } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

import type { DouyinNiche, DouyinPattern } from "@/lib/api-types";

import { DouyinPatternCard } from "./DouyinPatternCard";

/**
 * D5e (2026-06-05) — Kho Douyin · §I "Pattern signals" surface.
 *
 * Sits ABOVE the §II video grid per design pack ``screens/douyin.jsx``
 * §I — 3 cards/niche/week. The BE returns the most-recent week's 3
 * pattern rows per active niche as a flat array; this component
 * groups by ``niche_id`` and renders one 3-up grid per niche, OR a
 * single 3-up grid when the user has filtered to a specific niche.
 *
 * States:
 *
 *   • Loading — small spinner row (the §II grid still renders below).
 *   • No data — null (don't render the section at all). The cron may
 *     not have run yet for first-time deploys.
 *   • Filter narrows to a niche with no patterns — null too. The user
 *     can still browse §II videos for that niche.
 *
 * Loading + render-nothing are quiet on purpose: §I is a complement
 * to §II, not a blocker. If patterns aren't ready, the user still
 * gets the full grid below.
 */

export type DouyinPatternsSectionProps = {
  patterns: DouyinPattern[];
  /** Niches list from ``useDouyinFeed`` — used to label each
   *  per-niche group's heading. Subset of the BE active set. */
  niches: DouyinNiche[];
  /** Active niche slug from the chip filter; ``null`` = "all". When
   *  set, only that niche's patterns render (no per-niche heading). */
  activeNicheSlug: string | null;
  isLoading: boolean;
  /** D6b — when ``useDouyinPatterns`` errors (network blip, 5xx),
   *  render a thin retry banner instead of silently rendering null. */
  isError?: boolean;
  onRetry?: () => void;
};

export const DouyinPatternsSection = memo(function DouyinPatternsSection({
  patterns,
  niches,
  activeNicheSlug,
  isLoading,
  isError = false,
  onRetry,
}: DouyinPatternsSectionProps) {
  // Resolve active niche slug → niche_id once.
  const activeNicheId = useMemo(() => {
    if (!activeNicheSlug) return null;
    return niches.find((n) => n.slug === activeNicheSlug)?.id ?? null;
  }, [activeNicheSlug, niches]);

  // Group patterns by niche_id, scoped to the active filter.
  const groups = useMemo(() => {
    const filtered =
      activeNicheId == null
        ? patterns
        : patterns.filter((p) => p.niche_id === activeNicheId);
    if (filtered.length === 0) return [];
    const byNiche = new Map<number, DouyinPattern[]>();
    for (const p of filtered) {
      const arr = byNiche.get(p.niche_id) ?? [];
      arr.push(p);
      byNiche.set(p.niche_id, arr);
    }
    // Stable order: niche_id ASC, rank ASC within each group.
    const ordered: { niche: DouyinNiche | null; rows: DouyinPattern[] }[] = [];
    const nichesById = new Map(niches.map((n) => [n.id, n]));
    for (const nid of [...byNiche.keys()].sort((a, b) => a - b)) {
      const rows = (byNiche.get(nid) ?? []).slice().sort((a, b) => a.rank - b.rank);
      ordered.push({ niche: nichesById.get(nid) ?? null, rows });
    }
    return ordered;
  }, [patterns, activeNicheId, niches]);

  if (isLoading) {
    return (
      <section
        aria-label="Đang tải Pattern signals"
        className="mb-6 flex items-center gap-2 rounded-lg border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3 text-[color:var(--gv-ink-3)]"
        role="status"
      >
        <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} aria-hidden />
        <span className="text-[13px]">Đang tải Pattern signals…</span>
      </section>
    );
  }

  if (isError) {
    return (
      <section
        role="alert"
        className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3"
      >
        <div className="flex items-center gap-2 text-[color:var(--gv-ink-2)]">
          <AlertCircle
            className="h-4 w-4 text-[color:var(--gv-accent-deep)]"
            strokeWidth={2}
            aria-hidden
          />
          <span className="text-[13px]">
            Không tải được Pattern signals — đang chỉ hiển thị video bên dưới.
          </span>
        </div>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="gv-mono text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)] underline-offset-4 hover:underline"
          >
            Thử lại
          </button>
        ) : null}
      </section>
    );
  }

  if (groups.length === 0) return null;

  // Single-niche filter → simpler 3-up without per-niche heading.
  if (activeNicheId !== null && groups.length === 1) {
    const only = groups[0]!;
    return (
      <section className="mb-6" aria-label="Pattern signals tuần này">
        <SectionHeader />
        <PatternRow rows={only.rows} />
      </section>
    );
  }

  // All niches → render one row per niche with a compact heading.
  return (
    <section className="mb-6" aria-label="Pattern signals tuần này">
      <SectionHeader />
      <div className="flex flex-col gap-5">
        {groups.map(({ niche, rows }) => (
          <div key={niche?.id ?? "unknown"}>
            {niche ? (
              <p className="gv-mono mb-2 text-[10px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-ink-3)]">
                {niche.name_vn}
              </p>
            ) : null}
            <PatternRow rows={rows} />
          </div>
        ))}
      </div>
    </section>
  );
});


function SectionHeader() {
  return (
    <>
      <p className="gv-mono mb-1.5 text-[9px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
        § I — Pattern signals · cập nhật mỗi tuần
      </p>
      <h2 className="gv-tight m-0 mb-3.5 text-[20px] font-medium leading-tight text-[color:var(--gv-ink)]">
        Tuần này creator Douyin đang lặp gì
      </h2>
    </>
  );
}


function PatternRow({ rows }: { rows: DouyinPattern[] }) {
  return (
    <ul
      className="grid gap-3"
      style={{
        gridTemplateColumns:
          "repeat(auto-fill, minmax(min(100%, 280px), 1fr))",
      }}
    >
      {rows.map((p) => (
        <li key={p.id} className="contents">
          <DouyinPatternCard pattern={p} />
        </li>
      ))}
    </ul>
  );
}
