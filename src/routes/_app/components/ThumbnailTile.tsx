import { motion } from "motion/react";

export type ThumbnailDominantElement = "face" | "product" | "text" | "environment";
export type ThumbnailFacialExpression =
  | "neutral" | "surprised" | "confused" | "smiling" | "focused";
export type ThumbnailColourContrast = "high" | "medium" | "low";

export type ThumbnailAnalysisData = {
  stop_power_score: number;               // 0–10
  dominant_element: ThumbnailDominantElement;
  text_on_thumbnail: string | null;
  facial_expression: ThumbnailFacialExpression | null;
  colour_contrast: ThumbnailColourContrast;
  why_it_stops: string;
};

const DOMINANT_VI: Record<ThumbnailDominantElement, string> = {
  face: "Mặt người",
  product: "Sản phẩm",
  text: "Chữ",
  environment: "Bối cảnh",
};

const EXPRESSION_VI: Record<ThumbnailFacialExpression, string> = {
  neutral: "trung tính",
  surprised: "ngạc nhiên",
  confused: "bối rối",
  smiling: "cười",
  focused: "tập trung",
};

const CONTRAST_VI: Record<ThumbnailColourContrast, string> = {
  high: "contrast cao",
  medium: "contrast vừa",
  low: "contrast thấp",
};

function scoreLabel(score: number): { label: string; color: string } {
  if (score >= 7.5) return { label: "Stop-power cao", color: "text-emerald-600" };
  if (score >= 5) return { label: "Stop-power vừa", color: "text-amber-600" };
  return { label: "Stop-power thấp", color: "text-rose-600" };
}

/**
 * ThumbnailTile — compact "Vì sao thumbnail này dừng scroll" summary.
 *
 * Renders under the diagnosis bubble when video_diagnosis emits
 * structured_output.thumbnail_analysis. Hidden when null. Complements the
 * HookTimelineStrip: together they answer "did the scroll stop, and what
 * happened in the first 3 seconds if it did?"
 */
export function ThumbnailTile({
  data,
  frameUrl,
}: {
  data: ThumbnailAnalysisData;
  frameUrl?: string | null;
}) {
  const score = Math.max(0, Math.min(10, Number(data.stop_power_score) || 0));
  const scoreMeta = scoreLabel(score);
  const barWidthPct = Math.round(score * 10);

  const traits: string[] = [];
  traits.push(DOMINANT_VI[data.dominant_element]);
  if (data.facial_expression && data.dominant_element === "face") {
    traits.push(`biểu cảm ${EXPRESSION_VI[data.facial_expression]}`);
  }
  traits.push(CONTRAST_VI[data.colour_contrast]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="my-3 flex items-start gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3"
    >
      {frameUrl ? (
        <img
          src={frameUrl}
          alt="Cover frame"
          className="h-16 w-12 flex-shrink-0 rounded object-cover"
          loading="lazy"
        />
      ) : (
        <div className="h-16 w-12 flex-shrink-0 rounded bg-[var(--border)]" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className={`text-xs font-semibold ${scoreMeta.color}`}>
            {scoreMeta.label} — {score.toFixed(1)}/10
          </p>
        </div>
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--border)]">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${barWidthPct}%` }}
            transition={{ duration: 0.4, delay: 0.05, ease: "easeOut" }}
            className={`h-full rounded-full ${
              score >= 7.5
                ? "bg-emerald-500"
                : score >= 5
                ? "bg-amber-500"
                : "bg-rose-500"
            }`}
          />
        </div>
        <p className="mt-1.5 text-xs text-[var(--muted)]">
          {traits.join(" · ")}
          {data.text_on_thumbnail ? (
            <>
              {" · "}
              <span className="rounded bg-[var(--surface)] px-1.5 py-0.5 font-medium text-[var(--ink)]">
                "{data.text_on_thumbnail}"
              </span>
            </>
          ) : null}
        </p>
        <p className="mt-1.5 text-xs leading-relaxed text-[var(--ink)]">
          {data.why_it_stops}
        </p>
      </div>
    </motion.div>
  );
}
