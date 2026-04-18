import { memo } from "react";
import { Kicker } from "@/components/v2/Kicker";
import { Bignum } from "@/components/v2/Bignum";
import { Card } from "@/components/v2/Card";
import { useHomePulse } from "@/hooks/useHomePulse";

/**
 * PulseCard — UIUX reference: paper `.card`, padding 22px, column gap 18px,
 * mono kicker 9px ink-4, bignum in ink on light ground, pos-deep delta, rule separator.
 */

function formatViews(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return m >= 10 ? `${Math.round(m)}M` : `${m.toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toLocaleString("vi-VN");
}

export const PulseCard = memo(function PulseCard({
  omitKicker = false,
}: {
  omitKicker?: boolean;
} = {}) {
  const { data: pulse, isPending } = useHomePulse();

  if (isPending || !pulse) {
    return (
      <Card variant="paper" className="min-h-[240px] animate-pulse p-[22px]">
        {null}
      </Card>
    );
  }

  const isThin = pulse.adequacy === "none";
  const hasPrev = pulse.views_last_week > 0;
  const deltaTone: "pos" | "neg" | "ink" =
    !hasPrev || isThin ? "ink" : pulse.views_delta_pct >= 0 ? "pos" : "neg";
  const deltaSign = pulse.views_delta_pct >= 0 ? "▲" : "▼";

  return (
    <Card variant="paper" className="flex flex-col gap-[18px] p-[22px] text-[color:var(--gv-ink)]">
      {omitKicker ? null : <Kicker tone="muted">NHỊP TUẦN</Kicker>}

      <div className="flex flex-wrap items-end gap-2.5">
        <div className="min-w-0">
          <p className="gv-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
            View tuần này
          </p>
          <Bignum tone="ink" className="mt-1.5 !text-[color:var(--gv-ink)]">
            {formatViews(pulse.views_this_week)}
          </Bignum>
        </div>

        {hasPrev && !isThin ? (
          <div
            className={
              "mb-0.5 inline-flex items-center gap-1 rounded-full px-2 py-1 text-[13px] font-semibold " +
              (deltaTone === "pos"
                ? "text-[color:var(--gv-pos-deep)]"
                : "text-[color:var(--gv-neg-deep)]")
            }
          >
            <span>{deltaSign}</span>
            <span>{Math.abs(pulse.views_delta_pct).toFixed(1)}%</span>
          </div>
        ) : (
          <div className="mb-0.5 inline-flex items-center rounded-full bg-[color:var(--gv-canvas-2)] px-2 py-1 text-xs text-[color:var(--gv-ink-4)]">
            —
          </div>
        )}
      </div>

      {isThin ? (
        <p className="text-xs leading-snug text-[color:var(--gv-ink-3)]">
          Corpus ngách này đang thưa — tuần tới sẽ chính xác hơn.
        </p>
      ) : null}

      <hr className="m-0 border-0 border-t border-[color:var(--gv-rule)]" />

      <dl className="grid grid-cols-2 gap-x-3.5 gap-y-3.5">
        <Stat label="Video mới" value={pulse.videos_this_week} />
        <Stat label="Creator mới" value={pulse.new_creators_this_week} />
        <Stat label="Viral" value={pulse.viral_count_this_week} />
        <Stat label="Hook mới" value={pulse.new_hooks_this_week} />
      </dl>

      {pulse.top_hook_name ? (
        <p className="gv-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          Hook nổi bật ·{" "}
          <span className="gv-serif-italic text-[13px] font-medium normal-case tracking-normal text-[color:var(--gv-ink-2)]">
            “{pulse.top_hook_name}”
          </span>
        </p>
      ) : null}
    </Card>
  );
});

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="gv-mono text-[9px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
        {label}
      </dt>
      <dd className="gv-tight mt-0.5 text-[26px] leading-[1.1] text-[color:var(--gv-ink)]">
        {value.toLocaleString("vi-VN")}
      </dd>
    </div>
  );
}
