/**
 * PR-T6 Trends — TrendsRail render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 432-446.
 */
import { cleanup, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { RailVideo, TrendsRailVideos } from "@/hooks/useTrendsRailVideos";

const mockUseTrendsRailVideos = vi.fn();
vi.mock("@/hooks/useTrendsRailVideos", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useTrendsRailVideos")>(
    "@/hooks/useTrendsRailVideos",
  );
  return {
    ...actual,
    useTrendsRailVideos: (...args: unknown[]) => mockUseTrendsRailVideos(...args),
  };
});

const { TrendsRail } = await import("./TrendsRail");

beforeEach(() => {
  mockUseTrendsRailVideos.mockReset();
});

afterEach(() => {
  cleanup();
});

const sampleVideo = (overrides: Partial<RailVideo> = {}): RailVideo => ({
  video_id: "v1",
  thumbnail_url: "https://t/1.jpg",
  creator_handle: "an.tech",
  views: 250_000,
  posted_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
  hook_phrase: "Mình vừa test iPad Pro",
  ...overrides,
});

const samplePayload = (overrides: Partial<TrendsRailVideos> = {}): TrendsRailVideos => ({
  breakouts7d: [
    sampleVideo({ video_id: "b1", hook_phrase: "Breakout one" }),
    sampleVideo({ video_id: "b2", hook_phrase: "Breakout two" }),
  ],
  virals: [
    sampleVideo({ video_id: "v1", hook_phrase: "Viral one" }),
    sampleVideo({ video_id: "v2", hook_phrase: "Viral two" }),
  ],
  ...overrides,
});

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("TrendsRail", () => {
  it("renders nothing when nicheId is null", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: undefined, isPending: false });
    const { container } = wrap(<TrendsRail nicheId={null} />);
    expect(container.querySelector("section")).toBeNull();
  });

  it("renders both section headers + sub-lines per design", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: samplePayload(), isPending: false });
    const { getByText } = wrap(<TrendsRail nicheId={4} />);
    expect(getByText("VIDEO NÊN THAM KHẢO")).toBeTruthy();
    expect(getByText("Đang nổi lên")).toBeTruthy();
    expect(getByText("Top 5 view 7 ngày qua")).toBeTruthy();
    expect(getByText("VIDEO LEO ĐỈNH")).toBeTruthy();
    expect(getByText("Đang Viral")).toBeTruthy();
    expect(getByText("Top 5 Viral Video trong ngách của bạn")).toBeTruthy();
  });

  it("renders one row per video with hook phrase as the title", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: samplePayload(), isPending: false });
    const { getByText } = wrap(<TrendsRail nicheId={4} />);
    expect(getByText("Breakout one")).toBeTruthy();
    expect(getByText("Breakout two")).toBeTruthy();
    expect(getByText("Viral one")).toBeTruthy();
    expect(getByText("Viral two")).toBeTruthy();
  });

  it("renders skeletons in both sections while pending", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: undefined, isPending: true });
    const { container } = wrap(<TrendsRail nicheId={4} />);
    expect(container.querySelectorAll(".animate-pulse").length).toBe(6);
  });

  it("renders empty stub when both sections are empty arrays", () => {
    mockUseTrendsRailVideos.mockReturnValue({
      data: { breakouts7d: [], virals: [] },
      isPending: false,
    });
    const { getByText } = wrap(<TrendsRail nicheId={4} />);
    expect(getByText(/Chưa đủ dữ liệu/)).toBeTruthy();
    expect(getByText(/Chưa có video trong corpus/)).toBeTruthy();
  });

  it("normalises bare creator handles with leading @ in the row caption", () => {
    mockUseTrendsRailVideos.mockReturnValue({
      data: {
        breakouts7d: [sampleVideo({ creator_handle: "an.tech" })],
        virals: [],
      },
      isPending: false,
    });
    const { container } = wrap(<TrendsRail nicheId={4} />);
    expect(container.textContent).toContain("@an.tech");
  });

  it("falls back to 'Video' when hook_phrase is missing", () => {
    mockUseTrendsRailVideos.mockReturnValue({
      data: {
        breakouts7d: [sampleVideo({ hook_phrase: null })],
        virals: [],
      },
      isPending: false,
    });
    const { getByText } = wrap(<TrendsRail nicheId={4} />);
    expect(getByText("Video")).toBeTruthy();
  });
});
