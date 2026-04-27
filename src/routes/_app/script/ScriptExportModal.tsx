import { useEffect, useState } from "react";
import { Check, Download, X } from "lucide-react";
import type { ScriptExportFormat } from "@/lib/api-types";

/**
 * S4 — Export modal (per design pack ``screens/script.jsx`` lines 838-927).
 * Opened from the "Xuất kịch bản" button in the detail header. Renders
 * three radio cards (``shoot`` / ``markdown`` / ``plain``); on submit,
 * the parent runs ``useScriptExport({format})`` + triggers a Blob
 * download with the suggested file extension.
 *
 * Click-outside cancels (overlay closes the modal); Esc cancels too.
 * Submit shows a brief ``Đã tải`` confirmation before the parent closes
 * the modal — eliminates the dead 100ms where the dialog is open with
 * a stale CTA after the file lands in Downloads.
 */

const FORMATS: ReadonlyArray<{
  id: ScriptExportFormat;
  label: string;
  sub: string;
  ext: string;
}> = [
  {
    id: "shoot",
    label: "Format quay",
    sub: "Bố cục dễ đọc khi quay — VO + shot list + b-roll cues",
    ext: ".txt",
  },
  {
    id: "markdown",
    label: "Markdown",
    sub: "Mở trong Notion, Obsidian, hay editor markdown",
    ext: ".md",
  },
  {
    id: "plain",
    label: "Văn bản",
    sub: "Plain text — paste vào caption hay notes app",
    ext: ".txt",
  },
];

export type ScriptExportModalProps = {
  open: boolean;
  busy?: boolean;
  /** Most recent download succeeded — flips the CTA to ``Đã tải`` for ~1s. */
  exported?: boolean;
  onClose: () => void;
  onExport: (format: ScriptExportFormat) => void;
};

export function ScriptExportModal({
  open,
  busy = false,
  exported = false,
  onClose,
  onExport,
}: ScriptExportModalProps) {
  const [format, setFormat] = useState<ScriptExportFormat>("shoot");

  // Reset selection on each open so the modal opens with the design's
  // default radio (Format quay) checked.
  useEffect(() => {
    if (open) setFormat("shoot");
  }, [open]);

  // Esc key cancels.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="script-export-modal-title"
      className="fixed inset-0 z-[200] flex items-center justify-center bg-[color:color-mix(in_srgb,var(--gv-ink)_40%,transparent)] px-5"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[calc(100%-40px)] max-w-[520px] rounded-[8px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6 shadow-[0_12px_40px_rgba(0,0,0,0.18)]"
      >
        <div className="mb-2 flex items-center justify-between">
          <p className="gv-mono text-[9px] font-bold uppercase tracking-[0.18em] text-[color:var(--gv-accent)]">
            XUẤT KỊCH BẢN
          </p>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="text-[color:var(--gv-ink-3)] hover:text-[color:var(--gv-ink)] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <h3
          id="script-export-modal-title"
          className="m-0 mb-4 text-[24px] font-medium leading-tight text-[color:var(--gv-ink)]"
          style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.02em" }}
        >
          Chọn định dạng
        </h3>

        <div className="mb-5 flex flex-col gap-2">
          {FORMATS.map((f) => {
            const selected = format === f.id;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => setFormat(f.id)}
                aria-pressed={selected}
                className={
                  "flex items-center gap-3 rounded-[6px] px-3.5 py-3 text-left transition-colors " +
                  (selected
                    ? "border border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)]"
                    : "border border-[color:var(--gv-rule)] bg-transparent hover:border-[color:var(--gv-ink-4)]")
                }
              >
                <span
                  aria-hidden="true"
                  className={
                    "flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border " +
                    (selected
                      ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-paper)]"
                      : "border-[color:var(--gv-ink-3)] bg-transparent")
                  }
                >
                  {selected ? (
                    <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]" />
                  ) : null}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold text-[color:var(--gv-ink)]">
                    {f.label}{" "}
                    <span className="gv-mono text-[10px] font-normal text-[color:var(--gv-ink-4)]">
                      {f.ext}
                    </span>
                  </div>
                  <div className="text-[11.5px] leading-snug text-[color:var(--gv-ink-3)]">
                    {f.sub}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-[6px] border border-[color:var(--gv-rule)] bg-transparent px-3 py-1.5 text-[12px] text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-canvas-2)] transition-colors"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={() => onExport(format)}
            disabled={busy}
            className="inline-flex items-center gap-1.5 rounded-[6px] bg-[color:var(--gv-ink)] px-3 py-1.5 text-[12px] font-semibold text-[color:var(--gv-canvas)] disabled:opacity-50"
          >
            {exported ? (
              <Check className="h-3 w-3" strokeWidth={2.5} />
            ) : (
              <Download className="h-3 w-3" strokeWidth={2.5} />
            )}
            {exported ? "Đã tải" : busy ? "Đang xuất…" : "Tải file"}
          </button>
        </div>
      </div>
    </div>
  );
}
