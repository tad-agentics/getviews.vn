/**
 * Phase 4.4.1 — ChannelProofBlock
 *
 * Spec (v5 audit): renders "Dữ liệu kênh @handle" with two side-by-side cells
 * comparing this video's format range vs the channel's best-performing format.
 * Pattern note is a direct actionable observation (not just a stat).
 *
 * Render conditions:
 *   - channel_context.available === true
 *   - per_format_views has ≥2 formats with n≥3 each
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

function fmtRange(entry: PerFormatEntry): string {
  const lo = fmtViews(entry.min_views);
  const hi = fmtViews(entry.max_views);
  if (lo === hi) return `${lo} views`;
  return `${lo} · ${hi} views`;
}

function atHandle(raw: string | null | undefined): string {
  const s = (raw ?? "").trim();
  if (!s) return "";
  return s.startsWith("@") ? s : `@${s}`;
}

/** Single data cell — shows a format label + view range */
function FormatRangeCell({
  formatKey,
  entry,
  isAnalyzed,
}: {
  formatKey: string;
  entry: PerFormatEntry;
  isAnalyzed: boolean;
}) {
  return (
    <div
      className={`flex flex-col gap-1.5 rounded-[10px] border p-3 ${
        isAnalyzed
          ? "border-[color:var(--gv-accent)]/40 bg-[color:var(--gv-canvas-2)]"
          : "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]"
      }`}
    >
      <p
        className={`gv-mono m-0 text-[18px] font-bold leading-none ${
          isAnalyzed ? "text-[color:var(--gv-accent)]" : "text-[color:var(--gv-ink)]"
        }`}
      >
        {fmtRange(entry)}
      </p>
      <p className="m-0 text-[12px] capitalize text-[color:var(--gv-ink-2)]">
        {formatKey.replace(/_/g, " ")}
        {isAnalyzed ? (
          <span className="ml-1.5 text-[color:var(--gv-ink-4)]">(video này)</span>
        ) : null}
      </p>
      <p className="m-0 text-[10px] text-[color:var(--gv-ink-4)]">
        {fmtViews(entry.avg_views)} TB · {entry.n} video
      </p>
    </div>
  );
}

export function ChannelProofBlock({
  channelContext,
  analyzedFormat,
  creatorHandle,
}: {
  channelContext: ChannelContext;
  analyzedFormat?: string | null;
  creatorHandle?: string | null;
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

  const bestEntry = sorted[0];
  const analyzedKey = analyzedFormat?.toLowerCase().replace(/\s+/g, "_") ?? null;
  const analyzedEntry = analyzedKey
    ? Object.entries(perFormatViews).find(
        ([k]) => k.toLowerCase() === analyzedKey,
      )
    : null;

  // If the analyzed format IS the best, show best + second worst for contrast
  const isBestFormat = analyzedEntry && analyzedEntry[0] === bestEntry[0];
  const contrastEntry =
    isBestFormat && sorted.length > 1 ? sorted[sorted.length - 1] : null;

  // Pattern note
  const patternNote = (() => {
    if (!analyzedEntry) return null;
    if (isBestFormat) {
      return `Video này dùng format '${analyzedFormat}' — đây là format hoạt động tốt nhất trên kênh.`;
    }
    const ratio = bestEntry[1].avg_views / Math.max(analyzedEntry[1].avg_views, 1);
    const times = ratio >= 2 ? `${Math.round(ratio)}×` : "cao hơn đáng kể";
    return `Mỗi lần bạn đăng '${analyzedFormat}' thì lượt xem thấp hơn '${bestEntry[0].replace(/_/g, " ")}' khoảng ${times}. Đây là pattern nhất quán trong ${bestEntry[1].n} video gần nhất.`;
  })();

  const handle = atHandle(creatorHandle);

  return (
    <section className="mb-6" aria-label="Dữ liệu kênh">
      <h3 className="gv-mono mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
        Dữ liệu kênh {handle || ""}
      </h3>

      <div className="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2">
        {/* Best-performing format */}
        <FormatRangeCell
          formatKey={bestEntry[0]}
          entry={bestEntry[1]}
          isAnalyzed={Boolean(isBestFormat)}
        />

        {/* This video's format (or worst-performing if analyzed = best) */}
        {analyzedEntry && !isBestFormat ? (
          <FormatRangeCell
            formatKey={analyzedEntry[0]}
            entry={analyzedEntry[1]}
            isAnalyzed={true}
          />
        ) : contrastEntry ? (
          <FormatRangeCell
            formatKey={contrastEntry[0]}
            entry={contrastEntry[1]}
            isAnalyzed={false}
          />
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
