/**
 * PR-T4 Trends — PatternModal render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 652-946.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { TopPattern } from "@/hooks/useTopPatterns";
import { PatternModal } from "./PatternModal";

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
  ],
  ...overrides,
});

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("PatternModal — closed state", () => {
  it("renders nothing when open=false", () => {
    const { queryByText } = wrap(
      <PatternModal pattern={samplePattern()} open={false} onOpenChange={() => {}} />,
    );
    expect(queryByText("Sau ___ tháng dùng")).toBeNull();
  });

  it("renders nothing when pattern is null", () => {
    const { queryByText } = wrap(
      <PatternModal pattern={null} open onOpenChange={() => {}} />,
    );
    expect(queryByText("PATTERN ·")).toBeNull();
  });
});

describe("PatternModal — open state", () => {
  it("renders the header kicker, title, and sample-hook description", () => {
    const { getByText, getAllByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    expect(getByText(/PATTERN · 47 VIDEO · 142\.0K VIEW TB/)).toBeTruthy();
    expect(getByText("Sau ___ tháng dùng")).toBeTruthy();
    // Sample hook appears in the description AND inside the takeaway —
    // expect ≥ 1.
    expect(getAllByText(/Mình dùng iPad Pro 6 tháng/).length).toBeGreaterThan(0);
  });

  it("renders the takeaway / structure / gap-angles stub blocks", () => {
    const { getByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    expect(getByText("Ý CHÍNH")).toBeTruthy();
    expect(getByText("CẤU TRÚC ĐIỂN HÌNH")).toBeTruthy();
    expect(getByText("GÓC CÒN TRỐNG")).toBeTruthy();
    // Stub copy explicitly says these sections are coming.
    expect(getByText(/biên tập đang tổng hợp/)).toBeTruthy();
  });

  it("renders the sample switcher when ≥ 2 videos are available", () => {
    const { getByText, getAllByLabelText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    expect(getByText(/CHUYỂN VIDEO \(1\/3\)/)).toBeTruthy();
    expect(getAllByLabelText(/Mẫu \d+/).length).toBe(3);
  });

  it("hides the sample switcher when only one video is present", () => {
    const onePattern = samplePattern({
      videos: [samplePattern().videos[0]],
    });
    const { queryByText } = wrap(
      <PatternModal pattern={onePattern} open onOpenChange={() => {}} />,
    );
    expect(queryByText(/CHUYỂN VIDEO/)).toBeNull();
  });

  it("clicking a sample thumbnail switches the active video", () => {
    const { getByLabelText, getAllByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    const initialHandles = getAllByText(/^@an\.tech$/);
    expect(initialHandles.length).toBeGreaterThan(0);
    fireEvent.click(getByLabelText("Mẫu 2"));
    // After switch, the phone tile shows huy.codes.
    expect(getAllByText(/^@huy\.codes$/).length).toBeGreaterThan(0);
  });

  it("close button calls onOpenChange(false)", () => {
    const onChange = vi.fn();
    const { getByLabelText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={onChange} />,
    );
    fireEvent.click(getByLabelText("Đóng"));
    expect(onChange).toHaveBeenCalledWith(false);
  });

  it("renders a 'no video' fallback when pattern has zero videos", () => {
    const empty = samplePattern({ videos: [] });
    const { getByText } = wrap(
      <PatternModal pattern={empty} open onOpenChange={() => {}} />,
    );
    expect(getByText(/Chưa có video mẫu/)).toBeTruthy();
  });

  it("normalises bare creator handles with leading @ in the phone tile", () => {
    const { getByText } = wrap(
      <PatternModal pattern={samplePattern()} open onOpenChange={() => {}} />,
    );
    // First video has bare "an.tech" — renders with @ prefix.
    expect(getByText("@an.tech")).toBeTruthy();
  });
});
