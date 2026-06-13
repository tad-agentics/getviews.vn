import type {
  DiagnosisFinding,
  DiagnosisSectionVi,
  VideoStructureAxisBlock,
  VideoStructureAxisId,
} from "@/lib/api-types";

/** Unified FE block for editing + sound + script_structure + persona (after hook_analysis). */
export const VIDEO_STRUCTURE_SECTION_TITLE = "Phân tích cấu trúc Video";

export const STRUCTURE_AXIS_TITLES: Record<VideoStructureAxisId, string> = {
  rhythm: "Nhịp & cắt",
  editing: "Hậu kỳ & hình",
  sound: "Âm thanh",
  persona: "Giọng & persona",
};

const MERGE_SOURCE_IDS = new Set(["editing", "sound", "script_structure", "persona"]);

function sectionBody(s: DiagnosisSectionVi): string {
  return (s.text_vi || s.text || "").trim();
}

const MERGED_FINDINGS_CAP = 6;
const MERGED_TILES_CAP = 3;

function tileAwemeId(tile: unknown): string {
  if (!tile || typeof tile !== "object") return "";
  return String((tile as { aweme_id?: string }).aweme_id ?? "").trim();
}

function hasFindingContent(f: DiagnosisFinding): boolean {
  return Boolean(f.title_vi || f.body_vi || f.fix_vi);
}

function buildAxisBlock(
  axisId: VideoStructureAxisId,
  section: DiagnosisSectionVi | undefined,
): VideoStructureAxisBlock | null {
  if (!section) return null;
  const text = sectionBody(section);
  const findings = (section.findings ?? []).filter(hasFindingContent);
  const tiles = Array.isArray(section.embedded_tiles) ? section.embedded_tiles : [];
  if (!text && findings.length === 0 && tiles.length === 0) {
    return null;
  }
  return {
    axis_id: axisId,
    title_vi: STRUCTURE_AXIS_TITLES[axisId],
    text_vi: text,
    text,
    findings: findings.length > 0 ? findings : undefined,
    embedded_tiles: tiles.length > 0 ? tiles : undefined,
  };
}

function buildStructureAxes(
  editing: DiagnosisSectionVi | undefined,
  sound: DiagnosisSectionVi | undefined,
  script: DiagnosisSectionVi | undefined,
  persona: DiagnosisSectionVi | undefined,
): VideoStructureAxisBlock[] {
  const axes: VideoStructureAxisBlock[] = [];
  const rhythm = buildAxisBlock("rhythm", script);
  if (rhythm) axes.push(rhythm);
  const editingAxis = buildAxisBlock("editing", editing);
  if (editingAxis) axes.push(editingAxis);
  const soundAxis = buildAxisBlock("sound", sound);
  if (soundAxis) axes.push(soundAxis);
  const personaAxis = buildAxisBlock("persona", persona);
  if (personaAxis) axes.push(personaAxis);
  return axes;
}

/** script → editing → sound → persona per round. */
function mergeFindingsRoundRobin(
  script: DiagnosisFinding[],
  editing: DiagnosisFinding[],
  sound: DiagnosisFinding[],
  persona: DiagnosisFinding[],
): DiagnosisFinding[] {
  const sources = [
    script.filter(hasFindingContent),
    editing.filter(hasFindingContent),
    sound.filter(hasFindingContent),
    persona.filter(hasFindingContent),
  ];
  const out: DiagnosisFinding[] = [];
  let round = 0;
  while (out.length < MERGED_FINDINGS_CAP) {
    let pushed = false;
    for (const src of sources) {
      if (round < src.length && out.length < MERGED_FINDINGS_CAP) {
        out.push(src[round]!);
        pushed = true;
      }
    }
    if (!pushed) break;
    round += 1;
  }
  return out;
}

function dedupeEmbeddedTiles(...tileGroups: unknown[][]): unknown[] {
  const seen = new Set<string>();
  const out: unknown[] = [];
  for (const tile of tileGroups.flat()) {
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
  editing: DiagnosisSectionVi | undefined,
  sound: DiagnosisSectionVi | undefined,
  script: DiagnosisSectionVi | undefined,
  persona: DiagnosisSectionVi | undefined,
): DiagnosisSectionVi {
  const structureAxes = buildStructureAxes(editing, sound, script, persona);
  const findings = mergeFindingsRoundRobin(
    script?.findings ?? [],
    editing?.findings ?? [],
    sound?.findings ?? [],
    persona?.findings ?? [],
  );

  const tiles = dedupeEmbeddedTiles(
    Array.isArray(script?.embedded_tiles) ? script.embedded_tiles : [],
    Array.isArray(editing?.embedded_tiles) ? editing.embedded_tiles : [],
    Array.isArray(sound?.embedded_tiles) ? sound.embedded_tiles : [],
    Array.isArray(persona?.embedded_tiles) ? persona.embedded_tiles : [],
  );

  return {
    section_id: "script_structure",
    title_vi: VIDEO_STRUCTURE_SECTION_TITLE,
    title: VIDEO_STRUCTURE_SECTION_TITLE,
    text_vi: "",
    text: "",
    structure_axes: structureAxes.length > 0 ? structureAxes : undefined,
    findings: findings.length > 0 ? findings : undefined,
    embedded_tiles: tiles.length > 0 ? tiles : undefined,
  };
}

/**
 * Collapse «Hậu kỳ», «Âm thanh», «Phong cách», và «Cấu trúc video» into one
 * block and insert it immediately after hook_analysis.
 */
export function mergeVideoStructureSections(
  sections: DiagnosisSectionVi[],
): DiagnosisSectionVi[] {
  if (!sections.length) return sections;

  const editing = sections.find((s) => String(s.section_id) === "editing");
  const sound = sections.find((s) => String(s.section_id) === "sound");
  const script = sections.find((s) => String(s.section_id) === "script_structure");
  const persona = sections.find((s) => String(s.section_id) === "persona");
  if (!editing && !sound && !script && !persona) return sections;

  const rest = sections.filter((s) => !MERGE_SOURCE_IDS.has(String(s.section_id)));
  const merged = mergeDiagnosisSection(editing, sound, script, persona);

  const hookIdx = rest.findIndex((s) => String(s.section_id) === "hook_analysis");
  const insertAt = hookIdx >= 0 ? hookIdx + 1 : rest.length;
  const out = [...rest];
  out.splice(insertAt, 0, merged);
  return out;
}
