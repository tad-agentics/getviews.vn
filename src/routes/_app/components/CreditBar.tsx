import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import { Zap } from "lucide-react";

const DEFAULT_CAP = 50;

/** Sidebar credit widget + D5 flash on balance decrease */
export function CreditBar({
  deepCreditsRemaining,
  cap = DEFAULT_CAP,
}: {
  deepCreditsRemaining: number;
  cap?: number;
}) {
  const prev = useRef(deepCreditsRemaining);
  const [flash, setFlash] = useState(false);
  const [ghost, setGhost] = useState(false);

  useEffect(() => {
    const before = prev.current;
    if (deepCreditsRemaining < before) {
      setFlash(true);
      setGhost(true);
      const t = setTimeout(() => setFlash(false), 200);
      const t2 = setTimeout(() => setGhost(false), 400);
      prev.current = deepCreditsRemaining;
      return () => {
        clearTimeout(t);
        clearTimeout(t2);
      };
    }
    prev.current = deepCreditsRemaining;
  }, [deepCreditsRemaining]);

  const pct = Math.round((deepCreditsRemaining / cap) * 100);

  return (
    <motion.div
      animate={
        flash
          ? { boxShadow: "0 0 0 2px var(--purple)" }
          : { boxShadow: "0 0 0 0px transparent" }
      }
      transition={{ duration: 0.2 }}
      className="mx-3 mb-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2.5"
    >
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--faint)]">
          Deep credit
        </span>
        <Link
          to="/app/pricing"
          className="flex items-center gap-0.5 text-[10px] font-semibold text-[var(--purple)] hover:underline"
        >
          <Zap className="h-2.5 w-2.5" strokeWidth={2.5} />
          Nâng cấp
        </Link>
      </div>
      <div className="relative mb-1.5 flex items-baseline gap-1">
        <span className="font-mono text-base font-extrabold text-[var(--ink)]">{deepCreditsRemaining}</span>
        <span className="font-mono text-[10px] text-[var(--muted)]">/ {cap}</span>
        <AnimatePresence>
          {ghost ? (
            <motion.span
              key="minus"
              initial={{ opacity: 1, y: 0 }}
              animate={{ opacity: 0, y: -12 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              className="pointer-events-none absolute left-8 top-0 font-mono text-xs font-bold text-[var(--purple)]"
            >
              −1
            </motion.span>
          ) : null}
        </AnimatePresence>
      </div>
      {deepCreditsRemaining === 0 ? (
        <Link to="/app/pricing" className="mb-1.5 block text-xs font-semibold text-[var(--purple)] hover:underline">
          Hết credit. Mua thêm →
        </Link>
      ) : null}
      <div className="h-1 overflow-hidden rounded-full bg-[var(--border)]">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, background: "var(--gradient-primary)" }}
        />
      </div>
    </motion.div>
  );
}
