/**
 * Phase C.1.0 — Studio composer (neo-brutalist shell).
 * UIUX ref: artifacts/uiux-reference/screens/home.jsx Composer.
 */

import { Paperclip, Mic, Film, Eye, ArrowUp } from "lucide-react";

export type QueryComposerProps = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  nicheLabel?: string;
  corpusCount?: number;
  disabled?: boolean;
  showUrlChip?: boolean;
};

export function QueryComposer({
  value,
  onChange,
  onSubmit,
  placeholder = "Hỏi về hook, trend, hay kênh…",
  nicheLabel,
  corpusCount,
  disabled,
  showUrlChip,
}: QueryComposerProps) {
  return (
    <div className="gv-surface-brutal">
      <div className="px-5 pt-4 pb-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder={placeholder}
          rows={3}
          disabled={disabled}
          className="w-full resize-none border-0 bg-transparent font-[family-name:var(--gv-font-sans)] text-[17px] leading-relaxed text-[var(--gv-ink)] outline-none placeholder:text-[var(--gv-ink-4)]"
        />
        {nicheLabel ? (
          <p className="mt-1 font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">
            NGHIÊN CỨU · {nicheLabel}
          </p>
        ) : null}
      </div>
      <div className="flex items-center justify-between border-t border-[var(--gv-rule)] px-3 py-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-[var(--gv-rule)] bg-[var(--gv-paper)] px-2 py-1 text-[13px] text-[var(--gv-ink)]"
            title="Đính kèm"
          >
            <Paperclip className="size-3" />
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md border border-[var(--gv-rule)] bg-[var(--gv-paper)] px-2 py-1 text-[13px] text-[var(--gv-ink)]"
          >
            <Film className="size-3" /> Dán link video
          </button>
          <button
            type="button"
            className="hidden items-center gap-1 rounded-md border border-[var(--gv-rule)] bg-[var(--gv-paper)] px-2 py-1 text-[13px] text-[var(--gv-ink)] sm:inline-flex"
          >
            <Eye className="size-3" /> Dán @handle
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
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="hidden items-center gap-1 rounded-md border border-[var(--gv-rule)] bg-[var(--gv-paper)] px-2 py-1 text-[13px] sm:inline-flex"
            aria-label="Mic"
          >
            <Mic className="size-3" />
          </button>
          <button
            type="button"
            onClick={onSubmit}
            disabled={disabled}
            className="btn btn-accent inline-flex items-center gap-1.5 px-3 py-2 disabled:opacity-40"
          >
            <span>Gửi</span>
            <ArrowUp className="size-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
