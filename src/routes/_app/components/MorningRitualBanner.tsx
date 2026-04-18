import { memo } from "react";
import { motion } from "motion/react";
import { useDailyRitual, type RitualScript } from "@/hooks/useDailyRitual";

/**
 * Phase A · A2 — rendered above the quick-action cards on ChatScreen's
 * empty state. Validates that the Morning Ritual generator produces useful
 * output before we invest in the A3 Home shell.
 *
 * Each card click submits a pre-formed prompt into the existing chat
 * stream (shot-list intent). Once A3 lands, clicks will route to the
 * `answer` screen instead.
 */

function promptFromScript(script: RitualScript, nicheLabel: string) {
  return (
    `Lên kịch bản cho video TikTok trong ngách ${nicheLabel} theo hướng sau:\n` +
    `Hook: ${script.title_vi}\n` +
    `Loại hook: ${script.hook_type_vi}\n` +
    `Độ dài dự kiến: ${script.length_sec} giây, ${script.shot_count} shot.\n` +
    `Lý do hook chạy: ${script.why_works}\n\n` +
    `Viết kịch bản chi tiết cho mình.`
  );
}

export const MorningRitualBanner = memo(function MorningRitualBanner({
  nicheLabel,
  onSelectPrompt,
}: {
  nicheLabel: string;
  onSelectPrompt: (prompt: string) => void;
}) {
  const { data: ritual, isLoading } = useDailyRitual();

  // Render nothing while loading — the banner is additive, not blocking.
  if (isLoading || !ritual || ritual.scripts.length === 0) return null;

  const isThin = ritual.adequacy === "none" || ritual.adequacy === "reference_pool";

  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="w-full"
      aria-label="Kịch bản sáng nay"
    >
      <div className="mb-2.5 flex items-baseline justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-[var(--faint)]">
          Sáng nay trong ngách của bạn
        </p>
        {isThin ? (
          <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
            dữ liệu thưa
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
        {ritual.scripts.map((script, idx) => (
          <motion.button
            key={`${script.hook_type_en}-${idx}`}
            type="button"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18, delay: 0.08 + idx * 0.04, ease: "easeOut" }}
            onClick={() => onSelectPrompt(promptFromScript(script, nicheLabel))}
            className={
              "group flex flex-col gap-2 rounded-xl border p-3.5 text-left transition-all duration-[120ms] " +
              (idx === 0
                ? "border-[var(--ink)] bg-[var(--ink)] text-[var(--background)] hover:shadow-md"
                : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-active)] hover:shadow-sm")
            }
          >
            <div
              className={
                "flex items-center justify-between text-[10px] uppercase tracking-wider " +
                (idx === 0 ? "text-[var(--background)]/70" : "text-[var(--muted)]")
              }
            >
              <span>{script.hook_type_vi || "hook"}</span>
              <span>
                ~{script.retention_est_pct}% giữ chân
              </span>
            </div>
            <p
              className={
                "text-sm font-semibold italic leading-snug " +
                (idx === 0 ? "text-[var(--background)]" : "text-[var(--ink)]")
              }
            >
              {script.title_vi}
            </p>
            <p
              className={
                "line-clamp-2 text-[11px] leading-snug " +
                (idx === 0 ? "text-[var(--background)]/80" : "text-[var(--muted)]")
              }
            >
              {script.why_works}
            </p>
            <div
              className={
                "mt-1 text-[10px] tracking-wide " +
                (idx === 0 ? "text-[var(--background)]/60" : "text-[var(--faint)]")
              }
            >
              {script.shot_count} shot · {script.length_sec}s
            </div>
          </motion.button>
        ))}
      </div>
    </motion.section>
  );
});
