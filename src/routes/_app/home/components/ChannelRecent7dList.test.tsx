/**
 * PR-1 Studio Home — recent-7d ranked verdict list render-test.
 *
 * BE source-of-truth: ``_build_recent_7d`` in
 * ``cloud-run/getviews_pipeline/channel_analyze.py``.
 */
import { cleanup, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import type { ChannelRecent7dEntry } from "@/lib/api-types";
import { ChannelRecent7dList } from "./ChannelRecent7dList";

afterEach(() => {
  cleanup();
});

const winRow: ChannelRecent7dEntry = {
  video_id: "win",
  title: "5 app AI mà chưa ai nói",
  thumbnail_url: null,
  hook_category: "POV",
  posted_at: "2026-04-26T08:00:00Z",
  age_label: "3 giờ trước",
  views: 50_000,
  vs_median: 5,
  verdict: "WIN",
  verdict_note: "Vượt mức trung bình kênh — hook đang chạm đúng audience.",
};

const avgRow: ChannelRecent7dEntry = {
  ...winRow,
  video_id: "avg",
  title: "Recap tuần qua",
  vs_median: 1,
  verdict: "AVG",
  verdict_note: "Sát trung bình kênh — pattern quen thuộc, chưa có yếu tố đặc biệt.",
};

const underRow: ChannelRecent7dEntry = {
  ...winRow,
  video_id: "under",
  title: "Mở app này thử xem",
  vs_median: 0.4,
  verdict: "UNDER",
  verdict_note: "Dưới mức trung bình — hook chưa đủ mạnh để giữ scroll.",
};

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("ChannelRecent7dList", () => {
  it("renders a stub when rows is empty", () => {
    const { getByText } = wrap(<ChannelRecent7dList rows={[]} />);
    expect(getByText(/Chưa có video mới trong 7 ngày qua/)).toBeTruthy();
  });

  it("renders title, vs_median multiplier, verdict label, and note for each row", () => {
    const { getByText, getAllByText } = wrap(
      <ChannelRecent7dList rows={[winRow, avgRow, underRow]} />,
    );
    expect(getByText(/5 app AI mà chưa ai nói/)).toBeTruthy();
    expect(getByText(/5,0×/)).toBeTruthy();
    expect(getByText(/0,4×/)).toBeTruthy();
    expect(getByText(/1,0×/)).toBeTruthy();
    expect(getAllByText(/WIN/).length).toBeGreaterThan(0);
    expect(getAllByText(/UNDER/).length).toBeGreaterThan(0);
    expect(getAllByText(/AVG/).length).toBeGreaterThan(0);
  });

  it("uses the WIN tone (gv-pos-deep) on the multiplier for vs_median ≥ 1.5", () => {
    const { getByText } = wrap(<ChannelRecent7dList rows={[winRow]} />);
    const multiplier = getByText(/5,0×/);
    expect(multiplier.className).toMatch(/gv-pos-deep/);
  });

  it("uses the UNDER tone (gv-neg-deep) on the multiplier for vs_median < 0.7", () => {
    const { getByText } = wrap(<ChannelRecent7dList rows={[underRow]} />);
    const multiplier = getByText(/0,4×/);
    expect(multiplier.className).toMatch(/gv-neg-deep/);
  });

  it("renders large multipliers (≥10×) without decimals", () => {
    const huge: ChannelRecent7dEntry = { ...winRow, vs_median: 12.7 };
    const { getByText } = wrap(<ChannelRecent7dList rows={[huge]} />);
    expect(getByText(/13×/)).toBeTruthy();
  });

  it("hides the hook category fragment when hook_category is null", () => {
    const noHook: ChannelRecent7dEntry = { ...winRow, hook_category: null };
    const { queryByText } = wrap(<ChannelRecent7dList rows={[noHook]} />);
    expect(queryByText(/Hook:/)).toBeNull();
  });
});
