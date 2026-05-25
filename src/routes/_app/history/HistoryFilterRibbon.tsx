/**
 * Phase C — /history filter ribbon (answer sessions only).
 */

export type HistoryFilter = "all" | "answer";

export interface HistoryFilterCounts {
  all?: number;
  answer?: number;
}

const CHIPS: ReadonlyArray<{ key: HistoryFilter; label: string }> = [
  { key: "all", label: "Tất cả" },
  { key: "answer", label: "Phiên nghiên cứu" },
];

export function HistoryFilterRibbon({
  value,
  onChange,
  disabled,
  counts,
}: {
  value: HistoryFilter;
  onChange: (next: HistoryFilter) => void;
  disabled?: boolean;
  counts?: HistoryFilterCounts;
}) {
  return (
    <nav
      aria-label="Lọc lịch sử"
      className="flex flex-wrap items-center gap-2"
    >
      {CHIPS.map((c) => {
        const active = value === c.key;
        const n = counts?.[c.key];
        return (
          <button
            key={c.key}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => onChange(c.key)}
            className={`gv-mono inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide transition-colors ${
              active
                ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
                : "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] text-[color:var(--gv-ink-3)] hover:border-[color:var(--gv-ink)]"
            } ${disabled ? "cursor-not-allowed opacity-40" : "cursor-pointer"}`}
          >
            <span>{c.label}</span>
            {typeof n === "number" ? (
              <span className="rounded bg-[color:var(--gv-canvas-2)] px-1.5 text-[11px] font-medium text-[color:var(--gv-ink-2)]">
                {n}
              </span>
            ) : null}
          </button>
        );
      })}
    </nav>
  );
}
