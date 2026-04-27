/**
 * PatternMiniChart tests — covers the chart-kind dispatcher + the new
 * A2 ``cta_bars`` 2-row horizontal renderer. The legacy vertical
 * ``BarRow`` fallback stays under test so the back-compat path is
 * proven (older payloads still render).
 */

import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { PatternCellPayloadData } from "@/lib/api-types";
import { PatternMiniChart } from "./PatternMiniChart";

afterEach(cleanup);

function makeCell(overrides: Partial<PatternCellPayloadData> = {}): PatternCellPayloadData {
  return {
    title: "CTA",
    finding: "Hỏi ngược",
    detail: "câu hỏi ăn 3.4× follow",
    chart_kind: "cta_bars",
    chart_data: {},
    ...overrides,
  };
}

describe("PatternMiniChart", () => {
  it("renders 2-row CTA layout when chart_data.rows is present", () => {
    const cell = makeCell({
      chart_data: {
        rows: [
          { label: "HỎI NGƯỢC", multiplier: 3.4 },
          { label: '"FOLLOW"', multiplier: 1.0 },
        ],
      },
    });
    render(<PatternMiniChart cell={cell} />);
    expect(screen.getByText("HỎI NGƯỢC")).toBeTruthy();
    expect(screen.getByText('"FOLLOW"')).toBeTruthy();
    expect(screen.getByText(/3\.4×/)).toBeTruthy();
    expect(screen.getByText(/1\.0×/)).toBeTruthy();
  });

  it("uses accent fill on the first (winning) row, gray track on rest", () => {
    const cell = makeCell({
      chart_data: {
        rows: [
          { label: "A", multiplier: 5 },
          { label: "B", multiplier: 1 },
        ],
      },
    });
    const { container } = render(<PatternMiniChart cell={cell} />);
    const accentBars = container.querySelectorAll(".bg-\\[color\\:var\\(--gv-accent\\)\\]");
    // Exactly one accent bar — the primary row.
    expect(accentBars.length).toBe(1);
  });

  it("falls back to vertical BarRow when chart_data carries only legacy bars[]", () => {
    const cell = makeCell({
      chart_data: { bars: [10, 20, 30] },
    });
    const { container } = render(<PatternMiniChart cell={cell} />);
    // No 2-row labels present.
    expect(screen.queryByText(/×/)).toBeNull();
    // BarRow renders 3 vertical divs flex-1.
    const barRow = container.querySelector(".flex-1");
    expect(barRow).toBeTruthy();
  });

  it("falls back to BarRow when rows entries are malformed", () => {
    const cell = makeCell({
      chart_data: {
        rows: [
          { label: "", multiplier: 3 },
          { multiplier: 1 },
          { label: "B", multiplier: 0 },
        ],
        bars: [10, 20],
      },
    });
    render(<PatternMiniChart cell={cell} />);
    // None of the malformed rows survive normCtaRows; BarRow fallback wins.
    expect(screen.queryByText(/×/)).toBeNull();
  });

  it("renders sound_mix split bar from primary_pct", () => {
    const cell = makeCell({
      chart_kind: "sound_mix",
      chart_data: { primary_pct: 62 },
    });
    const { container } = render(<PatternMiniChart cell={cell} />);
    // SoundMixBar wraps in a flex container with two children.
    expect(container.querySelector(".bg-\\[color\\:var\\(--gv-accent-soft\\)\\]")).toBeTruthy();
  });

  it("renders hook_timing track with marker", () => {
    const cell = makeCell({
      chart_kind: "hook_timing",
      chart_data: { marker: 0.42 },
    });
    const { container } = render(<PatternMiniChart cell={cell} />);
    // Marker dot has the accent border.
    expect(container.querySelector(".border-\\[color\\:var\\(--gv-accent\\)\\]")).toBeTruthy();
  });
});
