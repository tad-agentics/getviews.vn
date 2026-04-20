/** Phase C.1.3 — related questions from report payload. */
export function RelatedQs({
  items,
  onPick,
  max = 5,
}: {
  items: string[];
  onPick: (q: string) => void;
  max?: number;
}) {
  const slice = items.slice(0, max);
  if (slice.length === 0) return null;
  return (
    <div className="mt-8">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">
        Câu hỏi liên quan
      </p>
      <ul className="flex flex-col gap-1 border-t border-[var(--gv-rule)]">
        {slice.map((rq) => (
          <li key={rq} className="border-b border-[var(--gv-rule)] py-2 last:border-b-0">
            <button
              type="button"
              className="w-full text-left text-sm text-[var(--gv-ink-2)] transition-colors hover:text-[color:var(--gv-accent)]"
              onClick={() => onPick(rq)}
            >
              {rq}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
