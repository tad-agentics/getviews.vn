import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

/** D6 — fade in 120ms → 2s visible → fade out 200ms */
export function FreeQueryPill({ pulseKey }: { pulseKey: number }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!pulseKey) return;
    setVisible(true);
    const hide = setTimeout(() => setVisible(false), 2320);
    return () => clearTimeout(hide);
  }, [pulseKey]);

  return (
    <AnimatePresence>
      {visible ? (
        <motion.span
          key={pulseKey}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { duration: 0.12 } }}
          exit={{ opacity: 0, transition: { duration: 0.2 } }}
          className="ml-2 inline-flex rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[10px] font-semibold text-[var(--muted)]"
        >
          Miễn phí ✓
        </motion.span>
      ) : null}
    </AnimatePresence>
  );
}
