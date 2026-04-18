import { memo } from "react";
import { Kicker } from "@/components/v2/Kicker";
import { Bignum } from "@/components/v2/Bignum";
import { Card } from "@/components/v2/Card";
import { useHomePulse } from "@/hooks/useHomePulse";

/**
 * PulseCard — the niche's week in one bignum + 4 supporting stats.
 *
 * - ink-filled hero surface with the big views number
 * - blue/pink delta chip rendered off pos/neg semantics
 * - 2×2 stats grid (videos / creators / viral / hooks)
 * - softens delta+bignum when adequacy is "none" (too thin to claim)
 */

function formatViews(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return m >= 10 ? `${Math.round(m)}M` : `${m.toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return n.toLocaleString("vi-VN");
}

export const PulseCard = memo(function PulseCard() {
  const { data: pulse, isPending } = useHomePulse();

  if (isPending || !pulse) {
    return (
      <Card variant="ink" className="min-h-[240px] animate-pulse p-6">
        {null}
      </Card>
    );
  }

  const isThin = pulse.adequacy === "none";
  const hasPrev = pulse.views_last_week > 0;
  const deltaTone: "pos" | "neg" | "ink" =
    !hasPrev || isThin ? "ink" :
    pulse.views_delta_pct >= 0 ? "pos" : "neg";
  const deltaSign = pulse.views_delta_pct >= 0 ? "▲" : "▼";

  return (
    <Card variant="ink" className="p-6">
      <Kicker tone="pos">NHỊP TUẦN</Kicker>

      <div className="mt-4 flex items-end gap-6">
        <div>
          <p className="text-[11px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
            View tuần này
          </p>
          <Bignum tone="ink" className="mt-1 !text-[color:var(--gv-canvas)]">
            {formatViews(pulse.views_this_week)}
          </Bignum>
        </div>

        {hasPrev && !isThin ? (
          <div
            className={
              "mb-1 inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold " +
              (deltaTone === "pos"
                ? "bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]"
                : "bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg-deep)]")
            }
          >
            <span>{deltaSign}</span>
            <span>{Math.abs(pulse.views_delta_pct).toFixed(1)}%</span>
          </div>
        ) : (
          <div className="mb-1 inline-flex items-center rounded-full bg-[color:var(--gv-ink-2)] px-2 py-1 text-xs text-[color:var(--gv-ink-4)]">
            —
          </div>
        )}
      </div>

      {isThin ? (
        <p className="mt-3 text-xs text-[color:var(--gv-ink-4)]">
          Corpus ngách này đang thưa — tuần tới sẽ chính xác hơn.
        </p>
      ) : null}

      <hr className="my-5 border-[color:var(--gv-ink-2)]" />

      <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
        <Stat label="Video mới" value={pulse.videos_this_week} />
        <Stat label="Creator mới" value={pulse.new_creators_this_week} />
        <Stat label="Viral" value={pulse.viral_count_this_week} />
        <Stat label="Hook mới" value={pulse.new_hooks_this_week} />
      </dl>

      {pulse.top_hook_name ? (
        <p className="mt-5 text-[11px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
          HOOK NỔI BẬT ·{" "}
          <span className="gv-serif-italic text-[color:var(--gv-canvas)] normal-case tracking-normal">
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
      <dt className="text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
        {label}
      </dt>
      <dd className="gv-tight mt-1 text-2xl text-[color:var(--gv-canvas)]">
        {value.toLocaleString("vi-VN")}
      </dd>
    </div>
  );
}
