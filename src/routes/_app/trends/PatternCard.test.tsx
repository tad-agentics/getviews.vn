/**
 * PR-T3 Trends — PatternCard render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 570-639.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TopPattern } from "@/hooks/useTopPatterns";
import { PatternCard } from "./PatternCard";

afterEach(() => {
  cleanup();
});

const samplePattern = (overrides: Partial<TopPattern> = {}): TopPattern => ({
  id: "p1",
  display_name: "Sau ___ tháng dùng",
  weekly_instance_count: 12,
  weekly_instance_count_prev: 4,
  instance_count: 47,
  niche_spread: [4],
  avg_views: 142_000,
  sample_hook: "Mình dùng iPad Pro 6 tháng rồi và…",
  videos: [
    { video_id: "v1", thumbnail_url: "https://t/1.jpg", creator_handle: "an.tech", views: 250_000 },
    { video_id: "v2", thumbnail_url: null, creator_handle: "huy.codes", views: 180_000 },
    { video_id: "v3", thumbnail_url: "https://t/3.jpg", creator_handle: "@chinasecrets", views: 90_000 },
    { video_id: "v4", thumbnail_url: null, creator_handle: null, views: 50_000 },
  ],
  ...overrides,
});

describe("PatternCard", () => {
  it("renders the title, sub, and 3-stat strip", () => {
    const { getByText } = render(<PatternCard pattern={samplePattern()} />);
    expect(getByText("Sau ___ tháng dùng")).toBeTruthy();
    expect(getByText(/Mình dùng iPad Pro 6 tháng/)).toBeTruthy();
    expect(getByText("VIDEO")).toBeTruthy();
    expect(getByText("47")).toBeTruthy();
    expect(getByText("VIEW TB")).toBeTruthy();
    // formatViews(142_000) → "142.0K" (always 1 decimal on K/M).
    expect(getByText("142.0K")).toBeTruthy();
    expect(getByText("GIỮ")).toBeTruthy();
  });

  it("renders a quoted sub when sample_hook is present, else em-dash", () => {
    const { getByText, queryAllByText, rerender } = render(
      <PatternCard pattern={samplePattern()} />,
    );
    expect(getByText(/^"Mình dùng iPad Pro/).textContent?.startsWith('"')).toBe(true);
    rerender(<PatternCard pattern={samplePattern({ sample_hook: null })} />);
    // Sub becomes "—" alongside the GIỮ stat cell's "—" — expect ≥ 2.
    expect(queryAllByText("—").length).toBeGreaterThanOrEqual(2);
  });

  it("renders 'Mới · tuần đầu' lifecycle hint when prev=0", () => {
    const { getByText } = render(
      <PatternCard
        pattern={samplePattern({ weekly_instance_count_prev: 0, weekly_instance_count: 8 })}
      />,
    );
    expect(getByText(/Mới · tuần đầu/)).toBeTruthy();
  });

  it("renders 'Đang lên · +X%' lifecycle hint when growth ≥ 1.5×", () => {
    const { getByText } = render(
      <PatternCard
        pattern={samplePattern({ weekly_instance_count_prev: 4, weekly_instance_count: 10 })}
      />,
    );
    expect(getByText(/Đang lên · \+150%/)).toBeTruthy();
  });

  it("invokes onOpen with the pattern when the card is clicked", () => {
    const onOpen = vi.fn();
    const pattern = samplePattern();
    const { getByLabelText } = render(<PatternCard pattern={pattern} onOpen={onOpen} />);
    fireEvent.click(getByLabelText(`Mở pattern: ${pattern.display_name}`));
    expect(onOpen).toHaveBeenCalledWith(pattern);
  });

  it("pads the collage to exactly 4 cells when fewer videos are provided", () => {
    const pattern = samplePattern({ videos: [samplePattern().videos[0]] });
    const { container } = render(<PatternCard pattern={pattern} />);
    const collage = container.querySelector(".grid-cols-2");
    expect(collage?.children.length).toBe(4);
  });

  it("renders 'GIỮ' as em-dash placeholder until BE plumbs retention", () => {
    const { container } = render(<PatternCard pattern={samplePattern()} />);
    // The third Stat cell holds "GIỮ" + value. Find dash there.
    const dashes = Array.from(container.querySelectorAll("p")).filter(
      (p) => p.textContent === "—",
    );
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("normalises @-prefixed creator handles in the collage", () => {
    const pattern = samplePattern({
      videos: [
        { video_id: "v1", thumbnail_url: null, creator_handle: "@chinasecrets", views: 100 },
      ],
    });
    const { container } = render(<PatternCard pattern={pattern} />);
    expect(container.textContent).toContain("@chinasecrets");
  });

  it("auto-prefixes @ on bare creator handles", () => {
    const pattern = samplePattern({
      videos: [
        { video_id: "v1", thumbnail_url: null, creator_handle: "an.tech", views: 100 },
      ],
    });
    const { container } = render(<PatternCard pattern={pattern} />);
    expect(container.textContent).toContain("@an.tech");
  });
});
