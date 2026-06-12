import type { DiagnosisReferenceTile } from "@/lib/diagnosisReferenceTiles";
import type { ScriptShotCardData, ScriptShotReferenceData } from "@/lib/api-types";
import { scriptRefToDiagnosisTile } from "@/lib/scriptNarrativeRefs";

function dedupeRefs(refs: ScriptShotReferenceData[]): ScriptShotReferenceData[] {
  const seen = new Set<string>();
  const out: ScriptShotReferenceData[] = [];
  for (const ref of refs) {
    const id = String(ref.video_id ?? "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    out.push(ref);
  }
  return out;
}

/** All unique corpus reference clips across shots — single evidence strip in script answers. */
export function allScriptCorpusTiles(
  shots: ScriptShotCardData[],
  limit = 6,
): DiagnosisReferenceTile[] {
  const pool = dedupeRefs(shots.flatMap((s) => s.references ?? []));
  return pool
    .slice(0, limit)
    .map(scriptRefToDiagnosisTile)
    .filter((t): t is DiagnosisReferenceTile => t !== null);
}
