/**
 * CueChip tests — S5 directorial-tag pill.
 * Per design pack ``screens/script.jsx`` lines 1253-1268.
 */

import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { CueChip } from "./CueChip";

afterEach(cleanup);

describe("CueChip", () => {
  it("renders nothing for null/empty/whitespace", () => {
    const { container: c1 } = render(<CueChip text={null} />);
    expect(c1.firstChild).toBeNull();
    const { container: c2 } = render(<CueChip text="" />);
    expect(c2.firstChild).toBeNull();
    const { container: c3 } = render(<CueChip text="   " />);
    expect(c3.firstChild).toBeNull();
  });

  it("strips outer brackets so the chip shows only inner copy", () => {
    render(<CueChip text="[dừng 0.3s]" />);
    expect(screen.getByText("dừng 0.3s")).toBeTruthy();
  });

  it("classifies pause cues with kind=pause", () => {
    const { container } = render(<CueChip text="[dừng 0.3s]" />);
    const chip = container.querySelector('[data-cue-kind]') as HTMLElement;
    expect(chip.getAttribute("data-cue-kind")).toBe("pause");
  });

  it("classifies cut/B-roll cues with kind=cut", () => {
    const { container: c1 } = render(<CueChip text="[CUT close-up]" />);
    expect(
      c1.querySelector('[data-cue-kind]')?.getAttribute("data-cue-kind"),
    ).toBe("cut");
    const { container: c2 } = render(<CueChip text="[B-roll: zoom giá]" />);
    expect(
      c2.querySelector('[data-cue-kind]')?.getAttribute("data-cue-kind"),
    ).toBe("cut");
  });

  it("classifies SFX cues with kind=sfx", () => {
    const { container } = render(<CueChip text="[SFX click]" />);
    expect(
      container.querySelector('[data-cue-kind]')?.getAttribute("data-cue-kind"),
    ).toBe("sfx");
  });

  it("classifies unknown cues with kind=generic", () => {
    const { container } = render(<CueChip text="[mặt nghiêm]" />);
    expect(
      container.querySelector('[data-cue-kind]')?.getAttribute("data-cue-kind"),
    ).toBe("generic");
  });
});
