import type { SceneIntelligenceRow, ScriptShot, ShotReference } from "@/lib/api-types";

/** In-memory shot row for the script studio (B.4.3) before ``POST /script/generate``. */
export type ScriptEditorShot = {
  t0: number;
  t1: number;
  cam: string;
  voice: string;
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

/** Map ``POST /script/generate`` rows into editor state (tips fall back to templates). */
export function apiShotsToEditorShots(rows: ScriptShot[], fallbacks: ScriptEditorShot[]): ScriptEditorShot[] {
  return rows.map((s, i) => {
    const fb = fallbacks[Math.min(i, fallbacks.length - 1)]!;
    return {
      t0: s.t0,
      t1: s.t1,
      cam: s.cam,
      voice: s.voice,
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
