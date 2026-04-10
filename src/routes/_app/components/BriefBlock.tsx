import { motion } from "motion/react";

/** D3 — sections slide in sequentially */
export function BriefBlock({ sections }: { sections: string[] }) {
  return (
    <div className="space-y-3">
      {sections.map((text, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: i * 0.15, ease: "easeOut" }}
          className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-sm text-[var(--ink)]"
        >
          {text}
        </motion.div>
      ))}
    </div>
  );
}
