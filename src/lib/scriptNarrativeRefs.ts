import type { DiagnosisReferenceTile } from "@/lib/diagnosisReferenceTiles";
import type {
  DiagnosisSectionVi,
  ReferenceVideoCard,
  ScriptShotReferenceData,
} from "@/lib/api-types";
import { r2VideoPlaybackUrl } from "@/lib/r2";

/** Legacy narrative sections — only ``next_video`` is surfaced in script answer UI. */
export function scriptNextVideoText(sections: DiagnosisSectionVi[]): string | null {
  const row = sections.find((s) => String(s.section_id ?? "").trim() === "next_video");
  const text = (row?.text_vi || row?.text || "").trim();
  return text || null;
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

function scriptRefPlaybackUrl(ref: ScriptShotReferenceData): string | null {
  const explicit =
    typeof ref.playback_url === "string"
      ? ref.playback_url.trim()
      : typeof ref.video_url === "string"
        ? ref.video_url.trim()
        : "";
  if (explicit && explicit.includes("/videos/") && !explicit.includes("tiktokcdn")) {
    return explicit;
  }
  const vid = String(ref.video_id ?? "").trim();
  return r2VideoPlaybackUrl(vid);
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
    playback_url: scriptRefPlaybackUrl(ref),
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
    playback_url: card.playback_url ?? null,
  };
}
