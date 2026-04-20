/**
 * Phase C.6.2 — /history row.
 *
 * Row shape is driven by the `history_union` RPC output:
 *   { id, type: 'answer' | 'chat', format?, niche_id?, title,
 *     turn_count, updated_at }
 *
 * Visual distinction between answer + chat rows (plan §C.6):
 *   - Answer: `NGHIÊN CỨU` chip (`chip-accent`) + optional format sub-pill
 *     (Pattern / Ideas / Timing / Generic).
 *   - Chat: `HỘI THOẠI` chip (neutral) — legacy readonly browse.
 *
 * Active row styling (when the route owns a `session` query param):
 *   `background: var(--gv-accent-soft), borderLeft: 3px solid var(--gv-accent)`.
 */

import type { HistoryUnionRow } from "@/hooks/useHistoryUnion";

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const d = Math.floor((Date.now() - t) / 86_400_000);
  if (d <= 0) return "Hôm nay";
  if (d === 1) return "Hôm qua";
  if (d < 7) return `${d} ngày`;
  return new Date(iso).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
}

function formatLabelVi(format: string | null | undefined): string | null {
  switch (format) {
    case "pattern":
      return "Pattern";
    case "ideas":
      return "Ideas";
    case "timing":
      return "Timing";
    case "generic":
      return "Tổng quát";
    default:
      return null;
  }
}

function TypePill({ type }: { type: "answer" | "chat" }) {
  if (type === "answer") {
    return (
      <span className="gv-mono inline-flex items-center rounded border border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] px-2 py-[2px] text-[10px] uppercase tracking-wide text-[color:var(--gv-accent-deep)]">
        Nghiên cứu
      </span>
    );
  }
  return (
    <span className="gv-mono inline-flex items-center rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-[2px] text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-3)]">
      Hội thoại
    </span>
  );
}

function FormatSubPill({ format }: { format: string | null | undefined }) {
  const label = formatLabelVi(format);
  if (!label) return null;
  return (
    <span className="gv-mono inline-flex items-center rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-[2px] text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-3)]">
      {label}
    </span>
  );
}

export function HistoryRow({
  row,
  active,
  onClick,
  actions,
}: {
  row: HistoryUnionRow;
  active?: boolean;
  onClick: () => void;
  /** Right-column controls (rename / delete) rendered only for legacy chat rows. */
  actions?: React.ReactNode;
}) {
  const title =
    (row.title || "").trim() ||
    (row.type === "answer" ? "Phiên nghiên cứu" : "Hội thoại cũ");
  return (
    <div
      className={`flex w-full items-stretch gap-2 border-l-[3px] transition-colors duration-[120ms] ${
        active
          ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)]"
          : "border-transparent hover:bg-[color:var(--gv-canvas-2)]"
      }`}
    >
      <button
        type="button"
        onClick={onClick}
        className="min-h-[44px] flex-1 px-3 py-3 text-left"
      >
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <TypePill type={row.type} />
          <FormatSubPill format={row.format} />
          <span className="gv-mono ml-auto text-[10px] text-[color:var(--gv-ink-4)]">
            {relativeTime(row.updated_at)}
          </span>
        </div>
        <p className="line-clamp-2 text-[14px] leading-snug text-[color:var(--gv-ink)]">
          {title}
        </p>
        <p className="gv-mono mt-1 text-[11px] text-[color:var(--gv-ink-4)]">
          {row.turn_count} {row.type === "answer" ? "lượt" : "tin nhắn"}
        </p>
      </button>
      {actions ? (
        <div className="flex flex-shrink-0 flex-col justify-center gap-1 pr-1">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
