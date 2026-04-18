import { memo } from "react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { useTopPatterns, type TopPattern } from "@/hooks/useTopPatterns";

/**
 * HooksTable — top 6 patterns in the user's niche, ranked by weekly
 * instance count. Columns: rank / pattern / tăng (weekly delta) / uses
 * (weekly instance count) / tổng (all-time). Matches the design's
 * 6-col Home table.
 *
 * Delta colouring is semantic (pos blue / neg pink); no colour when the
 * pattern is brand new (prev = 0) — "mới" badge instead.
 */

function deltaCell(curr: number, prev: number) {
  if (prev === 0) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-[color:var(--gv-accent-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--gv-accent-deep)]">
        Mới
      </span>
    );
  }
  const deltaPct = Math.round(((curr - prev) / prev) * 100);
  const up = deltaPct >= 0;
  return (
    <span
      className={
        "inline-flex items-center gap-1 text-xs font-semibold " +
        (up ? "text-[color:var(--gv-pos)]" : "text-[color:var(--gv-neg)]")
      }
    >
      <span aria-hidden="true">{up ? "▲" : "▼"}</span>
      {Math.abs(deltaPct)}%
    </span>
  );
}

export const HooksTable = memo(function HooksTable({ nicheId }: { nicheId: number | null }) {
  const { data: patterns, isPending } = useTopPatterns(nicheId, 6);

  if (isPending) {
    return (
      <section className="animate-pulse rounded-[18px] bg-[color:var(--gv-canvas-2)] p-6">
        <div className="h-4 w-32 rounded bg-[color:var(--gv-rule)]" />
        <div className="mt-6 h-48 w-full rounded bg-[color:var(--gv-rule)]" />
      </section>
    );
  }

  if (!patterns || patterns.length === 0) {
    return (
      <section className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
        <SectionHeader
          kicker="BẢNG XẾP HẠNG"
          title="Hook đang chạy trong ngách"
        />
        <p className="mt-6 text-sm text-[color:var(--gv-ink-4)]">
          Chưa đủ pattern để xếp hạng tuần này. Chạy ingest nữa là có.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
      <SectionHeader
        kicker="BẢNG XẾP HẠNG"
        title="Hook đang chạy trong ngách"
        caption="Top pattern trong tuần — xếp theo số video dùng."
      />

      <div className="mt-5 overflow-hidden rounded-[12px] border border-[color:var(--gv-rule)]">
        <table className="w-full text-sm">
          <thead className="bg-[color:var(--gv-canvas-2)]">
            <tr className="text-left">
              <Th className="w-10 text-center">#</Th>
              <Th>PATTERN</Th>
              <Th className="w-20">TĂNG</Th>
              <Th className="w-20 text-right">USES</Th>
              <Th className="w-24 text-right">TỔNG</Th>
            </tr>
          </thead>
          <tbody>
            {patterns.map((p: TopPattern, idx: number) => (
              <tr
                key={p.id}
                className="border-t border-[color:var(--gv-rule-2)] first:border-t-0 hover:bg-[color:var(--gv-canvas-2)]/60"
              >
                <td className="px-3 py-3 text-center gv-mono text-xs text-[color:var(--gv-ink-4)]">
                  {String(idx + 1).padStart(2, "0")}
                </td>
                <td className="px-3 py-3 font-medium text-[color:var(--gv-ink)]">
                  <span className="gv-serif-italic">“{p.display_name || "Pattern"}”</span>
                </td>
                <td className="px-3 py-3">
                  {deltaCell(p.weekly_instance_count, p.weekly_instance_count_prev)}
                </td>
                <td className="px-3 py-3 text-right gv-mono text-[color:var(--gv-ink)]">
                  {p.weekly_instance_count}
                </td>
                <td className="px-3 py-3 text-right gv-mono text-[color:var(--gv-ink-3)]">
                  {p.instance_count.toLocaleString("vi-VN")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
});

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      className={[
        "px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--gv-ink-4)]",
        className ?? "",
      ].filter(Boolean).join(" ")}
    >
      {children}
    </th>
  );
}
