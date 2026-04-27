import { memo, useMemo } from "react";
import { AlertCircle, Loader2 } from "lucide-react";

import type { DouyinNiche, DouyinPattern } from "@/lib/api-types";

import { DouyinPatternCard } from "./DouyinPatternCard";
import { formatFreshnessVN } from "./douyinFormatters";

/**
 * Patterns are written by the weekly D5c cron at Mondays 21:00 UTC.
 * If the most-recent ``computed_at`` we see is older than this many
 * days, the §I header surfaces a "có thể chưa cập nhật" caveat so
 * users know the cards may be stale (e.g. the cron failed last week).
 *
 * 8 days lets a single missed run fly without alarm; two missed runs
 * (≥ 14 days) trigger the caveat.
 */
const STALE_DAYS_BEFORE_CAVEAT = 13;

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

  // D6c — surface the week label + freshness caveat. We pick the most
  // recent ``week_of`` across the active group so a single late-running
  // niche doesn't downgrade the header.
  const headerMeta = useMemo(() => {
    const filtered =
      activeNicheId == null
        ? patterns
        : patterns.filter((p) => p.niche_id === activeNicheId);
    if (filtered.length === 0) return null;
    let latestWeek: string | null = null;
    let latestComputedAtIso: string | null = null;
    let latestComputedAtMs: number | null = null;
    for (const p of filtered) {
      if (p.week_of && (!latestWeek || p.week_of > latestWeek)) {
        latestWeek = p.week_of;
      }
      if (p.computed_at) {
        const t = Date.parse(p.computed_at);
        if (!Number.isNaN(t) && (latestComputedAtMs == null || t > latestComputedAtMs)) {
          latestComputedAtMs = t;
          latestComputedAtIso = p.computed_at;
        }
      }
    }
    const stale =
      latestComputedAtMs != null &&
      (Date.now() - latestComputedAtMs) / 86_400_000 > STALE_DAYS_BEFORE_CAVEAT;
    return { weekOf: latestWeek, computedAt: latestComputedAtIso, stale };
  }, [patterns, activeNicheId]);

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
        <SectionHeader meta={headerMeta} />
        <PatternRow rows={only.rows} />
      </section>
    );
  }

  // All niches → render one row per niche with a compact heading.
  return (
    <section className="mb-6" aria-label="Pattern signals tuần này">
      <SectionHeader meta={headerMeta} />
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


type HeaderMeta = {
  weekOf: string | null;
  computedAt: string | null;
  stale: boolean;
} | null;


/**
 * D7 (2026-06-06) — copy + freshness chip aligned with design pack
 * ``screens/douyin.jsx`` lines 574-596:
 *   - Kicker: "§ I — TÍN HIỆU SỚM · 🇨🇳 PATTERN ĐANG NỔ Ở TQ"
 *   - Headline: "3 pattern đi trước VN 4–10 tuần"
 *   - Sublead explaining the value prop
 *   - Right-side accent-dot pill with "CẬP NHẬT N NGÀY TRƯỚC" (D7c)
 *     OR "có thể chưa cập nhật" caveat when stale (D6c).
 */
function SectionHeader({ meta }: { meta: HeaderMeta }) {
  const weekLabel = meta?.weekOf ? formatWeekVN(meta.weekOf) : null;
  const freshLabel = meta?.computedAt ? formatFreshnessVN(meta.computedAt) : null;
  return (
    <header className="mb-3.5 flex flex-wrap items-baseline justify-between gap-3">
      <div className="min-w-0 flex-1">
        <p className="gv-mono mb-1 text-[9px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
          § I — Tín hiệu sớm · 🇨🇳 Pattern đang nổ ở TQ
        </p>
        <h2 className="gv-tight m-0 text-[22px] font-medium leading-tight text-[color:var(--gv-ink)]">
          3 pattern đi trước VN 4–10 tuần
        </h2>
        <p className="m-0 mt-1.5 max-w-[620px] text-[12.5px] leading-snug text-[color:var(--gv-ink-3)]">
          Cấu trúc lặp lại trên Douyin, đã sub VN, kèm note văn hoá và đánh giá khả
          năng adapt. Click để mở deck đầy đủ.
        </p>
      </div>
      {freshLabel ? (
        <div
          className={
            "inline-flex shrink-0 items-center gap-1.5 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-1.5 " +
            (meta?.stale
              ? "text-[color:var(--gv-accent-deep)]"
              : "text-[color:var(--gv-ink-3)]")
          }
          aria-live="polite"
        >
          <span
            aria-hidden
            className={
              "h-2 w-2 shrink-0 rounded-full " +
              (meta?.stale
                ? "bg-[color:var(--gv-accent-deep)]"
                : "bg-[color:var(--gv-accent)]")
            }
          />
          <span className="gv-mono text-[9px] font-semibold uppercase tracking-[0.06em]">
            {meta?.stale ? "Có thể chưa cập nhật" : freshLabel}
          </span>
          {weekLabel ? (
            <span className="gv-mono text-[9px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
              · Tuần {weekLabel}
            </span>
          ) : null}
        </div>
      ) : (
        <span className="gv-mono shrink-0 text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
          Đang chờ batch đầu tiên
        </span>
      )}
    </header>
  );
}


/**
 * Format an ISO Monday date (e.g. "2026-06-01") as "01/06/2026". The
 * BE stores ``week_of`` as DATE so it always parses cleanly here.
 */
function formatWeekVN(isoDate: string): string {
  // Parse as a UTC date — week_of is always a Monday at 00:00 UTC.
  const m = isoDate.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return isoDate;
  const [, yyyy, mm, dd] = m;
  return `${dd}/${mm}/${yyyy}`;
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
