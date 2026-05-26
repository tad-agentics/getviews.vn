import type { ChannelDiagnosisFinding } from "@/lib/api-types";
import { accountHealthFindings } from "./channelFindingGroups";

const STRENGTH_LABEL: Record<string, string> = {
  high: "Mạnh",
  medium: "Vừa",
  low: "Nhẹ",
};

/** Account distribution findings tile inside account_health memo section (§5.5 Wave 2). */
export function AccountHealthStrip({ findings }: { findings: ChannelDiagnosisFinding[] }) {
  const healthFindings = accountHealthFindings(findings);
  if (healthFindings.length === 0) return null;

  return (
    <div
      className="mb-4 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-3"
      aria-label="Sức khỏe tài khoản từ dữ liệu"
    >
      <p className="gv-kicker mb-2.5 text-[color:var(--gv-ink-3)]">Phân phối · từ quy luật view</p>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {healthFindings.map((f, index) => (
          <li
            key={`${f.finding_id}-${index}`}
            className="rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2"
          >
            <span className="gv-mono mb-1 block text-[10px] font-semibold uppercase tracking-wide text-[color:var(--gv-warn)]">
              {STRENGTH_LABEL[f.strength] ?? f.strength}
            </span>
            <p className="m-0 text-xs leading-snug text-[color:var(--gv-ink-2)]">{f.teaser}</p>
          </li>
        ))}
      </ul>
      <p className="mb-0 mt-2.5 text-[11px] leading-snug text-[color:var(--gv-ink-3)]">
        Vòng 1: Hãy mở TikTok → Cài đặt → Trạng thái tài khoản (Account Status) để kiểm tra. GetViews không tự đọc được tỷ lệ FYP (xu hướng).
      </p>
    </div>
  );
}
