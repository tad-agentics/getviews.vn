import type { SceneIntelligenceRow, ScriptReferenceClip, ScriptShot, ShotReference, VoLine } from "@/lib/api-types";
import type { ScriptShotCardData, ScriptShotReferenceData } from "@/lib/api-types";

/** In-memory shot row for the script studio (B.4.3) before ``POST /script/generate``. */
export type ScriptEditorShot = {
  t0: number;
  t1: number;
  cam: string;
  voice: string;
  /**
   * S5 — structured voice-over (timed lines + inline cues + ``*stress*``
   * markers). Optional; ScriptShotRow falls back to the flat ``voice``
   * string when this is empty.
   */
  vo?: VoLine[];
  viz: string;
  overlay: string;
  tip: string;
  corpusAvg: number;
  winnerAvg: number;
  overlayWinner: string;
  /** Join key for ``scene_intelligence.scene_type``. */
  intelSceneType: string;
  /**
   * Wave 2.5 Phase B PR #7 — per-shot reference cards. Empty array on
   * fallback tiles so the downstream component can render a neutral
   * "chưa có clip tham chiếu" state without null-checking.
   */
  references: ShotReference[];
};

export function reportShotsToEditorShots(
  rows: ScriptShotCardData[],
  fallbacks: ScriptEditorShot[],
): ScriptEditorShot[] {
  return rows.map((s, i) => {
    const fb = fallbacks[Math.min(i, fallbacks.length - 1)]!;
    return {
      t0: s.t0 ?? fb.t0,
      t1: s.t1 ?? fb.t1,
      cam: s.cam ?? fb.cam,
      voice: s.voice ?? fb.voice,
      vo:
        Array.isArray(s.vo) && s.vo.length > 0 ? (s.vo as unknown as VoLine[]) : undefined,
      viz: s.viz ?? fb.viz,
      overlay: s.overlay ?? fb.overlay,
      tip: fb.tip,
      corpusAvg: s.corpus_avg ?? fb.corpusAvg,
      winnerAvg: s.winner_avg ?? fb.winnerAvg,
      overlayWinner: (s.overlay_winner as string | undefined) ?? fb.overlayWinner,
      intelSceneType: s.intel_scene_type ?? fb.intelSceneType,
      references: cardReferencesToShotReferences(s.references),
    };
  });
}

function cardReferencesToShotReferences(
  refs: ScriptShotReferenceData[] | undefined,
): ShotReference[] {
  if (!refs?.length) return [];
  return refs.map((ref, i) => ({
    video_id: String(ref.video_id ?? `ref-${i}`),
    scene_index: typeof ref.scene_index === "number" ? ref.scene_index : 0,
    start_s: typeof ref.start_s === "number" ? ref.start_s : null,
    end_s: typeof ref.end_s === "number" ? ref.end_s : null,
    frame_url: typeof ref.frame_url === "string" ? ref.frame_url : null,
    thumbnail_url: ref.thumbnail_url ?? null,
    tiktok_url: typeof ref.tiktok_url === "string" ? ref.tiktok_url : null,
    creator_handle: ref.creator_handle ?? null,
    description: typeof ref.description === "string" ? ref.description : null,
    views: typeof ref.views === "number" ? ref.views : null,
    score: typeof ref.score === "number" ? ref.score : 0,
    match_signals: Array.isArray(ref.match_signals) ? (ref.match_signals as string[]) : [],
    match_label: typeof ref.match_label === "string" ? ref.match_label : "",
  }));
}

export function referenceClipsFromEditorShot(shot: ScriptEditorShot): ScriptReferenceClip[] {
  return shot.references.map((ref) => {
    const duration =
      ref.end_s != null && ref.start_s != null && ref.end_s > ref.start_s
        ? ref.end_s - ref.start_s
        : 3;
    return {
      video_id: ref.video_id,
      thumbnail_url: ref.thumbnail_url ?? ref.frame_url,
      handle: (ref.creator_handle ?? "creator").replace(/^@/, ""),
      label: ref.match_label?.trim() || ref.description?.trim() || "Clip tham khảo",
      duration_sec: duration,
    };
  });
}

export function sceneRowForShot(
  scenes: SceneIntelligenceRow[] | undefined,
  intelSceneType: string,
): SceneIntelligenceRow | undefined {
  if (!scenes?.length || !intelSceneType) return undefined;
  return scenes.find((row) => row.scene_type === intelSceneType);
}

/** Map ``POST /script/generate`` rows into editor state (tips fall back to templates). */
export function apiShotsToEditorShots(rows: ScriptShot[], fallbacks: ScriptEditorShot[]): ScriptEditorShot[] {
  return rows.map((s, i) => {
    const fb = fallbacks[Math.min(i, fallbacks.length - 1)]!;
    return {
      t0: s.t0,
      t1: s.t1,
      cam: s.cam,
      voice: s.voice,
      vo: Array.isArray(s.vo) && s.vo.length > 0 ? s.vo : undefined,
      viz: s.viz,
      overlay: s.overlay,
      tip: fb.tip,
      corpusAvg: s.corpus_avg ?? fb.corpusAvg,
      winnerAvg: s.winner_avg ?? fb.winnerAvg,
      overlayWinner: s.overlay_winner ?? fb.overlayWinner,
      intelSceneType: s.intel_scene_type ?? fb.intelSceneType,
      references: s.references ?? [],
    };
  });
}

export function mergeSceneIntelIntoShots(
  shots: ScriptEditorShot[],
  scenes: SceneIntelligenceRow[] | undefined | null,
): ScriptEditorShot[] {
  if (!scenes?.length) return shots;
  const m = new Map(scenes.map((s) => [s.scene_type, s]));
  return shots.map((shot) => {
    const row = m.get(shot.intelSceneType);
    if (!row) return shot;
    const c = row.corpus_avg_duration;
    const w = row.winner_avg_duration;
    return {
      ...shot,
      corpusAvg: typeof c === "number" ? c : shot.corpusAvg,
      winnerAvg: typeof w === "number" ? w : shot.winnerAvg,
      tip: row.tip?.trim() ? row.tip : shot.tip,
      overlayWinner: row.winner_overlay_style?.trim()
        ? row.winner_overlay_style
        : shot.overlayWinner,
    };
  });
}
