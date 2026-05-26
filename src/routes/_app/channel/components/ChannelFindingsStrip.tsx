import type { ChannelDiagnosisFinding } from "@/lib/api-types";

const STRENGTH_LABEL: Record<string, string> = {
  high: "Mạnh",
  medium: "Vừa",
  low: "Nhẹ",
};

/** Deep diagnosis — evidence-backed findings tile (§5.1 / V5 §2). */
export function ChannelFindingsStrip({ findings }: { findings: ChannelDiagnosisFinding[] }) {
  if (findings.length === 0) return null;

  return (
    <div
      className="mb-5 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-4"
      aria-label="Nhận định kênh từ dữ liệu"
    >
      <p className="gv-kicker mb-3 text-[color:var(--gv-ink-3)]">Nhận định từ dữ liệu · Chuyên sâu</p>
      <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
        {findings.map((f, index) => (
          <li
            key={`${f.finding_id}-${index}`}
            className="rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2.5"
          >
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="gv-mono text-[10px] font-semibold uppercase tracking-wide text-[color:var(--gv-accent-deep)]">
                {STRENGTH_LABEL[f.strength] ?? f.strength}
              </span>
            </div>
            <p className="m-0 text-xs leading-snug text-[color:var(--gv-ink-2)]">{f.teaser}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
