import { DiagnosisReferenceVideoCards } from "@/components/diagnosis/DiagnosisReferenceVideoCards";
import type { DiagnosisSectionVi, ScriptShotCardData } from "@/lib/api-types";
import {
  scriptNarrativeSectionTitle,
  scriptSectionReferenceTiles,
} from "@/lib/scriptNarrativeRefs";
import { ScriptNarrativeProse } from "./ScriptNarrativeProse";

export function ScriptNarrativeSections({
  sections,
  shots,
}: {
  sections: DiagnosisSectionVi[];
  shots: ScriptShotCardData[];
}) {
  if (!sections.length) return null;

  return (
    <section
      aria-label="Phân tích kịch bản"
      className="space-y-4 border-t border-[color:var(--gv-rule)] pt-5"
    >
      <p className="gv-mono m-0 text-[11px] font-semibold gv-kicker tracking-[0.12em] text-[color:var(--gv-ink-3)]">
        Phân tích kịch bản
      </p>
      {sections.map((section) => {
        const sid = String(section.section_id ?? "");
        const title = scriptNarrativeSectionTitle(section);
        const text = (section.text_vi || section.text || "").trim();
        const tiles = scriptSectionReferenceTiles(sid, shots);

        return (
          <article
            key={sid || title}
            className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3.5"
          >
            <h3 className="gv-tight m-0 text-base font-semibold leading-snug text-[color:var(--gv-ink)]">
              {title}
            </h3>
            {text ? <ScriptNarrativeProse text={text} /> : null}
            {tiles.length > 0 ? (
              <div className="mt-3 border-t border-[color:var(--gv-rule)] pt-3">
                <DiagnosisReferenceVideoCards
                  tiles={tiles}
                  label="Clip tham chiếu từ corpus"
                />
              </div>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
