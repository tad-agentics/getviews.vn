import { memo } from "react";
import { useNavigate } from "react-router";
import type { ChannelRecent7dEntry } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

/**
 * Studio Home — "7 NGÀY QUA" briefing block (PR-1 / design pack §B.).
 *
 * Ranked list of the kênh's videos posted in the last 7 days, sorted
 * WIN → AVG → UNDER (server-side; see
 * ``cloud-run/getviews_pipeline/channel_analyze.py::_build_recent_7d``).
 *
 * Each row: vsMedian × multiplier (color-keyed) + verdict pill, hook
 * phrase as title, age/hook category meta, verdict_note explanation.
 * Click routes to /app/video for full diagnosis.
 */

const VERDICT_COLOR: Record<ChannelRecent7dEntry["verdict"], string> = {
  WIN: "text-[color:var(--gv-pos-deep)]",
  AVG: "text-[color:var(--gv-ink-2)]",
  UNDER: "text-[color:var(--gv-neg-deep)]",
};

function formatVsMedian(v: number): string {
  // Display "0.8×" / "1.5×" / "12×". Two decimals only when < 10.
  if (!Number.isFinite(v)) return "—";
  if (v >= 10) return `${Math.round(v)}×`;
  return `${v.toFixed(1).replace(".", ",")}×`;
}

export const ChannelRecent7dList = memo(function ChannelRecent7dList({
  rows,
}: {
  rows: ReadonlyArray<ChannelRecent7dEntry>;
}) {
  const navigate = useNavigate();
  if (rows.length === 0) {
    return (
      <p className="m-0 text-[12.5px] leading-snug text-[color:var(--gv-ink-3)]">
        Chưa có video mới trong 7 ngày qua. Quay lại sau khi bạn đăng thêm để xem điểm mạnh / điểm yếu của từng video.
      </p>
    );
  }
  return (
    <ul aria-label="Video 7 ngày qua" className="flex flex-col">
      {rows.map((v, i) => {
        const tone = VERDICT_COLOR[v.verdict] ?? VERDICT_COLOR.AVG;
        const verdictLabel =
          v.verdict === "WIN" ? "WIN" : v.verdict === "UNDER" ? "UNDER" : "AVG";
        return (
          <li
            key={v.video_id || `${i}-${v.title}`}
            className={
              "grid w-full grid-cols-[auto_1fr_auto] items-start gap-x-3 gap-y-1 py-3 sm:gap-x-4 sm:py-3.5 " +
              (i === 0 ? "" : "border-t border-[color:var(--gv-rule)]")
            }
          >
            <button
              type="button"
              onClick={() => navigate("/app/video")}
              className="contents text-left"
              aria-label={`Mở chi tiết: ${v.title}`}
            >
              <div className="min-w-[56px]">
                <p className={"gv-mono text-[18px] font-bold leading-none tracking-[-0.02em] " + tone}>
                  {formatVsMedian(v.vs_median)}
                </p>
                <p
                  className={
                    "gv-mono mt-1 text-[9px] font-semibold uppercase tracking-[0.08em] " + tone
                  }
                >
                  {verdictLabel}
                </p>
              </div>
              <div className="min-w-0">
                <p className="m-0 truncate text-[14px] font-semibold leading-snug tracking-[-0.01em] text-[color:var(--gv-ink)]">
                  &ldquo;{v.title}&rdquo;
                </p>
                <p className="gv-mono mt-1 text-[11px] text-[color:var(--gv-ink-4)]">
                  {v.age_label}
                  {v.hook_category ? (
                    <>
                      {" · Hook: "}
                      <span className="text-[color:var(--gv-ink-3)]">{v.hook_category}</span>
                    </>
                  ) : null}
                </p>
                <p className="mt-1.5 text-[12px] leading-snug text-[color:var(--gv-ink-3)]" style={{ textWrap: "pretty" }}>
                  {v.verdict_note}
                </p>
              </div>
              <div className="flex flex-col gap-0.5 whitespace-nowrap text-right text-[11px] text-[color:var(--gv-ink-3)]">
                <span>
                  <span className="gv-mono font-semibold text-[color:var(--gv-ink)]">
                    {formatViews(v.views)}
                  </span>{" "}
                  view
                </span>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
});
