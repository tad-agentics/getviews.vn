/**
 * Phase 4.4.1 — ChannelProofBlock
 *
 * Reads channel_context.per_format_views (added in Phase 4.1) and renders
 * winner/loser format cards showing which formats perform best on this channel.
 *
 * Render conditions:
 *   - channel_context.available === true
 *   - per_format_views is not null (i.e. ≥2 formats with n≥3 each)
 *
 * Falls back to the legacy "Ngữ cảnh kênh" section if per_format_views is
 * unavailable (v4 responses from the BE will not have it).
 */

import type { ChannelContext } from "@/lib/api-types";

type PerFormatEntry = {
  n: number;
  avg_views: number;
  median_views: number;
  min_views: number;
  max_views: number;
};

function fmtViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toLocaleString("vi-VN");
}

function FormatCard({
  formatKey,
  entry,
  rank,
}: {
  formatKey: string;
  entry: PerFormatEntry;
  rank: "winner" | "loser" | "neutral";
}) {
  const badgeCls =
    rank === "winner"
      ? "bg-[color:var(--gv-pos)]/15 text-[color:var(--gv-pos)]"
      : rank === "loser"
        ? "bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg)]"
        : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]";
  const borderCls =
    rank === "winner"
      ? "border-[color:var(--gv-pos)]/40"
      : rank === "loser"
        ? "border-[color:var(--gv-rule)]"
        : "border-[color:var(--gv-rule)]";
  const rankLabel =
    rank === "winner" ? "Format mạnh nhất" : rank === "loser" ? "Format yếu nhất" : "Format khác";

  return (
    <div
      className={`flex flex-col gap-2 rounded-[10px] border ${borderCls} bg-[color:var(--gv-paper)] p-3`}
    >
      <div className={`gv-mono inline-self-start rounded px-2 py-0.5 text-[9px] font-semibold uppercase ${badgeCls}`}>
        {rankLabel}
      </div>
      <p className="m-0 text-[13px] font-semibold text-[color:var(--gv-ink)] capitalize">
        {formatKey.replace(/_/g, " ")}
      </p>
      <div className="flex flex-col gap-0.5">
        <p className="gv-mono m-0 text-[18px] font-bold leading-none text-[color:var(--gv-ink)]">
          {fmtViews(entry.avg_views)}
        </p>
        <p className="m-0 text-[10px] text-[color:var(--gv-ink-3)]">
          trung bình · {entry.n} video
        </p>
      </div>
      <p className="m-0 text-[10px] text-[color:var(--gv-ink-4)]">
        median {fmtViews(entry.median_views)} · min {fmtViews(entry.min_views)} · max {fmtViews(entry.max_views)}
      </p>
    </div>
  );
}

export function ChannelProofBlock({
  channelContext,
  analyzedFormat,
}: {
  channelContext: ChannelContext;
  analyzedFormat?: string | null;
}) {
  if (!channelContext.available) return null;

  const perFormatViews = channelContext.per_format_views as
    | Record<string, PerFormatEntry>
    | null
    | undefined;

  if (!perFormatViews || Object.keys(perFormatViews).length < 2) return null;

  const sorted = Object.entries(perFormatViews).sort(
    ([, a], [, b]) => b.avg_views - a.avg_views,
  );
  const winner = sorted[0];
  const loser = sorted[sorted.length - 1];

  const patternNote =
    analyzedFormat && winner
      ? analyzedFormat.toLowerCase() === winner[0].toLowerCase()
        ? `Video này dùng format '${analyzedFormat}' — đây là format hoạt động tốt nhất trên kênh.`
        : `Video này dùng format '${analyzedFormat}' nhưng kênh hoạt động tốt nhất với '${winner[0]}' (${fmtViews(winner[1].avg_views)} TB).`
      : null;

  return (
    <section className="mb-6" aria-label="Bằng chứng kênh theo format">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Bằng chứng kênh · format nào chạy tốt nhất
      </h3>

      <div className="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2">
        {winner ? (
          <FormatCard formatKey={winner[0]} entry={winner[1]} rank="winner" />
        ) : null}
        {loser && loser[0] !== winner?.[0] ? (
          <FormatCard formatKey={loser[0]} entry={loser[1]} rank="loser" />
        ) : null}
      </div>

      {patternNote ? (
        <p className="mt-2 text-[12px] leading-relaxed text-[color:var(--gv-ink-3)]">
          {patternNote}
        </p>
      ) : null}

      {channelContext.median_views != null ? (
        <p className="mt-1 text-[11px] text-[color:var(--gv-ink-4)]">
          Trung vị kênh:{" "}
          <span className="gv-mono font-medium text-[color:var(--gv-ink)]">
            {Math.round(channelContext.median_views).toLocaleString("vi-VN")}
          </span>{" "}
          lượt xem
          {channelContext.sample_size != null
            ? ` · ${channelContext.sample_size} video gần nhất`
            : ""}
        </p>
      ) : null}
    </section>
  );
}

/**
 * Legacy fallback for v4 BE responses that don't include per_format_views.
 * Renders the original Ngữ cảnh kênh card (top/bottom videos list).
 */
export function ChannelContextLegacy({
  channelContext,
  metaTitle,
  metaViews,
}: {
  channelContext: ChannelContext;
  metaTitle?: string | null;
  metaViews: number;
}) {
  if (!channelContext.available) return null;

  const formatViewsVi = (n: number) => n.toLocaleString("vi-VN");

  return (
    <section className="mb-6">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Ngữ cảnh kênh
      </h3>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 min-[1440px]:grid-cols-3">
        {channelContext.top_videos?.slice(0, 2).map((v) => (
          <div
            key={v.aweme_id}
            className="rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3"
          >
            <div className="mb-1 inline-block rounded-full bg-[color:var(--gv-pos)]/15 px-2 py-0.5 font-mono text-[9px] font-semibold uppercase text-[color:var(--gv-pos)]">
              HIT
            </div>
            <p className="truncate text-[12px] text-[color:var(--gv-ink-2)]">
              {v.desc ? `${v.desc.slice(0, 50)}${v.desc.length > 50 ? "…" : ""}` : "—"}
            </p>
            {v.views != null ? (
              <p className="gv-mono mt-1 text-[12px] font-medium text-[color:var(--gv-ink)]">
                {v.views.toLocaleString("vi-VN")} lượt xem
              </p>
            ) : null}
            {v.tiktok_url ? (
              <a
                href={v.tiktok_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 block text-[11px] font-semibold text-[color:var(--gv-accent)] underline underline-offset-2 hover:opacity-90"
              >
                Xem video →
              </a>
            ) : null}
          </div>
        ))}
        <div className="rounded-[10px] border border-[color:var(--gv-accent)]/40 bg-[color:var(--gv-paper)] p-3">
          <div className="mb-1 inline-block rounded-full bg-[color:var(--gv-accent-soft)] px-2 py-0.5 font-mono text-[9px] font-semibold uppercase text-[color:var(--gv-accent)]">
            Video này
          </div>
          <p className="truncate text-[12px] text-[color:var(--gv-ink-2)]">
            {metaTitle
              ? `${metaTitle.slice(0, 50)}${metaTitle.length > 50 ? "…" : ""}`
              : "—"}
          </p>
          <p className="gv-mono mt-1 text-[12px] font-medium text-[color:var(--gv-ink)]">
            {formatViewsVi(metaViews)} lượt xem
          </p>
        </div>
      </div>
      {channelContext.bottom_videos?.length ? (
        <div className="mt-3 grid grid-cols-1 gap-3 min-[700px]:grid-cols-2">
          {channelContext.bottom_videos.slice(0, 2).map((v) => (
            <div
              key={v.aweme_id}
              className="rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3"
            >
              <div className="mb-1 inline-block rounded-full bg-[color:var(--gv-neg-soft)] px-2 py-0.5 font-mono text-[9px] font-semibold uppercase text-[color:var(--gv-neg)]">
                Thấp hơn TB
              </div>
              <p className="truncate text-[12px] text-[color:var(--gv-ink-2)]">
                {v.desc ? `${v.desc.slice(0, 50)}${v.desc.length > 50 ? "…" : ""}` : "—"}
              </p>
              {v.views != null ? (
                <p className="gv-mono mt-1 text-[12px] font-medium text-[color:var(--gv-ink)]">
                  {v.views.toLocaleString("vi-VN")} lượt xem
                </p>
              ) : null}
              {v.tiktok_url ? (
                <a
                  href={v.tiktok_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 block text-[11px] font-semibold text-[color:var(--gv-accent)] underline underline-offset-2 hover:opacity-90"
                >
                  Xem video →
                </a>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
      {channelContext.median_views != null ? (
        <p className="mt-2 text-[12px] text-[color:var(--gv-ink-3)]">
          Trung vị kênh:{" "}
          <span className="gv-mono font-medium text-[color:var(--gv-ink)]">
            {Math.round(channelContext.median_views).toLocaleString("vi-VN")}
          </span>{" "}
          lượt xem
          {channelContext.sample_size != null
            ? ` · ${channelContext.sample_size} video gần nhất`
            : ""}
        </p>
      ) : null}
    </section>
  );
}
