import { memo } from "react";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { useTopPatterns, STUDIO_HOME_TOP_PATTERNS_LIMIT, type TopPattern, type TopPatternsScope } from "@/hooks/useTopPatterns";
import { formatViews } from "@/lib/formatters";
import { pickPatternExample, pickPatternFormula } from "@/lib/patternDisplay";

/**
 * HooksTable — 6-col table matching the design's Home block:
 *   #, MẪU HOOK, TĂNG, LƯỢT DÙNG, VIEW TB, VÍ DỤ
 *
 * VIEW TB + VÍ DỤ come from the top-viewed video_corpus row in each
 * pattern bucket (see useTopPatterns). LƯỢT DÙNG = ``niche_video_count``
 * (video trong ngách gắn pattern); TĂNG vẫn dùng weekly_instance_count
 * toàn corpus (ISSUE-015).
 */

function deltaCell(curr: number, prev: number) {
  if (prev === 0) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-[color:var(--gv-accent-soft)] px-2 py-0.5 text-[11px] font-semibold gv-kicker tracking-wider text-[color:var(--gv-accent-deep)]">
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

export const HooksTable = memo(function HooksTable({
  patternScope,
  embedded = false,
}: {
  patternScope: TopPatternsScope | null;
  embedded?: boolean;
}) {
  const { data: patterns, isPending } = useTopPatterns(patternScope, STUDIO_HOME_TOP_PATTERNS_LIMIT);

  if (isPending) {
    if (embedded) {
      return (
        <div className="animate-pulse rounded-[12px] bg-[color:var(--gv-canvas-2)] p-6">
          <div className="h-48 w-full rounded bg-[color:var(--gv-rule)]" />
        </div>
      );
    }
    return (
      <section className="animate-pulse rounded-[18px] bg-[color:var(--gv-canvas-2)] p-6">
        <div className="h-4 w-32 rounded bg-[color:var(--gv-rule)]" />
        <div className="mt-6 h-48 w-full rounded bg-[color:var(--gv-rule)]" />
      </section>
    );
  }

  if (!patterns || patterns.length === 0) {
    const emptyBody = (
      <p className={`text-sm text-[color:var(--gv-ink-3)] ${embedded ? "" : "mt-6"}`}>
        Chưa có công thức hook nổi bật để xếp hạng tuần này. Bạn hãy quay lại sau nhé.
      </p>
    );
    if (embedded) return emptyBody;
    return (
      <section className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
        <SectionHeader kicker="BẢNG XẾP HẠNG" title="Hook đang chạy trong ngách" />
        {emptyBody}
      </section>
    );
  }

  const listAndTable = (
    <>
      {/* Mobile: stacked cards. The 6-col table can't fit in 360-393px;
          forcing it would either overflow horizontally (looks broken) or
          collapse the MẪU HOOK column to one-character-per-line. */}
      <ul className={`space-y-3 sm:hidden ${embedded ? "mt-0" : "mt-5"}`}>
        {patterns.map((p: TopPattern, idx: number) => {
          const example = pickPatternExample(p);
          return (
          <li
            key={p.id}
            className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="gv-kicker text-[color:var(--gv-ink-4)]">
                  #{String(idx + 1).padStart(2, "0")} · CÔNG THỨC HOOK
                </div>
                <p className="gv-tight mt-1 text-base font-semibold leading-snug text-[color:var(--gv-ink)] line-clamp-3">
                  {pickPatternFormula(p)}
                </p>
              </div>
              <div className="shrink-0">
                {deltaCell(p.weekly_instance_count, p.weekly_instance_count_prev)}
              </div>
            </div>

            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-[color:var(--gv-rule-2)] pt-3">
              <div>
                <dt
                  className="gv-kicker text-[color:var(--gv-ink-4)]"
                  title="Số video trong ngách của bạn gắn công thức hook này."
                >
                  Số video dùng
                </dt>
                <dd
                  className="gv-mono mt-0.5 text-sm text-[color:var(--gv-ink)]"
                  title="Số video trong ngách của bạn gắn công thức hook này."
                >
                  {p.niche_video_count.toLocaleString("vi-VN")}
                </dd>
              </div>
              <div>
                <dt className="gv-kicker text-[color:var(--gv-ink-4)]">
                  View trung bình
                </dt>
                <dd className="gv-mono mt-0.5 text-sm text-[color:var(--gv-ink)]">
                  {p.avg_views == null ? "—" : formatViews(p.avg_views)}
                </dd>
              </div>
            </dl>

            {example ? (
              <div className="mt-3 border-t border-[color:var(--gv-rule-2)] pt-3">
                <div className="gv-kicker text-[color:var(--gv-ink-4)]">
                  Ví dụ
                </div>
                <p className="mt-1 text-sm leading-snug text-[color:var(--gv-ink-3)] line-clamp-3">
                  {example}
                </p>
              </div>
            ) : null}
          </li>
          );
        })}
      </ul>

      {/* Desktop / tablet: table. Horizontally scrollable so wider screens
          that still aren't quite wide enough don't collapse the cells. */}
      <div
        className={`hidden overflow-hidden rounded-[12px] border border-[color:var(--gv-rule)] sm:block ${embedded ? "mt-0 sm:mt-0" : "mt-5 sm:mt-6"}`}
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead className="bg-[color:var(--gv-canvas-2)]">
              <tr>
                <Th className="w-[52px] text-center">#</Th>
                <Th className="min-w-[200px]">CÔNG THỨC HOOK</Th>
                <Th
                  className="w-[92px] text-center"
                  hint="So sánh lượt gắn công thức này trên toàn hệ thống giữa 7 ngày vừa rồi và 7 ngày trước. «Mới» = tuần trước chưa có dữ liệu so sánh."
                >
                  TĂNG TRƯỞNG
                </Th>
                <Th
                  className="w-[88px] text-right"
                  hint="Số video trong ngách của bạn đã sử dụng công thức hook này. Khác với cột Tăng trưởng — đó là số liệu toàn hệ thống theo tuần."
                >
                  SỐ VIDEO DÙNG
                </Th>
                <Th className="w-[88px] text-right">VIEW TRUNG BÌNH</Th>
                <Th className="min-w-[180px]">VÍ DỤ THỰC TẾ</Th>
              </tr>
            </thead>
            <tbody>
              {patterns.map((p: TopPattern, idx: number) => (
                <tr
                  key={p.id}
                  className="border-t border-[color:var(--gv-rule-2)] first:border-t-0 hover:bg-[color:var(--gv-canvas-2)]/60"
                >
                  <td className="px-3 py-3 text-center">
                    <span className="gv-kicker text-[color:var(--gv-ink-4)]">
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                  </td>
                  <td className="px-3 py-3 font-semibold leading-snug text-[color:var(--gv-ink)]">
                    <span className="line-clamp-2">{pickPatternFormula(p)}</span>
                  </td>
                  <td className="px-3 py-3 text-center">
                    {deltaCell(p.weekly_instance_count, p.weekly_instance_count_prev)}
                  </td>
                  <td
                    className="px-3 py-3 text-right gv-mono text-xs text-[color:var(--gv-ink)]"
                  title="Số video trong ngách của bạn gắn công thức hook này."
                >
                  {p.niche_video_count.toLocaleString("vi-VN")}
                </td>
                  <td className="px-3 py-3 text-right gv-mono text-xs text-[color:var(--gv-ink)]">
                    {p.avg_views == null ? "—" : formatViews(p.avg_views)}
                  </td>
                  <td className="px-3 py-3 text-xs leading-snug text-[color:var(--gv-ink-3)]">
                    <span className="line-clamp-2">
                      {pickPatternExample(p) ?? "—"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );

  if (embedded) {
    return listAndTable;
  }

  return (
    <section className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4 sm:p-6">
      <SectionHeader
        kicker="BẢNG XẾP HẠNG"
        title="Hook đang chạy"
        caption={`Top ${patterns.length} công thức hook 3 giây có tỷ lệ tăng trưởng cao nhất tuần qua. «Số video dùng» thống kê trong ngách của bạn; «Tăng trưởng» đo lường trên toàn hệ thống 7 ngày.`}
      />
      {listAndTable}
    </section>
  );
});

function Th({
  children,
  className,
  hint,
}: {
  children: React.ReactNode;
  className?: string;
  /** Native tooltip — giải thích cột (ISSUE-015). */
  hint?: string;
}) {
  return (
    <th
      scope="col"
      title={hint}
      className={["px-3 py-2.5 align-middle", className ?? ""].filter(Boolean).join(" ")}
    >
      <span className="gv-kicker whitespace-nowrap text-[color:var(--gv-ink-4)]">
        {children}
      </span>
    </th>
  );
}
