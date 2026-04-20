/**
 * Phase C.3.2 — StyleCards × 5 grid.
 * Responsive: 5-col desktop (≤1100 → 2-col, ≤720 → 1-col).
 */

type StyleCardRow = {
  id?: string;
  name?: string;
  desc?: string;
  paired_ideas?: string[];
} & Record<string, unknown>;

function StyleCard({ row }: { row: StyleCardRow }) {
  const name = row.name ?? "Style";
  const desc = row.desc ?? "";
  const paired = Array.isArray(row.paired_ideas) ? row.paired_ideas : [];
  return (
    <li className="flex h-full flex-col justify-between border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-[14px] text-[13px] text-[color:var(--gv-ink-2)]">
      <div>
        <p className="gv-serif text-[16px] font-medium text-[color:var(--gv-ink)]">{name}</p>
        {desc ? (
          <p className="mt-1 text-[12px] leading-[1.5] text-[color:var(--gv-ink-3)]">{desc}</p>
        ) : null}
      </div>
      {paired.length > 0 ? (
        <p className="gv-mono mt-3 text-[10px] text-[color:var(--gv-ink-4)]">
          Cho ý tưởng {paired.join(", ")}
        </p>
      ) : null}
    </li>
  );
}

export function StyleCardGrid({ cards }: { cards: StyleCardRow[] }) {
  if (cards.length === 0) return null;
  return (
    <ul className="grid grid-cols-1 gap-2 min-[720px]:grid-cols-2 min-[1100px]:grid-cols-5">
      {cards.map((c, i) => (
        <StyleCard key={c.id ?? String(i)} row={c} />
      ))}
    </ul>
  );
}
