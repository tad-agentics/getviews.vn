import type { SceneIntelligenceRow } from "@/lib/api-types";

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
};

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
