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
          className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-alt)] px-3 py-1.5 text-xs text-[color:var(--gv-ink-3)] transition-all duration-[120ms] hover:border-[color:var(--gv-ink)] hover:bg-[color:var(--surface)] hover:text-[color:var(--ink)] active:scale-[0.97] whitespace-nowrap"
        >
          {q}
        </button>
      ))}
    </div>
  );
});
