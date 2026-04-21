/**
 * Phase D.1.6 — primitive render-test backfill (C.8.6 carryover).
 *
 * ScriptPacingRibbon renders one button per shot at a width proportional to
 * its span; the active shot gets `--gv-accent-soft` as its bar background;
 * slow shots (span > winnerAvg × 1.2) flip the "yours" bar to the accent
 * colour. `onSelectShot` fires on click with the shot index.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";
import { ScriptPacingRibbon } from "./ScriptPacingRibbon";

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
    tip: "Tip",
    corpusAvg: 4,
    winnerAvg: 5,
    overlayWinner: "NONE",
    intelSceneType: "hook",
    ...overrides,
  };
}

describe("ScriptPacingRibbon", () => {
  it("returns null when no shots are provided", () => {
    const { container } = render(
      <ScriptPacingRibbon shots={[]} activeShot={0} onSelectShot={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders one button per shot + kicker copy", () => {
    const shots = [makeShot({ t0: 0, t1: 4 }), makeShot({ t0: 4, t1: 10 })];
    const { container, getByText } = render(
      <ScriptPacingRibbon shots={shots} activeShot={0} onSelectShot={() => {}} />,
    );
    expect(container.querySelectorAll("button").length).toBe(shots.length);
    expect(getByText(/NHỊP ĐỘ · PACING RIBBON/)).toBeTruthy();
  });

  it("applies accent-soft background to the active shot button only", () => {
    const shots = [makeShot({ t0: 0, t1: 4 }), makeShot({ t0: 4, t1: 10 })];
    const { container } = render(
      <ScriptPacingRibbon shots={shots} activeShot={1} onSelectShot={() => {}} />,
    );
    const buttons = container.querySelectorAll("button");
    expect(buttons[0]!.className).not.toMatch(/gv-accent-soft/);
    expect(buttons[1]!.className).toMatch(/gv-accent-soft/);
  });

  it("invokes onSelectShot with the clicked shot index", () => {
    const shots = [makeShot({ t0: 0, t1: 4 }), makeShot({ t0: 4, t1: 10 })];
    const onSelect = vi.fn();
    const { container } = render(
      <ScriptPacingRibbon shots={shots} activeShot={0} onSelectShot={onSelect} />,
    );
    const buttons = container.querySelectorAll("button");
    fireEvent.click(buttons[1]!);
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
