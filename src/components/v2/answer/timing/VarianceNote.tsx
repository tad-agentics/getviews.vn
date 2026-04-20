/**
 * Phase C.4.3 — Timing VarianceNote chip (plan §2.3 section 5 — NEW).
 *
 * Three states keyed to `variance_note.kind`:
 *   - strong  → accent chip ("Heatmap CÓ ý nghĩa")
 *   - weak    → ink-3 chip  ("Heatmap có xu hướng nhưng chưa rõ")
 *   - sparse  → canvas-2 chip ("Heatmap CHƯA ổn định — mẫu thưa")
 *
 * The chip doubles as the expand affordance for the longer `detail` copy
 * rendered below it so the band stays scannable.
 */

import type { TimingReportPayload } from "@/lib/api-types";

type VarianceKind = "strong" | "weak" | "sparse";

export function VarianceNote({ note }: { note: TimingReportPayload["variance_note"] }) {
  const kind = ((note.kind as string) ?? "sparse") as VarianceKind;
  const label = (note.label as string) ?? "";
  const detail = (note.detail as string) ?? "";

  const chipCls =
    kind === "strong"
      ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)] border-[color:var(--gv-accent)]"
      : kind === "weak"
        ? "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-2)] border-[color:var(--gv-rule)]"
        : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)] border-[color:var(--gv-rule)]";

  return (
    <section className="flex flex-col gap-2">
      <span
        className={`gv-mono inline-flex w-fit rounded border px-2 py-[2px] text-[11px] uppercase tracking-wide ${chipCls}`}
      >
        {label}
      </span>
      {detail ? (
        <p className="text-[12px] leading-[1.5] text-[color:var(--gv-ink-3)]">{detail}</p>
      ) : null}
    </section>
  );
}
