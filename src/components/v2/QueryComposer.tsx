/**
 * Phase C.1.0 — Studio composer (neo-brutalist shell).
 * UIUX ref: artifacts/uiux-reference/screens/home.jsx Composer.
 */

import { forwardRef, type ReactNode } from "react";
import { ArrowUp } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import type { AnswerHandoffDepth } from "@/lib/answerHandoff";
import {
  STUDIO_COMPOSER_PILLS,
  composerDepthTitles,
  type StudioComposerPill,
} from "@/lib/studioComposer";

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
  /** §4.11.2 — Cơ bản / Chuyên sâu trước khi gửi (Tab Studio + Answer initial). */
  analysisDepth?: AnswerHandoffDepth;
  onAnalysisDepthChange?: (depth: AnswerHandoffDepth) => void;
  /** §3.1.2 — Studio intent pills (Khám Video flop / win / kênh / kịch bản). */
  studioPill?: StudioComposerPill;
  onStudioPillChange?: (pill: StudioComposerPill) => void;
  /** Disable Chuyên sâu on Khám Kênh when credits &lt; channelDeepCreditCost. */
  creditsRemaining?: number;
  channelDeepCreditCost?: number;
  /** Tắt depth picker (mặc định: hiện khi không có followUpSlot). */
  showDepthPicker?: boolean;
  /**
   * Khi có (vd. `/app/answer` follow-up): thay cụm nút studio trái bằng nội dung này;
   * ẩn depth picker.
   */
  followUpSlot?: ReactNode;
};

const FOCUS_RING =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--gv-canvas)]";

const DEPTH_PILL_BASE =
  "inline-flex min-h-[36px] shrink-0 items-center rounded-full border px-3 text-xs font-medium leading-tight transition-colors " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--gv-canvas)] " +
  "disabled:pointer-events-none disabled:cursor-not-allowed disabled:border-[color:var(--gv-rule)] disabled:bg-[color:var(--gv-faint)] disabled:text-[color:var(--gv-ink-4)]";

function depthPillClass(active: boolean): string {
  return active
    ? `${DEPTH_PILL_BASE} border-[color:var(--gv-accent)] bg-[color:var(--gv-accent)] text-[color:var(--gv-paper)] hover:border-[color:var(--gv-accent-deep)] hover:bg-[color:var(--gv-accent-deep)]`
    : `${DEPTH_PILL_BASE} border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)] hover:-translate-y-px hover:shadow-[0_8px_20px_-8px_rgba(0,0,0,0.3)]`;
}

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
      analysisDepth = "basic",
      onAnalysisDepthChange,
      studioPill,
      onStudioPillChange,
      creditsRemaining,
      channelDeepCreditCost = 3,
      showDepthPicker,
      followUpSlot,
    },
    ref,
  ) {
    const submitIfNonEmpty = () => {
      if (!value.trim() || disabled) return;
      onSubmit();
    };

    const depthVisible =
      (showDepthPicker ?? !followUpSlot) && studioPill !== "script";
    const depthTitles = composerDepthTitles(studioPill ?? "video_flop");
    const showStudioPills = studioPill != null && onStudioPillChange != null && !followUpSlot;
    const channelDeepDisabled =
      studioPill === "channel" &&
      creditsRemaining != null &&
      creditsRemaining < channelDeepCreditCost;
    const channelDeepTitle = channelDeepDisabled
      ? `Cần ${channelDeepCreditCost} credit — bạn còn ${creditsRemaining}`
      : depthTitles.deep;

    return (
    <div className="gv-surface-brutal">
      <div className="px-5 pt-4 pb-2">
        <textarea
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
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--gv-rule)] px-3 py-2">
        {followUpSlot ? (
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{followUpSlot}</div>
        ) : (
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
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
        <div className="flex shrink-0 items-center gap-1.5">
          {depthVisible ? (
            <div
              className="flex shrink-0 items-center gap-1.5"
              role="group"
              aria-label="Mức phân tích"
            >
              <button
                type="button"
                className={depthPillClass(analysisDepth === "basic")}
                aria-pressed={analysisDepth === "basic"}
                title={depthTitles.basic}
                disabled={disabled}
                onClick={() => onAnalysisDepthChange?.("basic")}
              >
                Cơ bản
              </button>
              <button
                type="button"
                className={depthPillClass(analysisDepth === "deep")}
                aria-pressed={analysisDepth === "deep"}
                title={channelDeepTitle}
                disabled={disabled || channelDeepDisabled}
                onClick={() => onAnalysisDepthChange?.("deep")}
              >
                Chuyên sâu
              </button>
            </div>
          ) : null}
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
