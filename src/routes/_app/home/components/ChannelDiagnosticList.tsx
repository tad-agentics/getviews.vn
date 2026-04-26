import { memo } from "react";
import type { ChannelDiagnosticItem } from "@/lib/api-types";

/**
 * Studio Home — Strengths / Weaknesses diagnostic list (PR-2).
 *
 * Mirrors the design pack's MyChannelCard §C / §D blocks: a card per
 * item, accent-soft fill, ink-left rule, title + colored metric line,
 * then a 2-column "VÌ SAO / TẬN DỤNG (or CÁCH SỬA)" body grid.
 *
 * The optional ``bridge_to`` ("01" or "02") renders a small mono pill
 * on the right that scrolls to a ``data-tier`` anchor on
 * ``HomeSuggestionsToday`` when clicked. The actual scroll wiring (and
 * the data-tier attributes) ship in PR-4 — until then this component
 * forwards the click via ``onBridgeClick`` so callers can no-op.
 *
 * Source of truth:
 * ``cloud-run/getviews_pipeline/channel_analyze.py::ChannelStrengthLLM``
 * + ``ChannelWeaknessLLM``.
 */

export type DiagnosticKind = "strength" | "weakness";

const KIND_STYLES: Record<DiagnosticKind, {
  symbol: string;
  fill: string;
  rule: string;
  metric: string;
  actionLabel: string;
}> = {
  strength: {
    symbol: "▲",
    fill: "bg-[color:var(--gv-pos-soft)]",
    rule: "border-[color:var(--gv-pos)]",
    metric: "text-[color:var(--gv-pos-deep)]",
    actionLabel: "TẬN DỤNG",
  },
  weakness: {
    symbol: "✕",
    fill: "bg-[color:var(--gv-neg-soft)]",
    rule: "border-[color:var(--gv-neg)]",
    metric: "text-[color:var(--gv-neg-deep)]",
    actionLabel: "CÁCH SỬA",
  },
};

export type ChannelDiagnosticListProps = {
  kind: DiagnosticKind;
  items: ReadonlyArray<ChannelDiagnosticItem>;
  /**
   * Called when the bridge pill is clicked. PR-2 doesn't wire scrolling
   * yet; PR-4 will replace this with a default scroll-to-anchor handler.
   */
  onBridgeClick?: (tier: "01" | "02") => void;
};

export const ChannelDiagnosticList = memo(function ChannelDiagnosticList({
  kind,
  items,
  onBridgeClick,
}: ChannelDiagnosticListProps) {
  if (items.length === 0) return null;
  const style = KIND_STYLES[kind];
  return (
    <ul aria-label={kind === "strength" ? "Điểm mạnh" : "Điểm yếu"} className="flex flex-col gap-3.5">
      {items.map((item, idx) => (
        <li
          key={`${item.title}-${idx}`}
          className={`rounded-md border-l-2 ${style.rule} ${style.fill} px-4 py-3.5`}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-baseline gap-2">
              <span
                className={`shrink-0 text-[11px] font-bold leading-tight ${style.metric}`}
                aria-hidden
              >
                {style.symbol}
              </span>
              <div className="min-w-0">
                <p className="m-0 text-[14.5px] font-semibold leading-snug tracking-[-0.01em] text-[color:var(--gv-ink)]">
                  {item.title}
                </p>
                {item.metric ? (
                  <p className={`gv-mono mt-0.5 text-[11px] font-semibold ${style.metric}`}>
                    {item.metric}
                  </p>
                ) : null}
              </div>
            </div>
            {item.bridge_to ? (
              <button
                type="button"
                className="gv-mono shrink-0 rounded-[3px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-1 text-[9px] font-bold uppercase tracking-[0.08em] text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink)]"
                onClick={() => onBridgeClick?.(item.bridge_to as "01" | "02")}
              >
                → {item.bridge_to}
              </button>
            ) : null}
          </div>
          <div className="mt-2 grid grid-cols-[60px_1fr] gap-x-2.5 gap-y-1.5">
            <span className="gv-mono pt-0.5 text-[9px] font-bold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
              VÌ SAO
            </span>
            <p className="m-0 text-[12.5px] leading-snug text-[color:var(--gv-ink-2)]" style={{ textWrap: "pretty" }}>
              {item.why}
            </p>
            <span className="gv-mono pt-0.5 text-[9px] font-bold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
              {style.actionLabel}
            </span>
            <p className="m-0 text-[12.5px] leading-snug text-[color:var(--gv-ink-2)]" style={{ textWrap: "pretty" }}>
              {item.action}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
});
