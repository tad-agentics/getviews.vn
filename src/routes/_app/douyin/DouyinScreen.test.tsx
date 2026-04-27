/**
 * D4b (2026-06-04) — Kho Douyin screen integration tests.
 *
 * Targets the §II surface (hero + niche chips + grid). Mocks
 * ``useDouyinFeed`` so tests are deterministic and don't need to
 * patch the network.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { DouyinFeedResponse, DouyinVideo } from "@/lib/api-types";

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "u" }, session: { user: { id: "u" } },
    loading: false, signOut: vi.fn(),
  }),
}));

const useDouyinFeed = vi.fn();
vi.mock("@/hooks/useDouyinFeed", () => ({
  useDouyinFeed: () => useDouyinFeed(),
}));

const { default: DouyinScreen } = await import("./DouyinScreen");


function _video(overrides: Partial<DouyinVideo> = {}): DouyinVideo {
  return {
    video_id: "v1",
    douyin_url: "https://www.douyin.com/video/v1",
    niche_id: 1,
    creator_handle: "alice", creator_name: "Alice",
    thumbnail_url: null, video_url: null, video_duration: 30,
    views: 100_000, likes: 10_000, saves: 5_000,
    engagement_rate: 15, posted_at: null,
    title_zh: "睡前3件事", title_vi: "3 việc trước khi ngủ",
    sub_vi: null, hashtags_zh: [],
    adapt_level: "green", adapt_reason: null,
    eta_weeks_min: null, eta_weeks_max: null, cn_rise_pct: null,
    translator_notes: [], synth_computed_at: null, indexed_at: null,
    ...overrides,
  };
}


function _feed(overrides: Partial<DouyinFeedResponse> = {}): DouyinFeedResponse {
  return {
    niches: [
      { id: 1, slug: "wellness", name_vn: "Wellness", name_zh: "养生", name_en: "Wellness" },
      { id: 2, slug: "tech", name_vn: "Tech", name_zh: "科技", name_en: "Tech" },
    ],
    videos: [
      _video({ video_id: "w1", niche_id: 1, title_vi: "Wellness video 1", adapt_level: "green" }),
      _video({ video_id: "w2", niche_id: 1, title_vi: "Wellness video 2", adapt_level: "yellow" }),
      _video({ video_id: "t1", niche_id: 2, title_vi: "Tech video 1", adapt_level: "green" }),
    ],
    ...overrides,
  };
}


beforeEach(() => {
  window.localStorage.clear();
  useDouyinFeed.mockReset();
});

afterEach(() => {
  window.localStorage.clear();
  cleanup();
});


describe("DouyinScreen — D4b §II surface", () => {
  it("renders the hero kicker + grid + 3 video cards on a populated feed", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Kho Douyin · Đà Việt hoá/)).toBeTruthy();
    expect(screen.getByText(/Trend Douyin/)).toBeTruthy();
    expect(screen.getByText("Wellness video 1")).toBeTruthy();
    expect(screen.getByText("Wellness video 2")).toBeTruthy();
    expect(screen.getByText("Tech video 1")).toBeTruthy();
  });

  it("hero stats reflect the unfiltered pool by default", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    // 3 total videos, 2 green (w1 + t1).
    expect(screen.getByText("Video trong kho")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("Dễ adapt (xanh)")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
    // §II header counter mirrors the visible-grid count.
    expect(screen.getByText(/3 video — đã sub VN/)).toBeTruthy();
  });

  it("filters the grid + hero stats when a niche chip is clicked", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tech" }));
    // Only the Tech video remains.
    expect(screen.queryByText("Wellness video 1")).toBeNull();
    expect(screen.queryByText("Wellness video 2")).toBeNull();
    expect(screen.getByText("Tech video 1")).toBeTruthy();
    // Header counter updates.
    expect(screen.getByText(/1 video — đã sub VN/)).toBeTruthy();
    // Hero scope sub label flips to "ngách <name>".
    expect(screen.getByText(/ngách tech/)).toBeTruthy();
  });

  it("renders the loading state while the feed is pending", () => {
    useDouyinFeed.mockReturnValue({
      data: undefined,
      isPending: true, isError: false, refetch: vi.fn(),
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText(/Đang tải Kho Douyin/)).toBeTruthy();
  });

  it("renders the error state on feed error + retries on click", () => {
    const refetch = vi.fn();
    useDouyinFeed.mockReturnValue({
      data: undefined,
      isPending: false, isError: true, refetch,
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Không tải được/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Thử lại/ }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders the empty state with reset CTA when filter has no matches", () => {
    // Feed has only wellness videos, but user clicks Tech chip → no matches.
    useDouyinFeed.mockReturnValue({
      data: _feed({
        videos: [_video({ video_id: "w1", niche_id: 1, title_vi: "Wellness only" })],
      }),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tech" }));
    expect(screen.getByText(/Không có video nào khớp ngách/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Xem tất cả ngách/ }));
    // Back to all.
    expect(screen.getByText("Wellness only")).toBeTruthy();
  });

  it("renders the empty state without reset CTA when corpus itself is empty", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed({ videos: [] }),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Chưa có video nào/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Xem tất cả ngách/ })).toBeNull();
  });

  it("hero saved count updates when a card save toggle is clicked", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    render(
      <MemoryRouter>
        <DouyinScreen />
      </MemoryRouter>,
    );
    // Hero stat initially 0.
    expect(screen.getByText("Đã lưu")).toBeTruthy();
    // Save the first card.
    const saveButtons = screen.getAllByLabelText(/Lưu vào kho/);
    fireEvent.click(saveButtons[0]!);
    // Read localStorage as the source of truth.
    const stored = JSON.parse(window.localStorage.getItem("gv-douyin-saved") || "[]");
    expect(stored.length).toBe(1);
  });
});
