/**
 * Trends — PatternCard render-test.
 *
 * L2.2 Sprint 5 reshape — card surfaces the deck-synthesized formula
 * (``structure[0]`` Hook line + ``why``) plus within-niche lift +
 * verb CTA. The bucket ``display_name`` is no longer the headline.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TopPattern } from "@/hooks/useTopPatterns";
import { PatternCard } from "./PatternCard";

afterEach(() => {
  cleanup();
});

const sampleVideos: TopPattern["videos"] = [
  {
    video_id: "v1",
    thumbnail_url: "https://t/1.jpg",
    creator_handle: "an.tech",
    views: 250_000,
    tiktok_url: null,
  },
  {
    video_id: "v2",
    thumbnail_url: null,
    creator_handle: "huy.codes",
    views: 180_000,
    tiktok_url: null,
  },
  {
    video_id: "v3",
    thumbnail_url: "https://t/3.jpg",
    creator_handle: "@chinasecrets",
    views: 90_000,
    tiktok_url: null,
  },
];

const samplePattern = (overrides: Partial<TopPattern> = {}): TopPattern => ({
  id: "p1",
  display_name: "Sau ___ tháng dùng",   // bucket label — should NOT be the headline
  weekly_instance_count: 12,
  weekly_instance_count_prev: 4,
  niche_video_count: 6,
  instance_count: 47,
  niche_spread: [4],
  avg_views: 142_000,
  lift_vs_niche: 2.4,
  sample_hook: "Mình dùng iPad Pro 6 tháng rồi và…",
  videos: sampleVideos,
  structure: [
    "Mở: câu hỏi cá nhân (0-2s)",
    "Setup: bối cảnh dùng sản phẩm (2-6s)",
    "Body: 3 chi tiết bất ngờ (6-22s)",
    "Payoff: so sánh + CTA (22-30s)",
  ],
  why: "Câu hỏi cá nhân tạo curiosity_gap, viewer cần lý do để xem hết.",
  careful: "Đừng kể lể quá dài — dưới 4 chi tiết là an toàn.",
  angles: null,
  ...overrides,
});

describe("PatternCard", () => {
  it("uses structure[0] (Hook line) as the headline, not the bucket display_name", () => {
    const { getByText, queryByText } = render(<PatternCard pattern={samplePattern()} />);
    // The "Mở:" prefix is stripped — the recipe line reads cleaner without it.
    expect(getByText(/câu hỏi cá nhân \(0-2s\)/)).toBeTruthy();
    // Bucket name must NOT appear on the card surface.
    expect(queryByText("Sau ___ tháng dùng")).toBeNull();
  });

  it("renders the ``why`` line under the headline when deck synth has produced one", () => {
    const { getByText } = render(<PatternCard pattern={samplePattern()} />);
    expect(getByText(/Câu hỏi cá nhân tạo curiosity_gap/)).toBeTruthy();
  });

  it("falls back to display_name + sample_hook when no deck has been synthesized", () => {
    // Defensive path — the hook filters un-decked patterns out, but the
    // component shouldn't crash if one slips through.
    const { getByText } = render(
      <PatternCard
        pattern={samplePattern({ structure: null, why: null })}
      />,
    );
    expect(getByText("Sau ___ tháng dùng")).toBeTruthy();
    expect(getByText(/Mình dùng iPad Pro/)).toBeTruthy();
  });

  it("renders the within-niche lift badge and niche video count", () => {
    const { getByText } = render(<PatternCard pattern={samplePattern()} />);
    expect(getByText(/↑ 2\.4× ngách/)).toBeTruthy();
    expect(getByText("6 video trong ngách")).toBeTruthy();
  });

  it("hides the lift badge when lift_vs_niche is null (corpus too thin to compute median)", () => {
    const { queryByText, getByText } = render(
      <PatternCard pattern={samplePattern({ lift_vs_niche: null })} />,
    );
    expect(queryByText(/× ngách/)).toBeNull();
    // The niche count still shows so creators retain the credibility signal.
    expect(getByText("6 video trong ngách")).toBeTruthy();
  });

  it("formats high lift values as integers (no .0× clutter)", () => {
    const { getByText } = render(
      <PatternCard pattern={samplePattern({ lift_vs_niche: 4.6 })} />,
    );
    expect(getByText(/↑ 5× ngách/)).toBeTruthy();
  });

  it("shows the verb-CTA so creators know clicking will teach the formula", () => {
    const { getByText } = render(<PatternCard pattern={samplePattern()} />);
    expect(getByText(/HỌC CÔNG THỨC/)).toBeTruthy();
  });

  it("invokes onOpen with the pattern when the card is clicked", () => {
    const onOpen = vi.fn();
    const pattern = samplePattern();
    const { getByLabelText } = render(<PatternCard pattern={pattern} onOpen={onOpen} />);
    // aria-label uses the headline (formula identity), not the bucket name.
    fireEvent.click(getByLabelText(/Mở công thức:/));
    expect(onOpen).toHaveBeenCalledWith(pattern);
  });

  it("renders only the videos provided — no padded empty placeholder cells", () => {
    // Sprint 5 — at low niche_video_count the old 2×2 padCollage filled with
    // grey placeholder tiles, making the card look broken. Now we render a
    // flex strip with only the videos that actually exist.
    const onlyOne = samplePattern({ videos: [sampleVideos[0]!] });
    const { container } = render(<PatternCard pattern={onlyOne} />);
    // No 2-col grid exists anymore — the strip uses flex and contains exactly
    // one tile when only one video is provided.
    expect(container.querySelector(".grid-cols-2")).toBeNull();
    const tiles = container.querySelectorAll('[aria-hidden="true"] > .relative');
    expect(tiles.length).toBe(1);
  });

  it("renders a 'Chưa có video mẫu' placeholder when the videos array is empty", () => {
    const empty = samplePattern({ videos: [] });
    const { getByText } = render(<PatternCard pattern={empty} />);
    expect(getByText(/Chưa có video mẫu/)).toBeTruthy();
  });

  it("normalises @-prefixed creator handles and auto-prefixes bare ones in collage", () => {
    const pattern = samplePattern({
      videos: [
        { video_id: "a", thumbnail_url: null, creator_handle: "@chinasecrets", views: 100, tiktok_url: null },
        { video_id: "b", thumbnail_url: null, creator_handle: "an.tech", views: 200, tiktok_url: null },
      ],
    });
    const { container } = render(<PatternCard pattern={pattern} />);
    expect(container.textContent).toContain("@chinasecrets");
    expect(container.textContent).toContain("@an.tech");
  });
});
