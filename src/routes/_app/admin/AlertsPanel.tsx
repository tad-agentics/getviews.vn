/**
 * Phase D.6.10 — Admin alerts panel.
 *
 * Pairs with the Cloud Run cron-triggered `POST /admin/evaluate-alerts`
 * which writes `admin_alert_fires` rows on threshold crossings. This
 * panel surfaces the most recent 20 fires + clears so an operator can
 * glance at "is anything broken right now" without opening Slack.
 *
 * A fire (severity=crit) in phase=firing renders with the danger token
 * tone; cleared rows dim to ink-4. Most-recent row per rule_key sits
 * at the top (the cron writes rows in chronological order so newest =
 * most relevant).
 */
import { useMemo } from "react";
import { useAdminAlertFires, type AlertFire } from "@/hooks/useAdminAlerts";

function severityToneClass(severity: string, phase: string): string {
  if (phase === "cleared") return "text-[color:var(--gv-ink-4)]";
  if (severity === "crit") return "text-[color:var(--gv-danger)]";
  if (severity === "warn") return "text-[color:var(--gv-warn)]";
  return "text-[color:var(--gv-ink-3)]";
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const sec = Math.round((Date.now() - then) / 1000);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.round(sec / 60)}m`;
  if (sec < 86400) return `${Math.round(sec / 3600)}h`;
  return `${Math.round(sec / 86400)}d`;
}

function PhaseChip({ phase }: { phase: "firing" | "cleared" }) {
  const firing = phase === "firing";
  return (
    <span
      className={
        "inline-flex items-center rounded-full px-2 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] " +
        (firing
          ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-danger)]"
          : "bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]")
      }
    >
      {firing ? "firing" : "cleared"}
    </span>
  );
}

function FireRow({ fire, current }: { fire: AlertFire; current: boolean }) {
  const tone = severityToneClass(fire.severity, fire.phase);
  return (
    <li className="flex items-start gap-3 border-b border-[color:var(--gv-rule)] py-2.5 last:border-0">
      <span className="w-[60px] shrink-0 gv-mono text-[11px] text-[color:var(--gv-ink-4)]" title={fire.created_at}>
        {relativeTime(fire.created_at)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`gv-mono text-[11px] font-semibold uppercase tracking-[0.08em] ${tone}`}>
            {fire.severity}
          </span>
          <span className="gv-mono text-[11px] text-[color:var(--gv-ink)]">{fire.rule_key}</span>
          <PhaseChip phase={fire.phase} />
          {current ? (
            <span className="gv-mono text-[10px] uppercase tracking-[0.08em] text-[color:var(--gv-accent-deep)]">
              current
            </span>
          ) : null}
        </div>
        <p className={`mt-1 text-[12px] leading-relaxed ${tone}`}>{fire.message}</p>
      </div>
    </li>
  );
}

export function AlertsPanel() {
  const q = useAdminAlertFires(20);

  // Each rule_key's newest row == current state. Tag those so the UI
  // highlights "which rules are firing right now" vs historical noise.
  const currentByRule = useMemo(() => {
    const out = new Set<string>();
    const seen = new Set<string>();
    for (const f of q.data?.fires ?? []) {
      if (!seen.has(f.rule_key)) {
        seen.add(f.rule_key);
        if (f.phase === "firing") out.add(f.id);
      }
    }
    return out;
  }, [q.data]);

  const firingNow = useMemo(
    () => (q.data?.fires ?? []).filter((f) => currentByRule.has(f.id)),
    [q.data, currentByRule],
  );

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải alerts"
        className="h-32 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const msg = q.error instanceof Error ? q.error.message : "unknown";
    return (
      <p className="text-[13px] text-[color:var(--gv-danger)]">
        Không tải được alerts ({msg}).
      </p>
    );
  }
  if (!q.data) return null;

  const fires = q.data.fires;

  if (fires.length === 0) {
    return (
      <p className="gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
        Chưa có alert nào fire — chờ cron-evaluator đánh giá lần đầu, hoặc mọi rule đều đang pass.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {firingNow.length > 0 ? (
        <div className="flex items-center gap-2 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-accent-soft)] bg-[color:var(--gv-accent-soft)] px-3 py-2">
          <span className="gv-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-danger)]">
            {firingNow.length} firing now
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-pos-soft)] px-3 py-2">
          <span className="gv-mono text-[11px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-pos-deep)]">
            Hệ thống ok — không có rule nào đang fire
          </span>
        </div>
      )}
      <ul className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3">
        {fires.map((f) => (
          <FireRow key={f.id} fire={f} current={currentByRule.has(f.id)} />
        ))}
      </ul>
    </div>
  );
}
