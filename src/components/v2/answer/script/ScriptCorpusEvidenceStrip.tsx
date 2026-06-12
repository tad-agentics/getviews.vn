import { DiagnosisReferenceVideoCards } from "@/components/diagnosis/DiagnosisReferenceVideoCards";
import type { DiagnosisReferenceTile } from "@/lib/diagnosisReferenceTiles";

export function ScriptCorpusEvidenceStrip({ tiles }: { tiles: DiagnosisReferenceTile[] }) {
  if (!tiles.length) return null;

  return (
    <section
      aria-label="Clip tham chiếu từ corpus"
      className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3.5"
    >
      <DiagnosisReferenceVideoCards
        tiles={tiles}
        label="Clip tham chiếu từ corpus"
        embedded
        showLabel
      />
    </section>
  );
}
