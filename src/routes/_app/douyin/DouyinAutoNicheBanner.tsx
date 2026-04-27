import { memo } from "react";
import { ArrowRight } from "lucide-react";

/**
 * D4c (2026-06-04) — Auto-niche affordance.
 * D7 (2026-06-06) — copy aligned with design pack
 *   ``screens/douyin.jsx`` lines 720-734. Reframed from
 *   "ưu tiên dựa trên hồ sơ" (suggestion) to "đang lọc theo ngách"
 *   (active filter) so users understand the chip is engaged.
 *
 * Renders a thin strip above the toolbar when the user's
 * ``profiles.primary_niche`` maps to a Douyin slug AND that slug has
 * at least one video in the corpus. The dismiss button clears the
 * chip back to "Tất cả" and reads "MỞ RỘNG → TẤT CẢ NGÁCH" per the
 * design (more direct than a generic X icon).
 *
 * Mounting/un-mounting is the parent's job: ``DouyinScreen`` only
 * renders this when the auto-niche heuristic returns a slug.
 */

export type DouyinAutoNicheBannerProps = {
  /** Niche label rendered inside the bold chip — e.g. "Wellness". */
  nicheLabel: string;
  /** Pre-computed match count for the secondary line. */
  matchCount: number;
  onDismiss: () => void;
};

export const DouyinAutoNicheBanner = memo(function DouyinAutoNicheBanner({
  nicheLabel,
  matchCount,
  onDismiss,
}: DouyinAutoNicheBannerProps) {
  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3"
    >
      <span className="gv-mono shrink-0 text-[9px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
        Đang lọc theo ngách bạn theo dõi
      </span>
      <span className="min-w-0 flex-1 text-[12.5px] text-[color:var(--gv-ink-2)]">
        Hiển thị video Douyin trong ngách{" "}
        <b className="text-[color:var(--gv-ink)]">{nicheLabel}</b> — phù hợp
        ngách bạn đã chọn.{" "}
        <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
          ({matchCount} video)
        </span>
      </span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Mở rộng để xem tất cả ngách"
        className="gv-mono inline-flex shrink-0 items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)] underline-offset-4 hover:underline"
      >
        Mở rộng
        <ArrowRight className="h-3 w-3" strokeWidth={2.2} aria-hidden />
        Tất cả ngách
      </button>
    </div>
  );
});
