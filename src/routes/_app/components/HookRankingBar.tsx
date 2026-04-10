import { motion } from "motion/react";

/** D2 — width 0 → target, 400ms cubic-bezier(0.34, 1.56, 0.64, 1) */
export function HookRankingBar({ label, percent }: { label: string; percent: number }) {
  const w = Math.min(100, Math.max(0, percent));
  return (
    <div className="mb-3">
      <div className="mb-1 flex justify-between text-xs font-medium text-[var(--ink)]">
        <span>{label}</span>
        <span className="font-mono text-[var(--muted)]">{w}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[var(--border)]">
        <motion.div
          className="h-full rounded-full"
          style={{ background: "var(--gradient-primary)" }}
          initial={{ width: "0%" }}
          animate={{ width: `${w}%` }}
          transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
        />
      </div>
    </div>
  );
}
