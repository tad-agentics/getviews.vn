import { motion } from "motion/react";

export type DiagnosisRowData = {
  type: string;
  finding: string;
  benchmark?: string;
  fix?: string;
};

/** D1 — stagger from left, 150ms each, 100ms stagger (DiagnosisReveal) */
export function DiagnosisRow({ row, index }: { row: DiagnosisRowData; index: number }) {
  const isFirstFail = index === 0 && row.type === "fail";
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.15, delay: index * 0.1, ease: "easeOut" }}
      className={`flex gap-3 py-3 ${isFirstFail ? "border-l-2 border-[var(--purple)] pl-3" : ""}`}
    >
      <div className="mt-0.5 flex-shrink-0">
        {row.type === "fail" ? (
          <span className="font-bold text-[var(--danger)]">✕</span>
        ) : (
          <span className="font-bold text-[var(--success)]">✓</span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="mb-1 font-medium text-[var(--ink)]">{row.finding}</p>
        {row.benchmark ? <p className="mb-1 text-sm text-[var(--ink-soft)]">{row.benchmark}</p> : null}
        {row.fix ? (
          <p className="text-sm text-[var(--ink)]">
            <span className="font-medium">Fix:</span> {row.fix}
          </p>
        ) : null}
      </div>
    </motion.div>
  );
}
