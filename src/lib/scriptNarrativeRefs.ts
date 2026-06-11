import type { DiagnosisReferenceTile } from "@/lib/diagnosisReferenceTiles";
import type {
  DiagnosisSectionVi,
  ReferenceVideoCard,
  ScriptShotCardData,
  ScriptShotReferenceData,
} from "@/lib/api-types";

/** Stable script section titles (ignore noisy Gemini variants). */
export const SCRIPT_NARRATIVE_SECTION_TITLES: Record<string, string> = {
  hook_analysis: "Hook 0–3 giây",
  script_structure: "Cấu trúc 6 cảnh",
  next_video: "Video tiếp theo",
};

export function scriptNarrativeSectionTitle(section: DiagnosisSectionVi): string {
  const sid = String(section.section_id ?? "").trim();
  const mapped = SCRIPT_NARRATIVE_SECTION_TITLES[sid];
  if (mapped) return mapped;
  return (section.title_vi || section.title || sid).trim();
}

function tiktokUrlForRef(ref: ScriptShotReferenceData): string | null {
  if (typeof ref.tiktok_url === "string" && ref.tiktok_url.trim()) {
    return ref.tiktok_url.trim();
  }
  const id = String(ref.video_id ?? "").trim();
  if (!id) return null;
  const handle = String(ref.creator_handle ?? "")
    .replace(/^@/, "")
    .trim();
  if (handle) return `https://www.tiktok.com/@${handle}/video/${id}`;
  return `https://www.tiktok.com/video/${id}`;
}

export function scriptRefToReferenceCard(
  ref: ScriptShotReferenceData,
): ReferenceVideoCard | null {
  const aweme_id = String(ref.video_id ?? "").trim();
  if (!aweme_id) return null;
  const tiktok_url = tiktokUrlForRef(ref);
  const handle = ref.creator_handle ?? null;
  return {
    aweme_id,
    desc: typeof ref.description === "string" ? ref.description : null,
    hook_type: null,
    content_format: null,
    views: typeof ref.views === "number" ? ref.views : null,
    engagement_rate: null,
    author_handle: handle,
    thumbnail_url: ref.thumbnail_url ?? null,
    tiktok_url,
    source: "corpus",
  };
}

export function scriptRefToDiagnosisTile(
  ref: ScriptShotReferenceData,
): DiagnosisReferenceTile | null {
  const card = scriptRefToReferenceCard(ref);
  if (!card) return null;
  const url = card.tiktok_url ?? "";
  const desc = card.desc ?? "";
  return {
    aweme_id: card.aweme_id,
    video_url: url,
    thumbnail_url: card.thumbnail_url ?? "",
    views: card.views ?? 0,
    caption_snippet: desc.slice(0, 200),
    posted_at: "",
    narrative_vi: desc || undefined,
    author_handle: card.author_handle,
    hook_type: null,
    playback_url: null,
  };
}

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

/** Map script narrative section → up to 3 reference clips from shot matcher output. */
export function scriptSectionReferenceTiles(
  sectionId: string,
  shots: ScriptShotCardData[],
): DiagnosisReferenceTile[] {
  const sid = sectionId.trim();
  let pool: ScriptShotReferenceData[] = [];

  if (sid === "hook_analysis") {
    pool = shots[0]?.references ?? [];
  } else if (sid === "script_structure") {
    pool = dedupeRefs(shots.slice(1).flatMap((s) => s.references ?? []));
  } else if (sid === "next_video") {
    pool = shots[5]?.references ?? shots.at(-1)?.references ?? [];
  }

  return dedupeRefs(pool)
    .slice(0, 3)
    .map(scriptRefToDiagnosisTile)
    .filter((t): t is DiagnosisReferenceTile => t !== null);
}
