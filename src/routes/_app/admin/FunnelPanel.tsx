import { useMemo, useState } from "react";

import { useAdminFunnel, type AdminFunnelResponse } from "@/hooks/useAdminFunnel";

/**
 * L2.2 Sprint 6a — measurement panel for the creator-views-uplift loop.
 *
 * The L2.2 sprints (1-5) shipped a chain of features instrumented with
 * ``logUsage``: ritual_view → script_clicked → evidence_expanded →
 * thumb_clicked, plus the Trends Pattern card. Without a way to read
 * those events we can't tell if the loop is moving views.
 *
 * This panel reads ``/admin/funnel`` (existing endpoint, service-role
 * aggregate over ``usage_events``) and slices the response into:
 *
 *   1. The L2.2 hot-path funnel — ritual_view → click → script_save.
 *   2. Enrichment uptake — what fraction of clicks expand evidence /
 *      explore the Pattern surface, signaling deep engagement.
 *   3. A "watchlist" of the L2.2 events with their per-window count
 *      and unique-user count.
 *   4. A daily-trend strip for the top actions.
 *
 * Everything is computed off the BE ``totals`` map — the BE already
 * does the SQL aggregation. We just project it through the L2.2 lens.
 */

const WINDOW_OPTIONS = [
  { days: 7, label: "7 ngày" },
  { days: 14, label: "14 ngày" },
  { days: 30, label: "30 ngày" },
] as const;

/** Events the L2.2 loop fires. Order matters — used to render the
 *  watchlist top-down in narrative order from "discovery" to "act". */
const L22_EVENTS: ReadonlyArray<{ action: string; label: string; group: "ritual" | "evidence" | "pattern" | "act" }> = [
  { action: "daily_ritual_script_clicked",        label: "Ritual · click vào script",        group: "ritual" },
  { action: "daily_ritual_evidence_expanded",     label: "Ritual · mở rộng evidence strip",  group: "evidence" },
  { action: "daily_ritual_evidence_thumb_clicked", label: "Ritual · click vào thumb evidence", group: "evidence" },
  { action: "pattern_card_clicked",               label: "Trends · click pattern card",      group: "pattern" },
  { action: "script_screen_load",                 label: "Studio · legacy /app/script redirect", group: "act" },
  { action: "script_generate",                    label: "Studio · script_generate",          group: "act" },
  { action: "script_save",                        label: "Studio · script_save",              group: "act" },
];

export function FunnelPanel() {
  const [days, setDays] = useState<number>(7);
  const { data, isPending, isError, error } = useAdminFunnel(days);

  if (isPending) {
    return (
      <div
        role="status"
        aria-label="Đang tải funnel"
        className="h-[280px] animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (isError) {
    return (
      <div className="rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-sm text-[color:var(--gv-ink-3)]">
        Không tải được funnel — {(error as Error)?.message ?? "lỗi không rõ"}.
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="flex flex-col gap-6">
      <WindowToggle days={days} onChange={setDays} />
      <HotPathFunnel data={data} />
      <EnrichmentUptake data={data} />
      <L22Watchlist data={data} />
      <DailyTrend data={data} />
    </div>
  );
}

// ── Window toggle ─────────────────────────────────────────────────────────


function WindowToggle({
  days,
  onChange,
}: {
  days: number;
  onChange: (next: number) => void;
}) {
  return (
    <div className="flex items-center gap-2" role="tablist" aria-label="Cửa sổ thời gian">
      {WINDOW_OPTIONS.map((opt) => {
        const active = opt.days === days;
        return (
          <button
            key={opt.days}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.days)}
            className={
              "gv-mono rounded-[3px] px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.08em] transition-colors " +
              (active
                ? "bg-[color:var(--gv-ink)] text-white"
                : "border border-[color:var(--gv-rule)] text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-canvas-2)]")
            }
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

// ── L2.2 hot-path funnel ──────────────────────────────────────────────────


/** Steps of the daily-ritual hot path. Each step has a denominator
 *  (the prior step's count) so the bar widths read as conversion. */
const HOT_PATH = [
  { action: "answer_session_create",      label: "Sessions opened (proxy for active days)" },
  { action: "daily_ritual_script_clicked", label: "Ritual click → script studio" },
  { action: "script_generate",             label: "Script generated" },
  { action: "script_save",                 label: "Script saved" },
] as const;


function HotPathFunnel({ data }: { data: AdminFunnelResponse }) {
  const counts = HOT_PATH.map((step) => ({
    ...step,
    count: data.totals[step.action] ?? 0,
    uniques: data.unique_users[step.action] ?? 0,
  }));
  const head = counts[0]?.count ?? 0;

  return (
    <div>
      <h3 className="gv-mono mb-3 text-[11px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        L2.2 hot path · ngày → click → save
      </h3>
      {head === 0 ? (
        <p className="rounded-md border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-4 text-xs text-[color:var(--gv-ink-3)]">
          Chưa có session nào trong cửa sổ — funnel sẽ hiện sau khi creator dùng app.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {counts.map((step, i) => {
            const denom = i === 0 ? head : counts[0]!.count;
            const prevDenom = i === 0 ? head : counts[i - 1]!.count;
            const pctOfTop = denom > 0 ? Math.round((step.count / denom) * 100) : 0;
            const pctOfPrev = prevDenom > 0 ? Math.round((step.count / prevDenom) * 100) : null;
            return (
              <li
                key={step.action}
                className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm font-medium text-[color:var(--gv-ink)]">
                    {step.label}
                  </span>
                  <span className="gv-mono whitespace-nowrap text-xs tabular-nums text-[color:var(--gv-ink-3)]">
                    {step.count.toLocaleString("vi-VN")} · {step.uniques} người
                  </span>
                </div>
                <div className="mt-2 h-[6px] overflow-hidden rounded-full bg-[color:var(--gv-rule-2,var(--gv-rule))]">
                  <div
                    className="h-full"
                    style={{
                      width: `${pctOfTop}%`,
                      background: "var(--gv-accent)",
                    }}
                  />
                </div>
                {i > 0 && pctOfPrev != null ? (
                  <p className="gv-mono mt-1.5 text-[11px] text-[color:var(--gv-ink-3)]">
                    {pctOfPrev}% chuyển đổi từ bước trước
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ── Enrichment uptake ─────────────────────────────────────────────────────


function EnrichmentUptake({ data }: { data: AdminFunnelResponse }) {
  const ritualClicks = data.totals["daily_ritual_script_clicked"] ?? 0;
  const evidenceExpanded = data.totals["daily_ritual_evidence_expanded"] ?? 0;
  const thumbClicked = data.totals["daily_ritual_evidence_thumb_clicked"] ?? 0;
  const patternClicked = data.totals["pattern_card_clicked"] ?? 0;

  const cards = [
    {
      label: "% click ritual mở evidence",
      sub: "expanded / clicked",
      pct: pct(evidenceExpanded, ritualClicks),
      detail: `${evidenceExpanded.toLocaleString("vi-VN")} / ${ritualClicks.toLocaleString("vi-VN")}`,
    },
    {
      label: "% expand → click thumb",
      sub: "thumb / expanded",
      pct: pct(thumbClicked, evidenceExpanded),
      detail: `${thumbClicked.toLocaleString("vi-VN")} / ${evidenceExpanded.toLocaleString("vi-VN")}`,
    },
    {
      label: "Trends Pattern · click rate",
      sub: "pattern_card_clicked",
      // No clean denominator — surface the absolute count + unique users.
      pct: null,
      detail: `${patternClicked.toLocaleString("vi-VN")} click · ${data.unique_users["pattern_card_clicked"] ?? 0} người`,
    },
  ];

  return (
    <div>
      <h3 className="gv-mono mb-3 text-[11px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        Enrichment uptake — ai dùng các phần thêm sau Sprint 1-5
      </h3>
      <div
        className="grid gap-2.5"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}
      >
        {cards.map((c) => (
          <div
            key={c.label}
            className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3"
          >
            <p className="gv-mono mb-1.5 text-[11px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-3)]">
              {c.sub}
            </p>
            <p className="m-0 mb-1 text-sm font-medium leading-tight text-[color:var(--gv-ink)]">
              {c.label}
            </p>
            <p className="gv-bignum tabular-nums text-[color:var(--gv-ink)]">
              {c.pct != null ? `${c.pct}%` : "—"}
            </p>
            <p className="gv-mono mt-1 text-[11px] tabular-nums text-[color:var(--gv-ink-3)]">
              {c.detail}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function pct(numer: number, denom: number): number | null {
  if (denom <= 0) return null;
  return Math.round((numer / denom) * 100);
}

// ── L2.2 watchlist ────────────────────────────────────────────────────────


function L22Watchlist({ data }: { data: AdminFunnelResponse }) {
  const rows = useMemo(
    () =>
      L22_EVENTS.map((e) => ({
        ...e,
        count: data.totals[e.action] ?? 0,
        uniques: data.unique_users[e.action] ?? 0,
      })),
    [data],
  );

  return (
    <div>
      <h3 className="gv-mono mb-3 text-[11px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        L2.2 events · counts trong cửa sổ
      </h3>
      <div className="overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[color:var(--gv-rule)] text-left text-[color:var(--gv-ink-4)]">
              <th className="gv-mono px-4 py-2 text-[11px] font-semibold gv-kicker tracking-[0.08em]">Event</th>
              <th className="gv-mono px-4 py-2 text-right text-[11px] font-semibold gv-kicker tracking-[0.08em]">Count</th>
              <th className="gv-mono px-4 py-2 text-right text-[11px] font-semibold gv-kicker tracking-[0.08em]">Unique users</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr
                key={r.action}
                className={
                  "tabular-nums " +
                  (i === 0 ? "" : "border-t border-[color:var(--gv-rule)] ")
                }
              >
                <td className="px-4 py-2.5">
                  <span className="text-[color:var(--gv-ink)]">{r.label}</span>
                  <span className="gv-mono ml-2 text-[11px] text-[color:var(--gv-ink-4)]">
                    {r.action}
                  </span>
                </td>
                <td className="gv-mono px-4 py-2.5 text-right text-[12px] text-[color:var(--gv-ink)]">
                  {r.count.toLocaleString("vi-VN")}
                </td>
                <td className="gv-mono px-4 py-2.5 text-right text-[12px] text-[color:var(--gv-ink-3)]">
                  {r.uniques.toLocaleString("vi-VN")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Daily trend (top actions × days) ───────────────────────────────────────


function DailyTrend({ data }: { data: AdminFunnelResponse }) {
  // Normalise to a sorted list of days so all rows share the same x-axis.
  const days = useMemo(() => {
    const set = new Set<string>();
    for (const buckets of Object.values(data.daily_top_actions)) {
      for (const day of Object.keys(buckets)) set.add(day);
    }
    return [...set].sort();
  }, [data]);

  const actions = Object.keys(data.daily_top_actions);

  if (actions.length === 0) {
    return null;
  }

  return (
    <div>
      <h3 className="gv-mono mb-3 text-[11px] font-semibold gv-kicker tracking-[0.08em] text-[color:var(--gv-ink-4)]">
        Top actions · daily count
      </h3>
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="border-b border-[color:var(--gv-rule)] text-left text-[color:var(--gv-ink-4)]">
              <th className="gv-mono whitespace-nowrap px-3 py-2 text-[11px] font-semibold gv-kicker tracking-[0.08em]">
                Action
              </th>
              {days.map((d) => (
                <th
                  key={d}
                  className="gv-mono whitespace-nowrap px-3 py-2 text-right text-[11px] font-semibold gv-kicker tracking-[0.08em]"
                >
                  {d.slice(5)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {actions.map((action) => {
              const buckets = data.daily_top_actions[action] ?? {};
              return (
                <tr key={action} className="border-t border-[color:var(--gv-rule)] tabular-nums">
                  <td className="gv-mono whitespace-nowrap px-3 py-2 text-[11px] text-[color:var(--gv-ink)]">
                    {action}
                  </td>
                  {days.map((d) => (
                    <td
                      key={d}
                      className="gv-mono whitespace-nowrap px-3 py-2 text-right text-[11px] text-[color:var(--gv-ink-3)]"
                    >
                      {(buckets[d] ?? 0).toLocaleString("vi-VN")}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
