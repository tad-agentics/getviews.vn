/**
 * Phase C — /history row (answer sessions only).
 */

import type { HistoryUnionRow } from "@/hooks/useHistoryUnion";
import { calendarDaysAgoInVn, VN_TIME_ZONE } from "@/lib/formatters";

export function relativeTime(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const d = calendarDaysAgoInVn(iso, now);
  if (d <= 0) {
    const time = new Date(iso).toLocaleTimeString("vi-VN", {
      timeZone: VN_TIME_ZONE,
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
    return `Hôm nay · ${time}`;
  }
  if (d === 1) return "Hôm qua";
  if (d < 7) return `${d} ngày`;
  return new Date(iso).toLocaleDateString("vi-VN", {
    timeZone: VN_TIME_ZONE,
    day: "2-digit",
    month: "2-digit",
  });
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

function FormatSubPill({ format }: { format: string | null | undefined }) {
  const label = formatLabelVi(format);
  if (!label) return null;
  return (
    <span className="gv-mono inline-flex items-center rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-[2px] text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
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
  actions?: React.ReactNode;
}) {
  const title = (row.title || "").trim() || "Phiên nghiên cứu";
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
          <span className="gv-mono inline-flex items-center rounded border border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] px-2 py-[2px] text-[11px] gv-kicker tracking-wide text-[color:var(--gv-accent-deep)]">
            Nghiên cứu
          </span>
          <FormatSubPill format={row.format} />
          <span className="gv-mono ml-auto text-[11px] text-[color:var(--gv-ink-4)]">
            {relativeTime(row.updated_at)}
          </span>
        </div>
        <p className="line-clamp-2 text-[14px] leading-snug text-[color:var(--gv-ink)]">
          {title}
        </p>
        <p className="gv-mono mt-1 text-[11px] text-[color:var(--gv-ink-3)]">
          {row.turn_count} lượt
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
