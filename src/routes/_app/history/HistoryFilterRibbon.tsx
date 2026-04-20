/**
 * Phase C.6.2 — /history filter ribbon (plan §C.6 design spec).
 *
 * 3-chip ribbon: `Tất cả` / `Phiên nghiên cứu` / `Hội thoại`. Active chip
 * uses `--gv-accent-soft` background + `--gv-accent` text, mirrors the
 * row type pill for consistency. Count badges render when supplied.
 *
 * Disabled during an active search (search operates on chat_sessions
 * only today; filter behaviour would confuse the user).
 */

export type HistoryFilter = "all" | "answer" | "chat";

export interface HistoryFilterCounts {
  all?: number;
  answer?: number;
  chat?: number;
}

const CHIPS: ReadonlyArray<{ key: HistoryFilter; label: string }> = [
  { key: "all", label: "Tất cả" },
  { key: "answer", label: "Phiên nghiên cứu" },
  { key: "chat", label: "Hội thoại" },
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
              <span className="rounded bg-[color:var(--gv-canvas-2)] px-1.5 text-[10px] font-medium text-[color:var(--gv-ink-2)]">
                {n}
              </span>
            ) : null}
          </button>
        );
      })}
    </nav>
  );
}
