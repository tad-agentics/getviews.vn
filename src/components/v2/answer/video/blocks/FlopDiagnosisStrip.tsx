import type { VideoAnalyzeMeta, VideoNicheMeta } from "@/lib/api-types";

const WINNERS_CLAIM_MIN = 10;

function formatViewsVi(n: number): string {
  return n.toLocaleString("vi-VN");
}

export function formatSaveRatePct(meta: VideoAnalyzeMeta): string {
  const r = meta.save_rate;
  if (r == null || Number.isNaN(r)) return "—";
  const pct = r <= 1 ? r * 100 : r;
  return `${pct.toFixed(1)}%`;
}

export function FlopDiagnosisStrip({
  meta,
  nicheMeta,
  retentionEnd,
}: {
  meta: VideoAnalyzeMeta;
  nicheMeta: VideoNicheMeta | null;
  retentionEnd: number | null;
}) {
  const retLabel = retentionEnd != null ? `${Math.round(retentionEnd)}% giữ chân` : "— giữ chân";
  const nicheViews =
    nicheMeta?.avg_views != null && nicheMeta.avg_views > 0
      ? formatViewsVi(nicheMeta.avg_views)
      : "—";
  const isContentClass = nicheMeta?.benchmark_axis === "content_class";
  const cohortLabel = isContentClass ? "Cùng format TB" : "Ngách TB";
  const retSuffix = isContentClass ? "ret cùng format" : "ret ngách TB";
  const winnersLabel = isContentClass ? "video cùng format" : "video thắng trong ngách";
  const nicheRet =
    nicheMeta?.avg_retention != null
      ? `${Math.round(nicheMeta.avg_retention * 100)}% ${retSuffix}`
      : null;
  const winnersN = nicheMeta?.winners_sample_size ?? null;

  return (
    <div className="border-t-2 border-[color:var(--gv-ink)] pt-5">
      <div className="flex flex-wrap gap-x-4 gap-y-1 font-[family-name:var(--gv-font-mono)] text-xs text-[color:var(--gv-ink-3)]">
        <span>
          {formatViewsVi(meta.views)} view · {retLabel} · save {formatSaveRatePct(meta)}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        <span>
          {cohortLabel}: {nicheViews}
          {nicheRet ? ` · ${nicheRet}` : ""}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        {winnersN != null && winnersN >= WINNERS_CLAIM_MIN ? (
          <span>So sánh với {winnersN} {winnersLabel}</span>
        ) : (
          <span className="text-[color:var(--gv-ink-4)]">
            Đang xây dựng pool (≥10 video cần thu thập)
          </span>
        )}
      </div>
    </div>
  );
}
