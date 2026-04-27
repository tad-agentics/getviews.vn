import { memo } from "react";
import { Sparkles, X } from "lucide-react";

/**
 * D4c (2026-06-04) — Auto-niche affordance.
 *
 * Renders a thin highlight strip above the toolbar when the user's
 * ``profiles.primary_niche`` maps to a Douyin slug AND that slug has at
 * least one video in the corpus. The ``onDismiss`` handler clears the
 * niche chip back to "Tất cả" — the user keeps full control.
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
      className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-[color:var(--gv-pos-deep)] bg-[color:var(--gv-pos-soft)] px-4 py-3"
    >
      <div className="flex items-start gap-2.5">
        <Sparkles
          className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--gv-pos-deep)]"
          strokeWidth={2}
          aria-hidden
        />
        <div className="min-w-0">
          <p className="text-[13px] font-medium text-[color:var(--gv-ink)]">
            Đang ưu tiên ngách{" "}
            <span className="font-semibold text-[color:var(--gv-pos-deep)]">
              {nicheLabel}
            </span>{" "}
            dựa trên hồ sơ của bạn.
          </p>
          <p className="gv-mono mt-0.5 text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-3)]">
            {matchCount} video khớp · bấm "Tất cả" hoặc dấu X để xem toàn bộ
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Bỏ ưu tiên ngách"
        className="ml-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[color:var(--gv-ink-3)] transition-colors hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)]"
      >
        <X className="h-3.5 w-3.5" strokeWidth={2} />
      </button>
    </div>
  );
});
