import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";

/** Positional weights — mirror ``script_generate._WEIGHTS`` (32s baseline). */
const SHOT_WEIGHTS = [3, 5, 8, 8, 6, 2] as const;

const BACKBONE_ROWS: Omit<ScriptEditorShot, "t0" | "t1">[] = [
  {
    cam: "Cận mặt",
    voice: "",
    viz: "",
    overlay: "BOLD CENTER",
    tip: "Hook trong 3 giây đầu — giữ cận mặt ổn định.",
    corpusAvg: 2.8,
    winnerAvg: 2.4,
    overlayWinner: "white sans 28pt · bottom-center",
    intelSceneType: "face_to_camera",
    references: [],
  },
  {
    cam: "Cắt nhanh b-roll",
    voice: "",
    viz: "",
    overlay: "SUB-CAPTION",
    tip: "B-roll nhanh — đừng kéo quá dài so với winner ngách.",
    corpusAvg: 4.2,
    winnerAvg: 5.0,
    overlayWinner: "yellow outlined · mid-left",
    intelSceneType: "product_shot",
    references: [],
  },
  {
    cam: "Side-by-side",
    voice: "",
    viz: "",
    overlay: "STAT BURST",
    tip: "Demo / số liệu — split-screen giúp retention giữa video.",
    corpusAvg: 7.8,
    winnerAvg: 8.0,
    overlayWinner: "number callout 72pt",
    intelSceneType: "demo",
    references: [],
  },
  {
    cam: "POV nghe",
    voice: "",
    viz: "",
    overlay: "LABEL",
    tip: "Giọng giải thích — POV ấm, caption strip dưới đáy.",
    corpusAvg: 6.2,
    winnerAvg: 7.5,
    overlayWinner: "caption strip · bottom",
    intelSceneType: "face_to_camera",
    references: [],
  },
  {
    cam: "Cận tay + texture",
    voice: "",
    viz: "",
    overlay: "NONE",
    tip: "Texture cận — không overlay, nhịp chậm hơn giữa video.",
    corpusAvg: 5.1,
    winnerAvg: 5.0,
    overlayWinner: "—",
    intelSceneType: "action",
    references: [],
  },
  {
    cam: "Cận mặt + câu hỏi",
    voice: "",
    viz: "",
    overlay: "QUESTION XL",
    tip: "CTA câu hỏi — kết bằng cận mặt, overlay câu hỏi to.",
    corpusAvg: 2.4,
    winnerAvg: 2.5,
    overlayWinner: "question mark · full bleed",
    intelSceneType: "face_to_camera",
    references: [],
  },
];

/** Six-shot editor fallbacks scaled to ``durationSec`` (default 32). */
export function scriptEditorFallbacks(durationSec = 32): ScriptEditorShot[] {
  const totalWeight = SHOT_WEIGHTS.reduce((a, b) => a + b, 0);
  let cursor = 0;
  return BACKBONE_ROWS.map((row, i) => {
    const span = (SHOT_WEIGHTS[i]! / totalWeight) * durationSec;
    const t0 = cursor;
    const t1 = cursor + span;
    cursor = t1;
    return { ...row, t0, t1 };
  });
}
