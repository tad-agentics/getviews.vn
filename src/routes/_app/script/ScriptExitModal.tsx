import { useEffect } from "react";
import { Save, X } from "lucide-react";

/**
 * S4 — Exit confirmation (per design pack ``screens/script.jsx`` lines
 * 800-835). Shown when the user clicks the "Quay lại Xưởng Viết" header
 * link with unsaved edits in the detail editor.
 *
 * Three actions:
 *   • Hủy             — close modal, stay in editor (also click-outside + Esc)
 *   • Thoát không lưu — discard pending edits, leave
 *   • Lưu & thoát     — save draft, then leave
 */

export type ScriptExitModalProps = {
  open: boolean;
  busy?: boolean;
  onCancel: () => void;
  onDiscard: () => void;
  onSaveAndExit: () => void;
};

export function ScriptExitModal({
  open,
  busy = false,
  onCancel,
  onDiscard,
  onSaveAndExit,
}: ScriptExitModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="script-exit-modal-title"
      className="fixed inset-0 z-[200] flex items-center justify-center bg-[color:color-mix(in_srgb,var(--gv-ink)_40%,transparent)] px-5"
      onClick={onCancel}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[calc(100%-40px)] max-w-[440px] rounded-[8px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6 shadow-[0_12px_40px_rgba(0,0,0,0.18)]"
      >
        <div className="mb-2 flex items-center justify-between">
          <p className="gv-mono text-[9px] font-bold uppercase tracking-[0.18em] text-[color:var(--gv-accent)]">
            CHƯA LƯU
          </p>
          <button
            type="button"
            onClick={onCancel}
            aria-label="Đóng"
            className="text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <h3
          id="script-exit-modal-title"
          className="m-0 mb-2 text-[24px] font-medium leading-tight text-[color:var(--gv-ink)]"
          style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.02em" }}
        >
          Bạn có thay đổi chưa lưu
        </h3>
        <p className="mb-5 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
          Nếu thoát mà không lưu, các thay đổi sẽ mất. Hệ thống không tự động lưu.
        </p>

        <div className="flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-[6px] border border-[color:var(--gv-rule)] bg-transparent px-3 py-1.5 text-[12px] text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-canvas-2)] transition-colors"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={onDiscard}
            className="rounded-[6px] border border-[color:var(--gv-rule)] bg-transparent px-3 py-1.5 text-[12px] text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-canvas-2)] transition-colors"
          >
            Thoát không lưu
          </button>
          <button
            type="button"
            onClick={onSaveAndExit}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-[6px] bg-[color:var(--gv-ink)] px-3 py-1.5 text-[12px] font-semibold text-[color:var(--gv-canvas)] disabled:opacity-50"
          >
            <Save className="h-3 w-3" strokeWidth={2.5} />
            {busy ? "Đang lưu…" : "Lưu & thoát"}
          </button>
        </div>
      </div>
    </div>
  );
}
