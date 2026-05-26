import type { ChannelDiagnosisFinding } from "@/lib/api-types";
import { auditHintsForFindings, summaryFindingsForStrip } from "./channelFindingGroups";

const STRENGTH_LABEL: Record<string, string> = {
  high: "Mạnh",
  medium: "Vừa",
  low: "Nhẹ",
};

/** Deep diagnosis — evidence-backed findings tile (§5.1 / V5 §2). */
export function ChannelFindingsStrip({ findings }: { findings: ChannelDiagnosisFinding[] }) {
  const summaryFindings = summaryFindingsForStrip(findings);
  const auditHints = auditHintsForFindings(findings);
  if (summaryFindings.length === 0 && auditHints.length === 0) return null;

  return (
    <div
      className="mb-5 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-4"
      aria-label="Nhận định kênh từ dữ liệu"
    >
      <p className="gv-kicker mb-3 text-[color:var(--gv-ink-3)]">Nhận định từ dữ liệu · Chuyên sâu</p>
      {summaryFindings.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
          {summaryFindings.map((f, index) => (
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
      ) : null}
      {auditHints.length > 0 ? (
        <div className={summaryFindings.length > 0 ? "mt-3 flex flex-col gap-2" : "flex flex-col gap-2"}>
          {auditHints.map((hint, index) => (
            <p key={index} className="mb-0 text-[11px] leading-snug text-[color:var(--gv-ink-3)]">
              {hint}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
