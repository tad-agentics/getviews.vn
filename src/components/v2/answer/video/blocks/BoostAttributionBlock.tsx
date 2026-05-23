import type { BoostAttributionLevel, DiagnosisFinding } from "@/lib/api-types";
import {
  boostAttributionLabel,
  shouldShowBoostAttributionBlock,
} from "@/lib/boostAttributionLabels";

export function BoostAttributionBlock({
  attribution,
  referenceEligible,
  findings,
}: {
  attribution?: BoostAttributionLevel | string | null;
  referenceEligible?: boolean | null;
  findings?: DiagnosisFinding[] | null;
}) {
  const show =
    shouldShowBoostAttributionBlock(attribution, referenceEligible) ||
    (findings?.length ?? 0) > 0;
  if (!show) return null;

  const label = boostAttributionLabel(attribution);
  const isSuspect =
    attribution === "suspect_medium" ||
    attribution === "suspect_low" ||
    referenceEligible === false;

  const cardFindings = (findings ?? []).filter(
    (f) => f.title_vi || f.body_vi || f.fix_vi,
  );

  return (
    <section
      className="mb-4 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
      aria-label="Phân loại nguồn view"
    >
      <p className="gv-kicker mb-2 text-[color:var(--gv-ink-3)]">Nguồn view & tham chiếu corpus</p>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`gv-mono rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide ${
            isSuspect
              ? "bg-[color:var(--gv-warn-soft)] text-[color:var(--gv-warn)]"
              : "bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos)]"
          }`}
        >
          {label}
        </span>
        {referenceEligible === false ? (
          <span className="gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
            Loại khỏi pool tham chiếu organic
          </span>
        ) : referenceEligible === true ? (
          <span className="gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
            Đủ điều kiện pool tham chiếu
          </span>
        ) : null}
      </div>
      {cardFindings.length > 0 ? (
        <ul className="mt-3 flex list-none flex-col gap-2 p-0">
          {cardFindings.map((f, i) => (
            <li
              key={i}
              className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-sm leading-relaxed text-[color:var(--gv-ink-2)]"
            >
              {f.title_vi ? (
                <span className="font-medium text-[color:var(--gv-ink)]">{f.title_vi}</span>
              ) : null}
              {f.body_vi ? (
                <p className={f.title_vi ? "mt-1" : ""}>{f.body_vi}</p>
              ) : null}
              {f.fix_vi ? (
                <p className="mt-1 text-[color:var(--gv-ink-3)]">
                  <span className="gv-mono font-semibold text-[color:var(--gv-accent)]">Sửa: </span>
                  {f.fix_vi}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm leading-relaxed text-[color:var(--gv-ink-2)]">
          View cao nhưng tương tác mỏng so cohort — kiểm tra nguồn traffic trước khi coi hook/ER là chuẩn organic.
        </p>
      )}
    </section>
  );
}
