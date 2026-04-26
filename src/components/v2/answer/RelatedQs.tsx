import { ChevronRight } from "lucide-react";

/** Phase C.1.3 — related questions from report payload (inline, dưới thân báo cáo). */
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

/** Card trong rail phải — khớp mock “CÂU HỎI LIÊN QUAN”. */
export function RelatedQsCard({
  items,
  onPick,
  max = 6,
}: {
  items: string[];
  onPick: (q: string) => void;
  max?: number;
}) {
  const slice = items.slice(0, max);
  if (slice.length === 0) return null;
  return (
    <div className="rounded-lg border border-[var(--gv-rule)] bg-[var(--gv-paper)] p-4">
      <p className="font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">
        Câu hỏi liên quan
      </p>
      <ul className="mt-3 divide-y divide-[var(--gv-rule)]">
        {slice.map((rq) => (
          <li key={rq}>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-2 py-2.5 text-left text-sm text-[var(--gv-ink-2)] transition-colors hover:text-[color:var(--gv-accent)]"
              onClick={() => onPick(rq)}
            >
              <span className="min-w-0">{rq}</span>
              <ChevronRight className="h-4 w-4 shrink-0 text-[var(--gv-ink-4)]" strokeWidth={2} aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
