/**
 * Phase D.1.4 — PostingHeatmap cell-tone classification + render contract.
 *
 * The colour helpers (`postingCellBackground`, `postingCellLabelColor`)
 * are pure functions — we exercise the five-band ramp + edge cases
 * (max=0, value=0, value=max). The render tests cover axis labels +
 * per-cell aria-label shape so a screen reader user can locate
 * "T4 · 18–20 · 6 video".
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  PostingHeatmap,
  postingCellBackground,
  postingCellLabelColor,
} from "./PostingHeatmap";

afterEach(() => {
  cleanup();
});

describe("postingCellBackground", () => {
  it("returns paper when value is 0 regardless of max", () => {
    expect(postingCellBackground(0, 10)).toBe("var(--gv-paper)");
    expect(postingCellBackground(0, 0)).toBe("var(--gv-paper)");
  });

  it("returns paper when max is 0 even if value is positive (guard)", () => {
    expect(postingCellBackground(3, 0)).toBe("var(--gv-paper)");
  });

  it("classifies into five bands against max", () => {
    // Max = 20; walk the five bands.
    expect(postingCellBackground(18, 20)).toBe("var(--gv-ink)"); // ≥ 0.85
    expect(postingCellBackground(12, 20)).toBe("var(--gv-ink-3)"); // ≥ 0.6
    expect(postingCellBackground(8, 20)).toBe("var(--gv-ink-4)"); // ≥ 0.35
    expect(postingCellBackground(3, 20)).toBe("var(--gv-rule)"); // ≥ 0.1
    expect(postingCellBackground(1, 20)).toBe("var(--gv-rule-2)"); // < 0.1
  });

  it("peak cell at max always hits the darkest ink", () => {
    expect(postingCellBackground(3, 3)).toBe("var(--gv-ink)");
    expect(postingCellBackground(1, 1)).toBe("var(--gv-ink)");
  });
});

describe("postingCellLabelColor", () => {
  it("returns muted ink when value is 0", () => {
    expect(postingCellLabelColor(0, 10)).toBe("var(--gv-ink-4)");
  });

  it("uses paper on dark cells (≥ 0.6 of max)", () => {
    expect(postingCellLabelColor(10, 10)).toBe("var(--gv-paper)");
    expect(postingCellLabelColor(7, 10)).toBe("var(--gv-paper)");
  });

  it("uses ink on mid cells (0.35 ≤ pct < 0.6)", () => {
    expect(postingCellLabelColor(4, 10)).toBe("var(--gv-ink)");
  });

  it("uses muted ink on light cells (< 0.35)", () => {
    expect(postingCellLabelColor(2, 10)).toBe("var(--gv-ink-3)");
  });
});

describe("PostingHeatmap", () => {
  it("renders the 7-day label column (T2..CN)", () => {
    const grid = Array.from({ length: 7 }, () => Array(8).fill(0));
    const { getByText } = render(<PostingHeatmap grid={grid} />);
    ["T2", "T3", "T4", "T5", "T6", "T7", "CN"].forEach((label) => {
      expect(getByText(label)).toBeTruthy();
    });
  });

  it("renders the 8 hour-bucket headers", () => {
    const grid = Array.from({ length: 7 }, () => Array(8).fill(0));
    const { getByText } = render(<PostingHeatmap grid={grid} />);
    ["6–9", "9–12", "12–15", "15–18", "18–20", "20–22", "22–24", "0–3"].forEach((h) => {
      expect(getByText(h)).toBeTruthy();
    });
  });

  it("labels cells with value + video suffix and hides zero counts", () => {
    // Row T2 (index 0) hour bucket 4 (18–20) gets 6 videos; rest 0.
    const grid: number[][] = Array.from({ length: 7 }, () => Array(8).fill(0));
    grid[0][4] = 6;
    const { container, getByLabelText } = render(<PostingHeatmap grid={grid} />);
    expect(getByLabelText("T2 · 18–20 · 6 video")).toBeTruthy();
    // The zero cells render an empty string (not "0"). 55 zero cells + 1 labelled.
    const zeroCells = container.querySelectorAll("[aria-label$='0 video']");
    expect(zeroCells.length).toBe(55);
  });

  it("renders with the optional legend footer when provided", () => {
    const grid = Array.from({ length: 7 }, () => Array(8).fill(0));
    const { getByText } = render(
      <PostingHeatmap grid={grid} legendFooter="Dữ liệu 90d · 120 video" />,
    );
    expect(getByText(/Dữ liệu 90d · 120 video/)).toBeTruthy();
  });
});
