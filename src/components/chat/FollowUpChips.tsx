interface FollowUpChipsProps {
  chips: string[];
  onSelect: (chip: string) => void;
}

export function FollowUpChips({ chips, onSelect }: FollowUpChipsProps) {
  if (!chips.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {chips.map((chip, i) => (
        <button
          key={i}
          type="button"
          onClick={() => onSelect(chip)}
          className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1 text-xs text-[var(--ink)] transition-colors hover:bg-[var(--surface)]"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
