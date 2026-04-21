/**
 * Phase D.1.6 — primitive render-test backfill (C.8.6 carryover).
 *
 * MiniBarCompare renders three labelled horizontal bars (Của bạn / Ngách TB /
 * Winner) with widths scaled against the max value × 1.1 padding. Labels
 * are Vietnamese; values render with a trailing "s" suffix to one decimal.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { MiniBarCompare } from "./MiniBarCompare";

afterEach(() => {
  cleanup();
});

describe("MiniBarCompare", () => {
  it("renders three Vietnamese bar labels", () => {
    const { getByText } = render(<MiniBarCompare yoursSec={8} corpusSec={4} winnerSec={5} />);
    expect(getByText("Của bạn")).toBeTruthy();
    expect(getByText("Ngách TB")).toBeTruthy();
    expect(getByText("Winner")).toBeTruthy();
  });

  it("formats values with a trailing s to one decimal", () => {
    const { getByText } = render(<MiniBarCompare yoursSec={8.2} corpusSec={4} winnerSec={5.5} />);
    expect(getByText("8.2s")).toBeTruthy();
    expect(getByText("4.0s")).toBeTruthy();
    expect(getByText("5.5s")).toBeTruthy();
  });

  it("scales the longest bar to near-max width", () => {
    // max = Math.max(6, 3, 2) * 1.1 = 6.6. Yours (6) → ~91%, just under 100%.
    const { container } = render(<MiniBarCompare yoursSec={6} corpusSec={3} winnerSec={2} />);
    const fills = container.querySelectorAll("div.absolute");
    // First fill corresponds to the "Của bạn" row.
    const yoursWidth = (fills[0] as HTMLElement).style.width;
    expect(yoursWidth).toMatch(/^9[0-9]\.?\d*%$/);
  });

  it("renders all-zero values without crashing", () => {
    const { getAllByText } = render(<MiniBarCompare yoursSec={0} corpusSec={0} winnerSec={0} />);
    // All three bars render "0.0s".
    expect(getAllByText("0.0s").length).toBe(3);
  });
});
