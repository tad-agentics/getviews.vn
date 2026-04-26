import { memo } from "react";
import type { ChannelCadence } from "@/lib/api-types";

/**
 * Studio Home — NHỊP ĐĂNG block (PR-3 / design pack §E.).
 *
 * 14-day boolean calendar grid + a Giờ vàng / Ngày vàng pair below.
 * The grid renders as 14 small squares: dark fill for "posted that
 * day", light fill for "skipped". Today's cell gets an accent outline
 * so creators can locate themselves at a glance.
 *
 * Source of truth:
 * ``cloud-run/getviews_pipeline/channel_analyze.py::_compute_cadence_struct``.
 */

export const ChannelCadenceBlock = memo(function ChannelCadenceBlock({
  cadence,
}: {
  cadence: ChannelCadence;
}) {
  const cells = cadence.posts_14d.length === 14
    ? cadence.posts_14d
    : padTo14(cadence.posts_14d);
  const todayIndex = cells.length - 1;
  return (
    <div>
      <div
        role="img"
        aria-label={`Lịch đăng 14 ngày · ${cadence.weekly_actual} bài tuần này`}
        className="grid grid-cols-[repeat(14,minmax(0,1fr))] gap-1"
      >
        {cells.map((posted, i) => {
          const isToday = i === todayIndex;
          return (
            <span
              key={i}
              aria-hidden
              title={posted ? "Đã đăng" : "Bỏ"}
              className={
                "aspect-square rounded-[3px] " +
                (posted
                  ? "bg-[color:var(--gv-ink)]"
                  : "bg-[color:var(--gv-rule)]") +
                (isToday
                  ? " outline outline-2 outline-offset-[1px] outline-[color:var(--gv-accent)]"
                  : "")
              }
            />
          );
        })}
      </div>
      <div className="gv-mono mt-1.5 flex items-center justify-between text-[9.5px] text-[color:var(--gv-ink-4)]">
        <span>14 ngày trước</span>
        <span>Hôm nay</span>
      </div>

      {(cadence.best_hour || cadence.best_days) ? (
        <div className="mt-3.5 grid grid-cols-2 gap-4">
          {cadence.best_hour ? (
            <div>
              <p className="gv-mono mb-1 text-[9px] font-bold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
                GIỜ VÀNG
              </p>
              <p className="m-0 text-[14px] font-medium text-[color:var(--gv-ink)]">
                {cadence.best_hour}
              </p>
              <p className="m-0 mt-0.5 text-[11px] text-[color:var(--gv-ink-3)]">
                Audience của bạn online cao nhất
              </p>
            </div>
          ) : <span />}
          {cadence.best_days ? (
            <div>
              <p className="gv-mono mb-1 text-[9px] font-bold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
                NGÀY VÀNG
              </p>
              <p className="m-0 text-[14px] font-medium text-[color:var(--gv-ink)]">
                {cadence.best_days}
              </p>
              <p className="m-0 mt-0.5 text-[11px] text-[color:var(--gv-ink-3)]">
                View median cao hơn ngày khác trên kênh
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
});

/** Defensive normalizer — pad / truncate to exactly 14 cells. */
function padTo14(arr: ReadonlyArray<boolean>): boolean[] {
  if (arr.length >= 14) return arr.slice(arr.length - 14);
  // Pad missing earlier days as "skipped".
  const out: boolean[] = new Array(14 - arr.length).fill(false);
  return out.concat(arr as boolean[]);
}
