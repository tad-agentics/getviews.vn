/**
 * ScriptShotRow tests — focused on the S6 per-shot regenerate affordance.
 * The row's structural rendering (timing pill, shot meta, reference strip)
 * is covered by the parent ScriptScreen happy-path tests; here we only
 * exercise the regenerate button's behavior.
 */

import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";
import { ScriptShotRow } from "./ScriptShotRow";

// ShotReferenceStrip + ShotTypeVisual aren't relevant here — short-
// circuit them so tests stay deterministic. FormattedVO + CueChip stay
// real so the structured-vo test below can assert against rendered text.
vi.mock("@/components/v2/ShotReferenceStrip", () => ({
  ShotReferenceStrip: () => null,
}));
vi.mock("@/components/v2/ShotTypeVisual", () => ({
  ShotTypeVisual: () => null,
}));

afterEach(cleanup);

function makeShot(overrides: Partial<ScriptEditorShot> = {}): ScriptEditorShot {
  return {
    t0: 0,
    t1: 3,
    cam: "Cận mặt",
    voice: "Mình vừa test xong",
    viz: "2 sản phẩm cạnh nhau",
    overlay: "BOLD CENTER",
    tip: "",
    corpusAvg: 2.4,
    winnerAvg: 2.4,
    overlayWinner: "white sans 28pt",
    intelSceneType: "face_to_camera",
    references: [],
    ...overrides,
  };
}

describe("ScriptShotRow — per-shot regenerate", () => {
  it("renders the 'viết lại' button only when onRegenerate is provided", () => {
    const { rerender } = render(
      <ScriptShotRow shot={makeShot()} idx={0} active={false} onClick={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: /Viết lại shot/ })).toBeNull();

    rerender(
      <ScriptShotRow
        shot={makeShot()}
        idx={0}
        active={false}
        onClick={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Viết lại shot/ })).toBeTruthy();
  });

  it("clicking the regen button calls onRegenerate but NOT onClick (stopPropagation)", () => {
    const onClick = vi.fn();
    const onRegenerate = vi.fn();
    render(
      <ScriptShotRow
        shot={makeShot()}
        idx={2}
        active={false}
        onClick={onClick}
        onRegenerate={onRegenerate}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Viết lại shot/ }));
    expect(onRegenerate).toHaveBeenCalledTimes(1);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("regenerating=true disables the button, swaps copy to 'đang viết…'", () => {
    const onRegenerate = vi.fn();
    render(
      <ScriptShotRow
        shot={makeShot()}
        idx={0}
        active={false}
        onClick={vi.fn()}
        onRegenerate={onRegenerate}
        regenerating
      />,
    );
    const btn = screen.getByRole("button", { name: /Viết lại shot/ }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(btn.textContent).toMatch(/đang viết/);
    // Click is a no-op while regenerating.
    fireEvent.click(btn);
    expect(onRegenerate).not.toHaveBeenCalled();
  });
});

describe("ScriptShotRow — structured VO (S5)", () => {
  it("renders structured vo with timestamps + bold stress + cue chips", () => {
    const shot = makeShot({
      voice: "Mình vừa test xong, khác thật sự hẳn",
      vo: [
        { t: "0:00", text: "Mình *vừa test* xong.", cue: null },
        { t: "0:01", text: "Khác *thật sự* hẳn.", cue: "[dừng 0.3s]" },
      ],
    });
    const { container } = render(
      <ScriptShotRow shot={shot} idx={0} active={false} onClick={vi.fn()} />,
    );
    // Both timestamps render
    expect(screen.getByText("0:00")).toBeTruthy();
    expect(screen.getByText("0:01")).toBeTruthy();
    // Stress markers wrap into <strong>
    const strongs = container.querySelectorAll("strong");
    expect(strongs.length).toBe(2);
    expect(strongs[0]?.textContent).toBe("vừa test");
    expect(strongs[1]?.textContent).toBe("thật sự");
    // Cue chip on the second line
    expect(screen.getByText("dừng 0.3s")).toBeTruthy();
    // Legacy flat ``"voice"`` rendering is NOT present when vo is set.
    expect(screen.queryByText('"Mình vừa test xong, khác thật sự hẳn"')).toBeNull();
  });

  it("falls back to flat voice string when vo is empty/missing", () => {
    const shot = makeShot({ voice: "Voice cũ", vo: undefined });
    render(
      <ScriptShotRow shot={shot} idx={0} active={false} onClick={vi.fn()} />,
    );
    // Legacy quoted display.
    expect(screen.getByText('"Voice cũ"')).toBeTruthy();
  });
});
