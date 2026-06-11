/**
 * Phase C.1.0 — Studio composer (neo-brutalist shell).
 * UIUX ref: artifacts/uiux-reference/screens/home.jsx Composer.
 */

import { forwardRef, type ReactNode } from "react";
import { ArrowUp } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { STUDIO_COMPOSER_PILLS, type StudioComposerPill } from "@/lib/studioComposer";

export type { StudioComposerPill };

export type QueryComposerProps = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  nicheLabel?: string;
  /** Hiện dòng “NGHIÊN CỨU · …” dưới textarea (tắt trên follow-up). */
  showNicheCaption?: boolean;
  disabled?: boolean;
  /** Valid TikTok URL detected — success chip. */
  showUrlChip?: boolean;
  /** Non-TikTok or unknown HTTP URL — danger chip (blocks honest analysis). */
  urlInvalidMessage?: string;
  /** §3.1.2 — Studio intent pills (Khám Video flop / win / kênh / kịch bản). */
  studioPill?: StudioComposerPill;
  onStudioPillChange?: (pill: StudioComposerPill) => void;
  /**
   * Khi có (vd. `/app/answer` follow-up): thay cụm nút studio trái bằng nội dung này.
   */
  followUpSlot?: ReactNode;
};

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--gv-canvas)]";

function intentPillClass(active: boolean): string {
  return active
    ? "inline-flex min-h-[36px] shrink-0 items-center rounded-full border border-[var(--gv-ink)] bg-[var(--gv-canvas-2)] px-3 text-xs font-medium text-[var(--gv-ink)]"
    : "inline-flex min-h-[36px] shrink-0 items-center rounded-full border border-[var(--gv-rule)] bg-[var(--gv-paper)] px-3 text-xs text-[var(--gv-ink-3)] hover:border-[var(--gv-ink-4)] hover:text-[var(--gv-ink)]";
}

export const QueryComposer = forwardRef<HTMLTextAreaElement, QueryComposerProps>(
  function QueryComposer(
    {
      value,
      onChange,
      onSubmit,
      placeholder = "Hỏi về hook, trend, hay kênh…",
      nicheLabel,
      showNicheCaption = true,
      disabled,
      showUrlChip,
      urlInvalidMessage,
      studioPill,
      onStudioPillChange,
      followUpSlot,
    },
    ref,
  ) {
    const submitIfNonEmpty = () => {
      if (!value.trim() || disabled) return;
      onSubmit();
    };

    const showStudioPills = studioPill != null && onStudioPillChange != null && !followUpSlot;

    return (
    <div className="gv-surface-brutal">
      <div className="px-5 pt-4 pb-2">
        <textarea
          key={studioPill ?? "composer"}
          ref={ref}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter" || e.shiftKey) return;
            // Empty: let Enter insert a newline (default) instead of submitting.
            if (!value.trim()) return;
            e.preventDefault();
            submitIfNonEmpty();
          }}
          placeholder={placeholder}
          rows={3}
          disabled={disabled}
          className={`w-full resize-none border-0 bg-transparent font-[family-name:var(--gv-font-sans)] text-[17px] leading-relaxed text-[var(--gv-ink)] placeholder:text-[var(--gv-ink-4)] ${FOCUS_RING}`}
        />
        {showNicheCaption && nicheLabel ? (
          <p className="mt-1 gv-kicker text-[var(--gv-ink-4)]">
            NGHIÊN CỨU · {nicheLabel}
          </p>
        ) : null}
      </div>
      <div className="flex flex-col gap-2 border-t border-[var(--gv-rule)] px-3 py-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        {followUpSlot ? (
          <div className="flex min-w-0 w-full flex-wrap items-center gap-2 sm:flex-1">{followUpSlot}</div>
        ) : (
          <div className="flex min-w-0 w-full flex-wrap items-center gap-1.5 sm:flex-1">
            {showStudioPills ? (
              <div
                className="flex min-w-0 flex-wrap gap-1"
                role="group"
                aria-label="Loại phân tích"
              >
                {STUDIO_COMPOSER_PILLS.map((pill) => (
                  <button
                    key={pill.id}
                    type="button"
                    disabled={disabled}
                    className={intentPillClass(studioPill === pill.id)}
                    aria-pressed={studioPill === pill.id}
                    onClick={() => onStudioPillChange?.(pill.id)}
                  >
                    {pill.label}
                  </button>
                ))}
              </div>
            ) : null}
            {urlInvalidMessage ? (
              <span
                className="rounded-md border border-[color:var(--gv-accent-deep)] bg-[color:var(--gv-accent-soft)] px-2 py-0.5 gv-kicker text-[color:var(--gv-accent-deep)]"
                role="alert"
              >
                {urlInvalidMessage}
              </span>
            ) : showUrlChip ? (
              <span className="rounded-md border border-[var(--gv-rule)] px-2 py-0.5 gv-kicker text-[var(--gv-ink-4)]">
                Đã nhận link TikTok ✓
              </span>
            ) : null}
          </div>
        )}
        <div className="flex w-full min-w-0 items-center gap-1.5 sm:w-auto sm:shrink-0">
          <Btn
            variant="accent"
            size="md"
            type="button"
            onClick={submitIfNonEmpty}
            disabled={Boolean(disabled) || !value.trim()}
            className="shrink-0"
          >
            <span>Gửi</span>
            <ArrowUp className="size-3.5" strokeWidth={2} aria-hidden />
          </Btn>
        </div>
      </div>
    </div>
    );
  },
);
