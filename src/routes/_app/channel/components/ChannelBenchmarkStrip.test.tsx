import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ChannelBenchmarkStrip } from "./ChannelBenchmarkStrip";
import type { ChannelQuickPeek } from "@/hooks/useChannelQuickPeek";

const samplePeek: ChannelQuickPeek = {
  finding_id: null,
  teaser: null,
  median_views: 500,
  dominant_hook: null,
  breakout_video: null,
  findings: [],
  corpus_video_count: 6,
  channel_summary: {
    avg_views: 900,
    engagement_rate_pct: 4.5,
    posts_per_week: 3.2,
  },
  niche_benchmarks: {
    channel_count: 12,
    avg_views_p50: 600,
    avg_views_p75: 1200,
    engagement_p50: 0.03,
    engagement_p75: 0.05,
    posts_per_week_p50: 2,
    posts_per_week_p75: 4,
  },
};

describe("ChannelBenchmarkStrip", () => {
  it("renders three benchmark rows when summary + benchmarks present", () => {
    render(<ChannelBenchmarkStrip data={samplePeek} />);
    expect(screen.getByLabelText(/So sánh kênh với mảng nội dung/i)).toBeTruthy();
    expect(screen.getByText(/Lượt xem trung bình/i)).toBeTruthy();
    expect(screen.getByText(/Tương tác/i)).toBeTruthy();
    expect(screen.getByText(/Tần suất đăng/i)).toBeTruthy();
  });

  it("returns null when benchmarks missing", () => {
    const { container } = render(
      <ChannelBenchmarkStrip
        data={{ ...samplePeek, niche_benchmarks: null }}
      />,
    );
    expect(container.firstChild).toBeNull();
  });
});
