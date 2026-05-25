import type { VideoAnalyzeMeta, VideoNicheMeta } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

const WINNERS_CLAIM_MIN = 10;

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
  isCarousel = false,
}: {
  meta: VideoAnalyzeMeta;
  nicheMeta: VideoNicheMeta | null;
  retentionEnd: number | null;
  isCarousel?: boolean;
}) {
  const retLabel = retentionEnd != null ? `${Math.round(retentionEnd)}% giữ chân` : "— giữ chân";
  const nicheViews =
    nicheMeta?.avg_views != null && nicheMeta.avg_views > 0
      ? formatViews(nicheMeta.avg_views)
      : "—";
  const isContentClass = nicheMeta?.benchmark_axis === "content_class";
  const cohortLabel =
    nicheMeta?.cohort_label?.trim() ||
    (isContentClass ? "Cùng format TB" : "Ngách TB");
  const retSuffix = isContentClass ? "ret cùng format" : "ret ngách TB";
  const winnersLabel = isContentClass ? "video cùng format" : "video thắng trong ngách";
  const nicheRet =
    nicheMeta?.avg_retention != null
      ? `${Math.round(nicheMeta.avg_retention * 100)}% ${retSuffix}`
      : null;
  const winnersN = nicheMeta?.winners_sample_size ?? null;
  const peerLabel = nicheMeta?.peer_percentile_label?.trim();
  const savePct = formatSaveRatePct(meta);
  const carouselSaveHint =
    isCarousel && meta.save_rate != null && !Number.isNaN(meta.save_rate)
      ? (() => {
          const pct = meta.save_rate <= 1 ? meta.save_rate * 100 : meta.save_rate;
          if (pct >= 3) return "save carousel ≥3% — ngưỡng phân phối tốt";
          return "save carousel dưới 3% — thử tăng giá trị từng slide";
        })()
      : null;

  return (
    <div className="border-t-2 border-[color:var(--gv-ink)] pt-5">
      <div className="flex flex-wrap gap-x-4 gap-y-1 font-[family-name:var(--gv-font-mono)] text-xs text-[color:var(--gv-ink-3)]">
        <span>
          {formatViews(meta.views)} view · {retLabel} · save {savePct}
          {carouselSaveHint ? ` · ${carouselSaveHint}` : ""}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        <span>
          {cohortLabel}: {nicheViews}
          {nicheRet ? ` · ${nicheRet}` : ""}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        {winnersN != null && winnersN >= WINNERS_CLAIM_MIN ? (
          <span>
            So sánh với {winnersN} {winnersLabel}
            {peerLabel ? ` · ${peerLabel}` : ""}
          </span>
        ) : peerLabel ? (
          <span>{peerLabel}</span>
        ) : (
          <span className="text-[color:var(--gv-ink-4)]">
            Chưa có nhóm đối chiếu cho video này
          </span>
        )}
      </div>
    </div>
  );
}
