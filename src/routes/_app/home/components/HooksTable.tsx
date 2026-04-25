import { memo } from "react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { useTopPatterns, type TopPattern } from "@/hooks/useTopPatterns";

/**
 * HooksTable — 6-col table matching the design's Home block:
 *   #, MẪU HOOK, TĂNG, LƯỢT DÙNG, VIEW TB, VÍ DỤ
 *
 * VIEW TB + VÍ DỤ come from the top-viewed video_corpus row in each
 * pattern bucket (see useTopPatterns); other fields from video_patterns.
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
        "inline-flex items-center gap-1 gv-mono text-xs font-semibold " +
        (up ? "text-[color:var(--gv-pos)]" : "text-[color:var(--gv-neg)]")
      }
    >
      <span aria-hidden="true">{up ? "▲" : "▼"}</span>
      {up ? "+" : "-"}{Math.abs(deltaPct)}%
    </span>
  );
}

function formatViews(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return m >= 10 ? `${Math.round(m)}M` : `${m.toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toString();
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
    <section className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4 sm:p-6">
      <SectionHeader
        kicker="BẢNG XẾP HẠNG"
        title="Hook đang chạy"
        caption="Top 6 mẫu hook 3 giây với tăng trưởng nhanh nhất tuần qua."
      />

      {/* Mobile: stacked cards. The 6-col table can't fit in 360-393px;
          forcing it would either overflow horizontally (looks broken) or
          collapse the MẪU HOOK column to one-character-per-line. */}
      <ul className="mt-5 space-y-3 sm:hidden">
        {patterns.map((p: TopPattern, idx: number) => (
          <li
            key={p.id}
            className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="gv-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
                  #{String(idx + 1).padStart(2, "0")} · MẪU HOOK
                </div>
                <p className="gv-tight mt-1 text-[15px] font-semibold leading-snug text-[color:var(--gv-ink)]">
                  "{p.display_name || "Pattern"}"
                </p>
              </div>
              <div className="shrink-0">
                {deltaCell(p.weekly_instance_count, p.weekly_instance_count_prev)}
              </div>
            </div>

            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-[color:var(--gv-rule-2)] pt-3">
              <div>
                <dt className="gv-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
                  Lượt dùng
                </dt>
                <dd className="gv-mono mt-0.5 text-sm text-[color:var(--gv-ink)]">
                  {p.weekly_instance_count.toLocaleString("vi-VN")}
                </dd>
              </div>
              <div>
                <dt className="gv-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
                  View TB
                </dt>
                <dd className="gv-mono mt-0.5 text-sm text-[color:var(--gv-ink)]">
                  {formatViews(p.avg_views)}
                </dd>
              </div>
            </dl>

            {p.sample_hook ? (
              <div className="mt-3 border-t border-[color:var(--gv-rule-2)] pt-3">
                <div className="gv-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
                  Ví dụ
                </div>
                <p className="mt-1 text-sm italic leading-snug text-[color:var(--gv-ink-3)]">
                  "{p.sample_hook}"
                </p>
              </div>
            ) : null}
          </li>
        ))}
      </ul>

      {/* Desktop / tablet: table. Horizontally scrollable so wider screens
          that still aren't quite wide enough don't collapse the cells. */}
      <div className="mt-5 hidden overflow-hidden rounded-[12px] border border-[color:var(--gv-rule)] sm:mt-6 sm:block">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="bg-[color:var(--gv-canvas-2)]">
              <tr>
                <Th className="w-[60px] text-center">#</Th>
                <Th>MẪU HOOK</Th>
                <Th className="w-[100px]">TĂNG</Th>
                <Th className="w-[90px] text-right">LƯỢT DÙNG</Th>
                <Th className="w-[100px] text-right">VIEW TB</Th>
                <Th>VÍ DỤ</Th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((p: TopPattern, idx: number) => (
                <tr
                  key={p.id}
                  className="border-t border-[color:var(--gv-rule-2)] first:border-t-0 hover:bg-[color:var(--gv-canvas-2)]/60"
                >
                  <td className="px-3 py-3 text-center gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
                    {String(idx + 1).padStart(2, "0")}
                  </td>
                  <td className="px-3 py-3 gv-tight text-[17px] font-semibold text-[color:var(--gv-ink)]">
                    "{p.display_name || "Pattern"}"
                  </td>
                  <td className="px-3 py-3">
                    {deltaCell(p.weekly_instance_count, p.weekly_instance_count_prev)}
                  </td>
                  <td className="px-3 py-3 text-right gv-mono text-xs text-[color:var(--gv-ink)]">
                    {p.weekly_instance_count.toLocaleString("vi-VN")}
                  </td>
                  <td className="px-3 py-3 text-right gv-mono text-xs text-[color:var(--gv-ink)]">
                    {formatViews(p.avg_views)}
                  </td>
                  <td className="px-3 py-3 text-xs text-[color:var(--gv-ink-3)] italic truncate max-w-[260px]">
                    {p.sample_hook ? `"${p.sample_hook}"` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
});

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      scope="col"
      className={[
        "px-3 py-2 text-left gv-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]",
        className ?? "",
      ].filter(Boolean).join(" ")}
    >
      {children}
    </th>
  );
}
