/**
 * PR-1 Studio Home — pulse hero render-test.
 *
 * BE source-of-truth: ``_compute_pulse`` in
 * ``cloud-run/getviews_pipeline/channel_analyze.py``.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { ChannelPulse } from "@/lib/api-types";
import { ChannelPulseBlock } from "./ChannelPulseBlock";

afterEach(() => {
  cleanup();
});

const basePulse: ChannelPulse = {
  streak_days: 5,
  streak_window: 14,
  headline: "Tuần qua kênh đang lên — view trung bình ↑ 18% MoM so với tháng trước.",
  headline_kind: "win",
  mom_delta: "↑ 18% MoM",
  avg_views: 12_500,
};

describe("ChannelPulseBlock", () => {
  it("renders the headline + STREAK kicker when streak ≥ 1", () => {
    const { getByText } = render(<ChannelPulseBlock pulse={basePulse} />);
    expect(getByText(/STREAK 5\/14 NGÀY/)).toBeTruthy();
    expect(getByText(/Tuần qua kênh đang lên/)).toBeTruthy();
  });

  it("falls back to a 'PULSE KÊNH' kicker when streak is 0", () => {
    const { getByText, queryByText } = render(
      <ChannelPulseBlock pulse={{ ...basePulse, streak_days: 0 }} />,
    );
    expect(getByText(/PULSE KÊNH/)).toBeTruthy();
    expect(queryByText(/STREAK/)).toBeNull();
  });

  it("returns null (no markup) when the headline is empty", () => {
    const { container } = render(
      <ChannelPulseBlock pulse={{ ...basePulse, headline: "" }} />,
    );
    expect(container.querySelector("section")).toBeNull();
  });

  it("uses the concern tone class for headline_kind=concern", () => {
    const { getByText } = render(
      <ChannelPulseBlock
        pulse={{
          ...basePulse,
          headline_kind: "concern",
          headline: "Tuần qua kênh đang chùng — view trung bình ↓ 22% MoM.",
        }}
      />,
    );
    const kicker = getByText(/STREAK 5\/14 NGÀY/);
    expect(kicker.className).toMatch(/gv-neg-deep/);
  });

  it("uses the win tone class for headline_kind=win", () => {
    const { getByText } = render(<ChannelPulseBlock pulse={basePulse} />);
    const kicker = getByText(/STREAK 5\/14 NGÀY/);
    expect(kicker.className).toMatch(/gv-pos-deep/);
  });
});
