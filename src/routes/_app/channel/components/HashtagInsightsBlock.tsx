/**
 * HashtagInsightsBlock — top hashtag rows with captions from backend templates.
 */

import type { ChannelHashtagInsight } from "@/lib/api-types";

function fmtViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(Math.round(n));
}

interface HashtagInsightsBlockProps {
  insights: ChannelHashtagInsight[];
}

export function HashtagInsightsBlock({ insights }: HashtagInsightsBlockProps) {
  if (!insights.length) {
    return (
      <div className="mt-3 rounded-[12px] border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-3">
        <p className="text-xs text-[color:var(--gv-ink-3)]">
          60 video gần nhất không có hashtag trong caption public — bỏ qua phần này hoặc thêm hashtag ngách vào
          video tiếp theo.
        </p>
      </div>
    );
  }

  return (
    <ul className="mt-3 flex flex-col gap-2">
      {insights.slice(0, 5).map((row) => (
        <li
          key={row.tag}
          className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2.5"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="font-mono text-sm font-semibold text-[color:var(--gv-ink)]">{row.tag}</span>
            <span className="gv-kicker text-[color:var(--gv-ink-3)]">
              ×{row.multiplier.toFixed(2)} · {row.count} video · TB {fmtViews(row.avg_views)}
            </span>
          </div>
          {row.caption ? (
            <p className="mt-1.5 text-xs leading-relaxed text-[color:var(--gv-ink-3)]">{row.caption}</p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
