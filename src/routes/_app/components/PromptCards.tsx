import { memo } from "react";
import { motion } from "motion/react";

export const PromptCards = memo(function PromptCards({
  nicheLabel,
  onSelect,
}: {
  nicheLabel: string;
  onSelect: (prompt: string) => void;
}) {
  const cards = [
    `Xu hướng đang hot trong ${nicheLabel || "ngách của bạn"} tuần này?`,
    "Dán link video TikTok để soi chi tiết",
    "Lên kịch bản quay video mới cho tuần tới",
  ];
  return (
    <div className="mt-4 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-3">
      {cards.map((text, idx) => (
        <motion.button
          key={text}
          type="button"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, delay: 0.05 + idx * 0.05, ease: "easeOut" }}
          onClick={() => onSelect(text)}
          className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-left text-xs leading-snug text-[var(--ink)] transition-all duration-[120ms] hover:border-[var(--border-active)] hover:shadow-sm active:scale-[0.98]"
        >
          {text}
        </motion.button>
      ))}
    </div>
  );
});
