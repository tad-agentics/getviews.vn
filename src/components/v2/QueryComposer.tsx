/**
 * Phase C.1.0 — Studio composer (neo-brutalist shell).
 * UIUX ref: artifacts/uiux-reference/screens/home.jsx Composer.
 */

import { forwardRef, type ReactNode } from "react";
import { ArrowUp } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import type { AnswerHandoffDepth } from "@/lib/answerHandoff";

export type QueryComposerProps = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  nicheLabel?: string;
  /** Hiện dòng “NGHIÊN CỨU · …” dưới textarea (tắt trên follow-up). */
  showNicheCaption?: boolean;
  corpusCount?: number;
  disabled?: boolean;
  showUrlChip?: boolean;
  /** §4.11.2 — Cơ bản / Chuyên sâu trước khi gửi (Tab Studio + Answer initial). */
  analysisDepth?: AnswerHandoffDepth;
  onAnalysisDepthChange?: (depth: AnswerHandoffDepth) => void;
  /** Tắt depth picker (mặc định: hiện khi không có followUpSlot). */
  showDepthPicker?: boolean;
  /**
   * Khi có (vd. `/app/answer` follow-up): thay cụm nút studio trái bằng nội dung này;
   * ẩn depth picker.
   */
  followUpSlot?: ReactNode;
};

const DEPTH_PILL_BASE =
  "inline-flex h-10 shrink-0 items-center rounded-md border px-3 text-[13px] leading-tight transition-colors disabled:pointer-events-none disabled:opacity-40";

function depthPillClass(active: boolean): string {
  return active
    ? `${DEPTH_PILL_BASE} border-[var(--gv-ink)] bg-[var(--gv-canvas-2)] font-medium text-[var(--gv-ink)]`
    : `${DEPTH_PILL_BASE} border-[var(--gv-rule)] bg-[var(--gv-paper)] text-[var(--gv-ink-3)] hover:border-[var(--gv-ink-4)] hover:text-[var(--gv-ink)]`;
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
      corpusCount,
      disabled,
      showUrlChip,
      analysisDepth = "basic",
      onAnalysisDepthChange,
      showDepthPicker,
      followUpSlot,
    },
    ref,
  ) {
    const submitIfNonEmpty = () => {
      if (!value.trim() || disabled) return;
      onSubmit();
    };

    const depthVisible = showDepthPicker ?? !followUpSlot;

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
          className="w-full resize-none border-0 bg-transparent font-[family-name:var(--gv-font-sans)] text-[17px] leading-relaxed text-[var(--gv-ink)] outline-none placeholder:text-[var(--gv-ink-4)]"
        />
        {showNicheCaption && nicheLabel ? (
          <p className="mt-1 font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">
            NGHIÊN CỨU · {nicheLabel}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[var(--gv-rule)] px-3 py-2">
        {followUpSlot ? (
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">{followUpSlot}</div>
        ) : depthVisible ? (
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
            <div
              className="inline-flex shrink-0 rounded-md border border-[var(--gv-rule)] p-0.5"
              role="group"
              aria-label="Mức phân tích"
            >
              <button
                type="button"
                className={depthPillClass(analysisDepth === "basic")}
                aria-pressed={analysisDepth === "basic"}
                title="Giải mã nhanh · 1 credit"
                disabled={disabled}
                onClick={() => onAnalysisDepthChange?.("basic")}
              >
                Cơ bản
              </button>
              <button
                type="button"
                className={depthPillClass(analysisDepth === "deep")}
                aria-pressed={analysisDepth === "deep"}
                title="Đầy đủ góc · 2 credit"
                disabled={disabled}
                onClick={() => onAnalysisDepthChange?.("deep")}
              >
                Chuyên sâu
              </button>
            </div>
            {showUrlChip ? (
              <span className="rounded-md border border-[var(--gv-rule)] px-2 py-0.5 font-mono text-[10px] text-[var(--gv-ink-4)]">
                URL detected
              </span>
            ) : null}
            {corpusCount != null ? (
              <span className="font-mono text-[10px] text-[var(--gv-ink-4)]">
                {corpusCount.toLocaleString()}+ video
              </span>
            ) : null}
          </div>
        ) : (
          <div className="min-w-0 flex-1" />
        )}
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
    );
  },
);
