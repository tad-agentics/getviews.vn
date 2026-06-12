import type { DiagnosisSectionVi } from "@/lib/api-types";

/** Unified FE block for sound + script_structure (placed after hook_analysis). */
export const VIDEO_STRUCTURE_SECTION_TITLE = "Phân tích cấu trúc Video";

const MERGE_SOURCE_IDS = new Set(["sound", "script_structure"]);

function sectionBody(s: DiagnosisSectionVi): string {
  return (s.text_vi || s.text || "").trim();
}

const MERGED_FINDINGS_CAP = 3;
const MERGED_TILES_CAP = 3;

function tileAwemeId(tile: unknown): string {
  if (!tile || typeof tile !== "object") return "";
  return String((tile as { aweme_id?: string }).aweme_id ?? "").trim();
}

/** script_structure prose is canonical; sound section is findings-only on the BE. */
function mergedStructureProse(
  sound: DiagnosisSectionVi | undefined,
  script: DiagnosisSectionVi | undefined,
): string {
  const scriptText = script ? sectionBody(script) : "";
  if (scriptText) return scriptText;
  return sound ? sectionBody(sound) : "";
}

function dedupeEmbeddedTiles(
  scriptTiles: unknown[],
  soundTiles: unknown[],
): unknown[] {
  const seen = new Set<string>();
  const out: unknown[] = [];
  for (const tile of [...scriptTiles, ...soundTiles]) {
    const aid = tileAwemeId(tile);
    if (aid) {
      if (seen.has(aid)) continue;
      seen.add(aid);
    }
    out.push(tile);
    if (out.length >= MERGED_TILES_CAP) break;
  }
  return out;
}

function mergeDiagnosisSection(
  sound: DiagnosisSectionVi | undefined,
  script: DiagnosisSectionVi | undefined,
): DiagnosisSectionVi {
  const findings = [
    ...(script?.findings ?? []),
    ...(sound?.findings ?? []),
  ]
    .filter((f) => f.title_vi || f.body_vi || f.fix_vi)
    .slice(0, MERGED_FINDINGS_CAP);

  const tiles = dedupeEmbeddedTiles(
    Array.isArray(script?.embedded_tiles) ? script.embedded_tiles : [],
    Array.isArray(sound?.embedded_tiles) ? sound.embedded_tiles : [],
  );

  const text = mergedStructureProse(sound, script);

  return {
    section_id: "script_structure",
    title_vi: VIDEO_STRUCTURE_SECTION_TITLE,
    title: VIDEO_STRUCTURE_SECTION_TITLE,
    text_vi: text,
    text,
    findings: findings.length > 0 ? findings : undefined,
    embedded_tiles: tiles.length > 0 ? tiles : undefined,
    next_video: script?.next_video ?? sound?.next_video ?? null,
  };
}

/**
 * Collapse «Âm thanh và nhịp điệu» + «Dòng thời gian · Cấu trúc video» into one
 * block and insert it immediately after hook_analysis.
 */
export function mergeVideoStructureSections(
  sections: DiagnosisSectionVi[],
): DiagnosisSectionVi[] {
  if (!sections.length) return sections;

  const sound = sections.find((s) => String(s.section_id) === "sound");
  const script = sections.find((s) => String(s.section_id) === "script_structure");
  if (!sound && !script) return sections;

  const rest = sections.filter((s) => !MERGE_SOURCE_IDS.has(String(s.section_id)));
  const merged = mergeDiagnosisSection(sound, script);

  const hookIdx = rest.findIndex((s) => String(s.section_id) === "hook_analysis");
  const insertAt = hookIdx >= 0 ? hookIdx + 1 : rest.length;
  const out = [...rest];
  out.splice(insertAt, 0, merged);
  return out;
}
