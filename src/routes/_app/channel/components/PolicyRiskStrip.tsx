import type { ChannelDiagnosisFinding } from "@/lib/api-types";
import { policyRiskFindings } from "./channelFindingGroups";

const STRENGTH_LABEL: Record<string, string> = {
  high: "Mạnh",
  medium: "Vừa",
  low: "Nhẹ",
};

/** Compliance findings tile inside policy_risk memo section (§5.5 Wave 2). */
export function PolicyRiskStrip({ findings }: { findings: ChannelDiagnosisFinding[] }) {
  const policyFindings = policyRiskFindings(findings);
  if (policyFindings.length === 0) return null;

  return (
    <div
      className="mb-4 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-3"
      aria-label="Rủi ro chính sách từ dữ liệu"
    >
      <p className="gv-kicker mb-2.5 text-[color:var(--gv-ink-3)]">Tuân thủ chính sách · từ video của kênh</p>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {policyFindings.map((f, index) => (
          <li
            key={`${f.finding_id}-${index}`}
            className="rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2"
          >
            <span className="gv-mono mb-1 block text-[10px] font-semibold uppercase tracking-wide text-[color:var(--gv-neg-deep)]">
              {STRENGTH_LABEL[f.strength] ?? f.strength}
            </span>
            <p className="m-0 text-xs leading-snug text-[color:var(--gv-ink-2)]">{f.teaser}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
