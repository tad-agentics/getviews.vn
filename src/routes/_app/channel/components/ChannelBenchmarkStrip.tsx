import { formatVN } from "@/lib/formatters";
import type { ChannelQuickPeek } from "@/hooks/useChannelQuickPeek";
import {
  benchmarkBarPct,
  benchmarkRankLabel,
  formatEngagementPct,
} from "@/lib/channelBenchmarkRank";

function normalizeEngagement(value: number): number {
  return value <= 1 ? value * 100 : value;
}

type BenchmarkRow = {
  key: string;
  label: string;
  userLabel: string;
  nicheLabel: string;
  rank: string;
  barPct: number;
};

function buildRows(data: ChannelQuickPeek): BenchmarkRow[] {
  const summary = data.channel_summary;
  const bench = data.niche_benchmarks;
  if (!summary || !bench || bench.channel_count < 1) return [];

  const viewsUser = summary.avg_views;
  const viewsP50 = bench.avg_views_p50;
  const viewsP75 = bench.avg_views_p75;

  const erUser = normalizeEngagement(summary.engagement_rate_pct);
  const erP50 = normalizeEngagement(bench.engagement_p50);
  const erP75 = normalizeEngagement(bench.engagement_p75);

  const cadenceUser = summary.posts_per_week;
  const cadenceP50 = bench.posts_per_week_p50;
  const cadenceP75 = bench.posts_per_week_p75;

  return [
    {
      key: "views",
      label: "View trung bình",
      userLabel: formatVN(viewsUser),
      nicheLabel: `Ngách: ${formatVN(viewsP50)}`,
      rank: benchmarkRankLabel(viewsUser, viewsP50, viewsP75),
      barPct: benchmarkBarPct(viewsUser, viewsP75),
    },
    {
      key: "engagement",
      label: "Tương tác",
      userLabel: formatEngagementPct(erUser),
      nicheLabel: `vs ngách ${formatEngagementPct(erP50)}`,
      rank: benchmarkRankLabel(erUser, erP50, erP75),
      barPct: benchmarkBarPct(erUser, erP75),
    },
    {
      key: "cadence",
      label: "Tần suất đăng",
      userLabel: `${cadenceUser.toFixed(1)} / tuần`,
      nicheLabel: `Top 25%: ${cadenceP75.toFixed(1)}+`,
      rank: benchmarkRankLabel(cadenceUser, cadenceP50, cadenceP75),
      barPct: benchmarkBarPct(cadenceUser, cadenceP75),
    },
  ];
}

/** Studio Home — percentile bars vs niche (``niche_channel_benchmarks`` via quick-peek). */
export function ChannelBenchmarkStrip({ data }: { data: ChannelQuickPeek }) {
  const rows = buildRows(data);
  if (rows.length === 0) return null;

  return (
    <div
      className="mb-5 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-4"
      aria-label="So sánh kênh với ngách"
    >
      <p className="gv-kicker mb-3 text-[color:var(--gv-ink-3)]">Tóm tắt kênh · so với ngách</p>
      <ul className="m-0 flex list-none flex-col gap-4 p-0">
        {rows.map((row) => (
          <li key={row.key}>
            <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-2">
              <span className="text-xs font-medium text-[color:var(--gv-ink-2)]">{row.label}</span>
              <span className="gv-mono text-[11px] font-semibold text-[color:var(--gv-accent-deep)]">
                {row.rank}
              </span>
            </div>
            <div
              className="mb-1 h-2 overflow-hidden rounded-full bg-[color:var(--gv-rule)]"
              role="presentation"
            >
              <div
                className="h-full rounded-full bg-[color:var(--gv-accent)] transition-[width] duration-300"
                style={{ width: `${row.barPct}%` }}
              />
            </div>
            <div className="flex flex-wrap justify-between gap-2 text-[11px] text-[color:var(--gv-ink-3)]">
              <span className="gv-mono font-semibold text-[color:var(--gv-ink)]">{row.userLabel}</span>
              <span>{row.nicheLabel}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
