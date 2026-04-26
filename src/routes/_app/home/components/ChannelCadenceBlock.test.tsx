/**
 * PR-3 Studio Home — ChannelCadenceBlock render-test.
 *
 * BE source-of-truth:
 * ``cloud-run/getviews_pipeline/channel_analyze.py::_compute_cadence_struct``.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ChannelCadence } from "@/lib/api-types";
import { ChannelCadenceBlock } from "./ChannelCadenceBlock";

afterEach(() => {
  cleanup();
});

const baseCadence: ChannelCadence = {
  posts_14d: [
    false, true, true, false, false, true, false, // 7 cells (weeks ago)
    true, false, true, true, false, true, true,    // 7 cells (last week)
  ],
  weekly_actual: 5,
  weekly_target: 5,
  best_hour: "20:00–22:00",
  best_days: "T7, CN",
};

describe("ChannelCadenceBlock", () => {
  it("renders 14 cells in the calendar grid", () => {
    const { getByRole } = render(<ChannelCadenceBlock cadence={baseCadence} />);
    const grid = getByRole("img");
    // The grid is the only role=img element; cells are span children.
    expect(grid.children.length).toBe(14);
  });

  it("uses ink fill for posted days and rule fill for skipped days", () => {
    const { getByRole } = render(<ChannelCadenceBlock cadence={baseCadence} />);
    const grid = getByRole("img");
    // Cell index 0 = false (skipped), index 1 = true (posted).
    expect((grid.children[0] as HTMLElement).className).toMatch(/gv-rule/);
    expect((grid.children[1] as HTMLElement).className).toMatch(/gv-ink\b/);
  });

  it("highlights today (last cell) with the accent outline", () => {
    const { getByRole } = render(<ChannelCadenceBlock cadence={baseCadence} />);
    const grid = getByRole("img");
    const todayCell = grid.children[grid.children.length - 1] as HTMLElement;
    expect(todayCell.className).toMatch(/outline-\[color:var\(--gv-accent\)\]/);
  });

  it("renders both GIỜ VÀNG and NGÀY VÀNG sub-blocks", () => {
    const { getByText } = render(<ChannelCadenceBlock cadence={baseCadence} />);
    expect(getByText("GIỜ VÀNG")).toBeTruthy();
    expect(getByText("20:00–22:00")).toBeTruthy();
    expect(getByText("NGÀY VÀNG")).toBeTruthy();
    expect(getByText("T7, CN")).toBeTruthy();
  });

  it("hides the NGÀY VÀNG sub-block when best_days is empty", () => {
    const { queryByText } = render(
      <ChannelCadenceBlock cadence={{ ...baseCadence, best_days: "" }} />,
    );
    expect(queryByText("NGÀY VÀNG")).toBeNull();
  });

  it("hides both sub-blocks when neither best_hour nor best_days is set", () => {
    const { queryByText } = render(
      <ChannelCadenceBlock
        cadence={{ ...baseCadence, best_hour: "", best_days: "" }}
      />,
    );
    expect(queryByText("GIỜ VÀNG")).toBeNull();
    expect(queryByText("NGÀY VÀNG")).toBeNull();
  });

  it("pads short posts_14d arrays to 14 cells defensively", () => {
    const short: ChannelCadence = {
      ...baseCadence,
      posts_14d: [true, true, false], // only 3 cells
    };
    const { getByRole } = render(<ChannelCadenceBlock cadence={short} />);
    expect(getByRole("img").children.length).toBe(14);
  });
});
