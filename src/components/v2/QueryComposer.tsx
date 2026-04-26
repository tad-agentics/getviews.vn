/**
 * Phase C.1.0 — Studio composer (neo-brutalist shell).
 * UIUX ref: artifacts/uiux-reference/screens/home.jsx Composer.
 */

import { forwardRef, type ReactNode } from "react";
import { Film, Eye, ArrowUp } from "lucide-react";
import { Btn } from "@/components/v2/Btn";

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
  /** e.g. navigate to `/app/video` to paste a link */
  onPasteVideoClick?: () => void;
  /** e.g. seed textarea with @handle prompt */
  onPasteHandleClick?: () => void;
  /**
   * Khi có (vd. `/app/answer` follow-up): thay cụm nút studio trái bằng nội dung này;
   * ẩn dán video / handle.
   */
  followUpSlot?: ReactNode;
};

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
      onPasteVideoClick,
      onPasteHandleClick,
      followUpSlot,
    },
    ref,
  ) {
    const submitIfNonEmpty = () => {
      if (!value.trim() || disabled) return;
      onSubmit();
    };

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
        ) : (
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
            <button
              type="button"
              className="inline-flex h-10 shrink-0 items-center gap-1.5 rounded-md border border-[var(--gv-rule)] bg-[var(--gv-paper)] px-3 text-[13px] leading-tight text-[var(--gv-ink)]"
              onClick={onPasteVideoClick}
            >
              <Film className="size-3 shrink-0" /> Dán link video
            </button>
            <button
              type="button"
              className="hidden h-10 shrink-0 items-center gap-1.5 rounded-md border border-[var(--gv-rule)] bg-[var(--gv-paper)] px-3 text-[13px] leading-tight text-[var(--gv-ink)] sm:inline-flex"
              onClick={onPasteHandleClick}
            >
              <Eye className="size-3 shrink-0" /> Dán @handle
            </button>
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
