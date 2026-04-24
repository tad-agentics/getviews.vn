/**
 * Phase D.1.6 — primitive render-test backfill (C.8.6 carryover).
 *
 * SceneIntelligencePanel renders five stacked sections:
 *   1. Optional thin-corpus banner (sample < 30).
 *   2. Tip card (serif 18px on ink bg).
 *   3. Độ dài shot + MiniBarCompare.
 *   4. Text overlay library + overlay sample chips.
 *   5. Clip tham khảo row (3 placeholders OR ≤ 5 real thumbs).
 *
 * Uses react-router `<Link>` for clip nav — mock via MemoryRouter.
 */
import { MemoryRouter } from "react-router";
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";
import { SceneIntelligencePanel } from "./SceneIntelligencePanel";

afterEach(() => {
  cleanup();
});

function makeShot(overrides: Partial<ScriptEditorShot> = {}): ScriptEditorShot {
  return {
    t0: 0,
    t1: 5,
    cam: "close-up",
    voice: "Voice",
    viz: "Viz",
    overlay: "NONE",
    tip: "Mở bằng mặt trong 0.5 giây.",
    corpusAvg: 4,
    winnerAvg: 5,
    overlayWinner: "ĐỪNG MUA",
    intelSceneType: "hook",
    references: [],
    ...overrides,
  };
}

function renderPanel(props: Parameters<typeof SceneIntelligencePanel>[0]) {
  return render(
    <MemoryRouter>
      <SceneIntelligencePanel {...props} />
    </MemoryRouter>,
  );
}

describe("SceneIntelligencePanel", () => {
  it("renders the tip card with shot.tip text + SHOT XX kicker", () => {
    const { getByText } = renderPanel({
      shot: makeShot({ tip: "Đừng đổi khung trong 3s." }),
      shotIndex: 2,
      overlaySamples: [],
      referenceClips: [],
    });
    expect(getByText("Đừng đổi khung trong 3s.")).toBeTruthy();
    expect(getByText(/SHOT 03 · PHÂN TÍCH CẤU TRÚC/)).toBeTruthy();
  });

  it("renders the slow-pacing warning when span > winnerAvg × 1.2", () => {
    // span = 7; winnerAvg = 5; 7 > 5 × 1.2 = 6 → slow.
    const { getByText } = renderPanel({
      shot: makeShot({ t0: 0, t1: 7, winnerAvg: 5 }),
      shotIndex: 0,
      overlaySamples: [],
      referenceClips: [],
    });
    expect(getByText(/▲ dài hơn 2\.0s/)).toBeTruthy();
  });

  it("renders the 'đúng nhịp ngách' tick when span is within winnerAvg × 1.2", () => {
    // span = 5; winnerAvg = 5; 5 ≤ 6 → on pace.
    const { getAllByText } = renderPanel({
      shot: makeShot({ t0: 0, t1: 5, winnerAvg: 5 }),
      shotIndex: 0,
      overlaySamples: [],
      referenceClips: [],
    });
    // Copy appears in the header pill; using getAllByText avoids the
    // multiple-match error if an ancestor's textContent matches too.
    expect(getAllByText(/đúng nhịp ngách/).length).toBeGreaterThan(0);
  });

  it("shows the thin-corpus banner when sceneSampleSize < 30", () => {
    const { getByText } = renderPanel({
      shot: makeShot(),
      shotIndex: 0,
      overlaySamples: [],
      referenceClips: [],
      sceneSampleSize: 12,
    });
    expect(getByText(/Ngách đang thưa \(12 video \/ scene\)/)).toBeTruthy();
  });

  it("hides the thin-corpus banner when sceneSampleSize is null or ≥ 30", () => {
    const { queryByText } = renderPanel({
      shot: makeShot(),
      shotIndex: 0,
      overlaySamples: [],
      referenceClips: [],
      sceneSampleSize: 80,
    });
    expect(queryByText(/Ngách đang thưa/)).toBeNull();
  });

  it("anchors the overlay library to overlayCorpusCount when provided", () => {
    const { getByText } = renderPanel({
      shot: makeShot(),
      shotIndex: 0,
      overlaySamples: [],
      referenceClips: [],
      overlayCorpusCount: 47,
    });
    expect(getByText(/Trong 47 video thắng, scene loại này dùng:/)).toBeTruthy();
  });

  it("renders 3 placeholder tiles when referenceClips is empty", () => {
    const { getAllByText } = renderPanel({
      shot: makeShot(),
      shotIndex: 0,
      overlaySamples: [],
      referenceClips: [],
    });
    expect(getAllByText("Sắp có clip").length).toBe(3);
  });

  it("renders up to 3 overlay sample chips when shot.overlay !== NONE", () => {
    const { container } = renderPanel({
      shot: makeShot({ overlay: "TEXT_TITLE" }),
      shotIndex: 0,
      overlaySamples: ["ĐỪNG MUA", "TỐI NAY", "XEM NGAY", "ĐỪNG BỎ LỠ"],
      referenceClips: [],
    });
    // Rounded-full chip buttons; slice(0, 3) caps at 3.
    const chips = container.querySelectorAll("button.rounded-full");
    expect(chips.length).toBe(3);
  });
});
