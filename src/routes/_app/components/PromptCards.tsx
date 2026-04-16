import { memo } from "react";

export const PromptCards = memo(function PromptCards({
  nicheLabel,
  onSelect,
}: {
  nicheLabel: string;
  onSelect: (prompt: string) => void;
}) {
  const cards = [
    `Xu hướng đang hot trong ${nicheLabel || "ngách của bạn"} tuần này?`,
    `Hook nào đang hiệu quả nhất trong ${nicheLabel || "ngách của bạn"} gần đây?`,
    `Gợi ý 3 ý tưởng video cho kênh ${nicheLabel || "của tôi"} tuần tới`,
  ];
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 w-full" style={{ scrollbarWidth: "none" }}>
      {cards.map((text, idx) => (
        <button
          key={idx}
          type="button"
          onClick={() => onSelect(text)}
          className="flex-shrink-0 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs text-[var(--ink)] transition-all duration-[120ms] hover:border-[var(--border-active)] hover:bg-[var(--surface-alt)] active:scale-[0.98] whitespace-nowrap"
        >
          {text}
        </button>
      ))}
    </div>
  );
});
