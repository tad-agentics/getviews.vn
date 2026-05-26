import type { ChannelDiagnosisFinding } from "@/lib/api-types";
import { AUDIT_RINGS, findingsForRing } from "./channelFindingGroups";

const STRENGTH_LABEL: Record<string, string> = {
  high: "Mạnh",
  medium: "Vừa",
  low: "Nhẹ",
};

function RingStatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={
        "gv-mono shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide " +
        (active
          ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
          : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]")
      }
    >
      {active ? "⚠ cần xem" : "— chưa có tín hiệu"}
    </span>
  );
}

/** V5 five-ring audit map for channel deep diagnosis (§5.3 / §5.5). */
export function ChannelAuditRingsPanel({ findings }: { findings: ChannelDiagnosisFinding[] }) {
  return (
    <div
      className="mb-5 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-4 py-4"
      aria-label="Kiểm toán theo Vòng"
    >
      <p className="gv-kicker mb-1 text-[color:var(--gv-ink-3)]">Kiểm toán theo Vòng · Chuyên sâu</p>
      <p className="mb-4 text-[11px] leading-snug text-[color:var(--gv-ink-4)]">
        Năm tầng kiểm tra thuật toán — map finding kênh vào bước cần xử lý trước.
      </p>
      <ol className="m-0 flex list-none flex-col gap-3 p-0">
        {AUDIT_RINGS.map((ring) => {
          const ringFindings = findingsForRing(ring, findings);
          const active = ringFindings.length > 0;
          return (
            <li
              key={ring.id}
              className={
                "rounded-[10px] border px-3 py-3 " +
                (active
                  ? "border-[color:var(--gv-accent)] bg-[color:var(--gv-paper)]"
                  : "border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]")
              }
            >
              <div className="flex items-start gap-3">
                <span
                  className="gv-mono flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[12px] font-semibold text-[color:var(--gv-ink-2)]"
                  aria-hidden
                >
                  {ring.step}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="m-0 text-sm font-medium leading-snug text-[color:var(--gv-ink)]">
                        {ring.title}
                      </p>
                      <p className="gv-mono m-0 mt-0.5 text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">
                        {ring.subtitle}
                      </p>
                    </div>
                    <RingStatusBadge active={active} />
                  </div>

                  {ringFindings.length > 0 ? (
                    <ul className="mb-2.5 mt-2 flex list-none flex-col gap-1.5 p-0">
                      {ringFindings.map((f, index) => (
                        <li
                          key={`${f.finding_id}-${index}`}
                          className="rounded-[8px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-2.5 py-2"
                        >
                          <span className="gv-mono mb-0.5 block text-[10px] font-semibold uppercase tracking-wide text-[color:var(--gv-accent-deep)]">
                            {STRENGTH_LABEL[f.strength] ?? f.strength}
                          </span>
                          <p className="m-0 text-xs leading-snug text-[color:var(--gv-ink-2)]">
                            {f.teaser}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mb-2.5 mt-1 text-[11px] leading-snug text-[color:var(--gv-ink-4)]">
                      Chưa thấy dấu hiệu chặn ở tầng này từ corpus kênh.
                    </p>
                  )}

                  <p className="mb-0 text-[11px] leading-snug text-[color:var(--gv-ink-3)]">
                    {ring.hint}
                  </p>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
