import { motion } from "motion/react";

/** D4 — fade + translateY 12px → 0, 250ms, stagger via parent delay */
export function CreatorCard({
  handle,
  meta,
  index,
}: {
  handle: string;
  meta: string;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.08, ease: "easeOut" }}
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3"
    >
      <p className="font-semibold text-[var(--ink)]">{handle}</p>
      <p className="text-xs text-[var(--muted)]">{meta}</p>
    </motion.div>
  );
}
