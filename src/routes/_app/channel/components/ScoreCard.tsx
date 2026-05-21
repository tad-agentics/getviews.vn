/**
 * ScoreCard — 5-row TLDR metrics + educative captions (template from Cloud Run).
 */

import type { ChannelScoreCard as ChannelScoreCardT } from "@/lib/api-types";

function fmtViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(Math.round(n));
}

interface ScoreCardProps {
  card: ChannelScoreCardT;
}

export function ScoreCard({ card }: ScoreCardProps) {
  const c = card.captions ?? {};
  const isContentClassCohort = card.benchmark_axis === "content_class";
  const cohortMeta =
    isContentClassCohort && card.category_label && card.category_label !== "—"
      ? card.category_label
      : isContentClassCohort
        ? "cùng format"
        : "ngách";
  const rows: { key: string; label: string; value: string; caption?: string }[] = [
    {
      key: "percentile",
      label: isContentClassCohort ? "Vị trí trong format" : "Vị trí trong ngách",
      value: `~P${card.percentile_in_niche ?? "—"}`,
      caption: c.percentile,
    },
    {
      key: "trajectory",
      label: "Quỹ đạo",
      value: `${(card.trajectory_delta_pct ?? 0) > 0 ? "+" : ""}${card.trajectory_delta_pct ?? 0}% vs đỉnh`,
      caption: c.trajectory,
    },
    {
      key: "cadence",
      label: "Nhịp đăng (30 ngày)",
      value: `${(card.posts_per_week ?? 0).toFixed(1)} / tuần`,
      caption: c.cadence,
    },
    {
      key: "best_hour",
      label: "Khung giờ mạnh",
      value: `${card.best_hour_range ?? "—"}`,
      caption: c.best_hour,
    },
    {
      key: "peak_recent",
      label: "Đỉnh vs gần đây",
      value: `${fmtViews(card.peak_views ?? 0)} → ${fmtViews(card.recent_avg_views ?? 0)}`,
      caption: c.peak_recent,
    },
  ];

  return (
    <div
      className="mb-5 rounded-[14px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-4 sm:px-5"
      aria-label="Tóm tắt số liệu kênh"
    >
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[color:var(--gv-ink-3)]">
          Tóm tắt nhanh
        </p>
        <p className="text-[10px] text-[color:var(--gv-ink-4)]">
          n={card.sample_size_videos ?? "—"} video · {cohortMeta}
        </p>
      </div>
      <dl className="flex flex-col gap-3">
        {rows.map((row) => (
          <div key={row.key} className="border-b border-[color:var(--gv-rule)] pb-3 last:border-0 last:pb-0">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <dt className="text-xs font-medium text-[color:var(--gv-ink-3)]">{row.label}</dt>
              <dd className="gv-mono text-sm font-semibold tabular-nums text-[color:var(--gv-ink)]">
                {row.value}
              </dd>
            </div>
            {row.caption ? (
              <p className="mt-1.5 text-[11.5px] leading-relaxed text-[color:var(--gv-ink-3)]">
                {row.caption}
              </p>
            ) : null}
          </div>
        ))}
      </dl>
    </div>
  );
}

export function ScoreCardSkeleton() {
  return (
    <div
      className="mb-5 animate-pulse rounded-[14px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-4 sm:px-5"
      aria-hidden
    >
      <div className="mb-3 h-3 w-28 rounded bg-[color:var(--gv-canvas-2)]" />
      <div className="flex flex-col gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="space-y-2 border-b border-[color:var(--gv-rule)] pb-3 last:border-0">
            <div className="flex justify-between gap-2">
              <div className="h-3 w-24 rounded bg-[color:var(--gv-canvas-2)]" />
              <div className="h-4 w-20 rounded bg-[color:var(--gv-canvas-2)]" />
            </div>
            <div className="h-8 w-full rounded bg-[color:var(--gv-canvas-2)] opacity-70" />
          </div>
        ))}
      </div>
    </div>
  );
}
