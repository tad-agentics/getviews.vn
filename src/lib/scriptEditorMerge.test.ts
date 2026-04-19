import { describe, expect, it } from "vitest";
import { mergeSceneIntelIntoShots, type ScriptEditorShot } from "./scriptEditorMerge";

const base: ScriptEditorShot[] = [
  {
    t0: 0,
    t1: 2,
    cam: "A",
    voice: "v",
    viz: "z",
    overlay: "NONE",
    tip: "old",
    corpusAvg: 1,
    winnerAvg: 1,
    overlayWinner: "oldw",
    intelSceneType: "face_to_camera",
  },
];

describe("mergeSceneIntelIntoShots", () => {
  it("overlays row metrics when scene_type matches", () => {
    const out = mergeSceneIntelIntoShots(base, [
      {
        niche_id: 1,
        scene_type: "face_to_camera",
        corpus_avg_duration: 3.3,
        winner_avg_duration: 2.2,
        winner_overlay_style: "TEXT_TITLE",
        overlay_samples: [],
        tip: "new tip",
        reference_video_ids: [],
        sample_size: 40,
        computed_at: "2026-01-01T00:00:00Z",
      },
    ]);
    expect(out[0]!.corpusAvg).toBe(3.3);
    expect(out[0]!.winnerAvg).toBe(2.2);
    expect(out[0]!.tip).toBe("new tip");
    expect(out[0]!.overlayWinner).toBe("TEXT_TITLE");
  });

  it("returns originals when scenes missing", () => {
    const out = mergeSceneIntelIntoShots(base, []);
    expect(out[0]!.tip).toBe("old");
  });
});
