import { memo } from "react";

interface FollowUpChipsProps {
  questions: string[];
  onSelect: (q: string) => void;
}

export const FollowUpChips = memo(function FollowUpChips({
  questions,
  onSelect,
}: FollowUpChipsProps) {
  if (!questions.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {questions.map((q, i) => (
        <button
          key={i}
          type="button"
          onClick={() => onSelect(q)}
          className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs text-[var(--ink-soft)] transition-all duration-[120ms] hover:border-[var(--border-active)] hover:bg-[var(--surface)] hover:text-[var(--ink)] active:scale-[0.97] whitespace-nowrap"
        >
          {q}
        </button>
      ))}
    </div>
  );
});
