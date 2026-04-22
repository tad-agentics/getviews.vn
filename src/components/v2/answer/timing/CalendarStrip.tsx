/**
 * Content-calendar strip — 7-day grid rendered below the Timing heatmap
 * when ``calendar_slots`` is non-empty.
 *
 * Added 2026-04-22 as part of absorbing the ``content_calendar`` intent
 * into the Timing template (see ``artifacts/docs/report-template-prd-
 * timing-calendar.md``). Hidden when the array is empty so pure timing
 * queries keep the existing heatmap-only layout.
 *
 * Design tokens only (no hardcoded hex) — the ``check-tokens.mjs``
 * guard fails the build on raw hex in ``src/``. Chip colours per kind
 * come from existing tokens.
 */

import type { CalendarSlotData } from "@/lib/api-types";

const DAYS_VN: ReadonlyArray<{ idx: number; label: string }> = [
  { idx: 0, label: "Thứ 2" },
  { idx: 1, label: "Thứ 3" },
  { idx: 2, label: "Thứ 4" },
  { idx: 3, label: "Thứ 5" },
  { idx: 4, label: "Thứ 6" },
  { idx: 5, label: "Thứ 7" },
  { idx: 6, label: "CN" },
];

const KIND_LABELS: Record<CalendarSlotData["kind"], string> = {
  pattern: "Pattern",
  ideas: "Ý tưởng",
  timing: "Thời điểm",
  repost: "Repost",
};

const KIND_CHIP_CLASS: Record<CalendarSlotData["kind"], string> = {
  // Background + foreground token pairs that exist in ``src/app.css``.
  pattern: "bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]",
  ideas: "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]",
  timing: "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-2)]",
  repost: "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]",
};

export function CalendarStrip({ slots }: { slots: CalendarSlotData[] }) {
  if (slots.length === 0) return null;

  // Index slots by day so render-order is Mon→Sun regardless of input order.
  const byDay = new Map<number, CalendarSlotData>();
  for (const s of slots) byDay.set(s.day_idx, s);

  return (
    <section>
      <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        Lịch content tuần
      </p>
      <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
        {slots.length} video đề xuất cho tuần tới
      </h3>
      <div className="grid grid-cols-7 gap-1.5">
        {DAYS_VN.map(({ idx, label }) => {
          const slot = byDay.get(idx);
          return (
            <CalendarCell key={idx} label={label} slot={slot ?? null} />
          );
        })}
      </div>
    </section>
  );
}

function CalendarCell({
  label,
  slot,
}: {
  label: string;
  slot: CalendarSlotData | null;
}) {
  if (!slot) {
    return (
      <div
        className="flex min-h-[96px] flex-col gap-1 rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-2 opacity-60"
        aria-label={`${label} — không có đề xuất`}
      >
        <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">{label}</span>
        <span className="text-[18px] text-[color:var(--gv-ink-4)]">—</span>
      </div>
    );
  }

  const chipClass = KIND_CHIP_CLASS[slot.kind];
  return (
    <div
      className="flex min-h-[96px] flex-col gap-1.5 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2"
      title={slot.rationale}
    >
      <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">{label}</span>
      <span
        className={`inline-flex w-max items-center rounded-full px-1.5 py-0.5 gv-mono text-[9px] font-medium ${chipClass}`}
      >
        {KIND_LABELS[slot.kind]}
      </span>
      <p className="line-clamp-2 text-[11px] font-medium leading-tight text-[color:var(--gv-ink)]">
        {slot.title}
      </p>
      <span className="gv-mono mt-auto text-[10px] text-[color:var(--gv-ink-4)]">
        {slot.suggested_time}
      </span>
    </div>
  );
}
