/**
 * D4b (2026-06-04) — Kho Douyin screen integration tests.
 * D4c (2026-06-04) — extended for toolbar (search / adapt / sort /
 *                    saved-only), auto-niche banner, "Xoá bộ lọc".
 *
 * Mocks ``useDouyinFeed`` and ``useProfile`` so tests stay deterministic
 * and don't need the network or Supabase realtime channel.
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

const useDouyinPatterns = vi.fn();
vi.mock("@/hooks/useDouyinPatterns", () => ({
  useDouyinPatterns: () => useDouyinPatterns(),
}));

const useProfile = vi.fn();
vi.mock("@/hooks/useProfile", () => ({
  useProfile: () => useProfile(),
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


function _renderScreen() {
  return render(
    <MemoryRouter>
      <DouyinScreen />
    </MemoryRouter>,
  );
}


beforeEach(() => {
  window.localStorage.clear();
  useDouyinFeed.mockReset();
  useDouyinPatterns.mockReset();
  useProfile.mockReset();
  // Default: no profile (auto-niche banner inactive) + empty patterns.
  useProfile.mockReturnValue({ data: null });
  useDouyinPatterns.mockReturnValue({
    data: { patterns: [] },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  });
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
    _renderScreen();
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
    _renderScreen();
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
    _renderScreen();
    fireEvent.click(screen.getByRole("button", { name: "Tech" }));
    expect(screen.queryByText("Wellness video 1")).toBeNull();
    expect(screen.queryByText("Wellness video 2")).toBeNull();
    expect(screen.getByText("Tech video 1")).toBeTruthy();
    expect(screen.getByText(/1 video — đã sub VN/)).toBeTruthy();
    expect(screen.getByText(/ngách tech/)).toBeTruthy();
  });

  it("renders the loading state while the feed is pending", () => {
    useDouyinFeed.mockReturnValue({
      data: undefined,
      isPending: true, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    expect(screen.getByLabelText(/Đang tải Kho Douyin/)).toBeTruthy();
  });

  it("renders the error state on feed error + retries on click", () => {
    const refetch = vi.fn();
    useDouyinFeed.mockReturnValue({
      data: undefined,
      isPending: false, isError: true, refetch,
    });
    _renderScreen();
    expect(screen.getByText(/Không tải được/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Thử lại/ }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders the empty state with reset CTA when filter has no matches", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed({
        videos: [_video({ video_id: "w1", niche_id: 1, title_vi: "Wellness only" })],
      }),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    fireEvent.click(screen.getByRole("button", { name: "Tech" }));
    expect(screen.getByText(/Không có video nào khớp bộ lọc/)).toBeTruthy();
    // The empty-state CTA is "Xoá bộ lọc"; the §II header link is the
    // same copy — getAllByRole and click the first one.
    const resets = screen.getAllByRole("button", { name: /Xoá bộ lọc/ });
    fireEvent.click(resets[0]!);
    expect(screen.getByText("Wellness only")).toBeTruthy();
  });

  it("renders the empty state without reset CTA when corpus itself is empty", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed({ videos: [] }),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    expect(screen.getByText(/Chưa có video nào/)).toBeTruthy();
    // No filter is active → "Xoá bộ lọc" link / button absent.
    expect(screen.queryByRole("button", { name: /Xoá bộ lọc/ })).toBeNull();
  });

  it("hero saved count updates when a card save toggle is clicked", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    expect(screen.getByText("Đã lưu")).toBeTruthy();
    const saveButtons = screen.getAllByLabelText(/Lưu vào kho/);
    fireEvent.click(saveButtons[0]!);
    const stored = JSON.parse(window.localStorage.getItem("gv-douyin-saved") || "[]");
    expect(stored.length).toBe(1);
  });
});


describe("DouyinScreen — D4c toolbar + auto-niche", () => {
  it("filters the grid via the search input (case-insensitive substring)", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    fireEvent.change(screen.getByLabelText(/Tìm trong Kho Douyin/), {
      target: { value: "TECH" },
    });
    expect(screen.queryByText("Wellness video 1")).toBeNull();
    expect(screen.queryByText("Wellness video 2")).toBeNull();
    expect(screen.getByText("Tech video 1")).toBeTruthy();
    expect(screen.getByText(/1 video — đã sub VN/)).toBeTruthy();
  });

  it("filters the grid via an adapt-level chip and excludes pending rows", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed({
        videos: [
          _video({ video_id: "g1", niche_id: 1, adapt_level: "green", title_vi: "Green only" }),
          _video({ video_id: "y1", niche_id: 1, adapt_level: "yellow", title_vi: "Yellow only" }),
          _video({ video_id: "p1", niche_id: 1, adapt_level: null, title_vi: "Pending only" }),
        ],
      }),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    // The card adapt-chip text is also "XANH" inside an article[role=
    // button], so exact-name match is required to hit the toolbar chip.
    fireEvent.click(screen.getByRole("button", { name: "XANH" }));
    expect(screen.getByText("Green only")).toBeTruthy();
    expect(screen.queryByText("Yellow only")).toBeNull();
    // Pending rows ARE excluded from level chips by design.
    expect(screen.queryByText("Pending only")).toBeNull();
  });

  it("sorts the grid by views DESC when the sort dropdown is changed", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed({
        videos: [
          _video({ video_id: "low", niche_id: 1, views: 100, title_vi: "Low views" }),
          _video({ video_id: "hi", niche_id: 1, views: 5_000_000, title_vi: "High views" }),
          _video({ video_id: "mid", niche_id: 1, views: 50_000, title_vi: "Mid views" }),
        ],
      }),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    fireEvent.change(screen.getByLabelText(/Sắp xếp video/), {
      target: { value: "views" },
    });
    // Read the rendered order: each card has a unique title — query by title text.
    const order = screen
      .getAllByText(/views/)
      .map((el) => el.textContent ?? "")
      .filter((t) => /^(High|Mid|Low) views$/.test(t));
    expect(order).toEqual(["High views", "Mid views", "Low views"]);
  });

  it("narrows to the saved set when Kho cá nhân is toggled on", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    // Save w1.
    const saveButtons = screen.getAllByLabelText(/Lưu vào kho/);
    fireEvent.click(saveButtons[0]!);
    // Toggle saved-only.
    fireEvent.click(screen.getByRole("button", { name: /Kho cá nhân/ }));
    expect(screen.getByText("Wellness video 1")).toBeTruthy();
    expect(screen.queryByText("Wellness video 2")).toBeNull();
    expect(screen.queryByText("Tech video 1")).toBeNull();
  });

  it("shows the Xoá bộ lọc link only when at least one filter is active", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    expect(screen.queryByRole("button", { name: /Xoá bộ lọc/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "XANH" }));
    const resetLink = screen.getByRole("button", { name: /Xoá bộ lọc/ });
    expect(resetLink).toBeTruthy();
    // Click resets back to ALL.
    fireEvent.click(resetLink);
    expect(screen.queryByRole("button", { name: /Xoá bộ lọc/ })).toBeNull();
    expect(screen.getByText(/3 video — đã sub VN/)).toBeTruthy();
  });

  it("auto-applies the user's primary niche when the slug has matches", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    // VN niche 8 = Gym / Fitness VN → maps to "wellness" slug.
    useProfile.mockReturnValue({ data: { primary_niche: 8 } });
    _renderScreen();
    // Banner present — "Wellness" appears both in the niche chip and
    // the banner, so we assert via the banner status role.
    const banner = screen.getByRole("status");
    expect(banner.textContent).toMatch(/Đang ưu tiên ngách/);
    expect(banner.textContent).toMatch(/Wellness/);
    // Grid is scoped to wellness only.
    expect(screen.getByText("Wellness video 1")).toBeTruthy();
    expect(screen.getByText("Wellness video 2")).toBeTruthy();
    expect(screen.queryByText("Tech video 1")).toBeNull();
    // Dismissing the banner clears back to ALL.
    fireEvent.click(screen.getByRole("button", { name: /Bỏ ưu tiên ngách/ }));
    expect(screen.queryByRole("status", { name: /Kho Douyin/ })).toBeNull();
    expect(screen.getByText("Tech video 1")).toBeTruthy();
  });

  it("opens the video modal when a card is clicked + shows the Adapt CTA", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    _renderScreen();
    // No modal mounted yet — the Adapt CTA isn't on the page.
    expect(
      screen.queryByRole("button", { name: /Adapt sang VN → Kịch bản/ }),
    ).toBeNull();
    // Click the first card (article role=button).
    const cards = screen.getAllByRole("button", { name: /Wellness video 1/ });
    fireEvent.click(cards[0]!);
    // Modal opens — Adapt CTA + close X are now in the DOM.
    expect(
      screen.getByRole("button", { name: /Adapt sang VN → Kịch bản/ }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Đóng" })).toBeTruthy();
  });

  it("does not show the auto-niche banner when the primary niche has no Douyin equivalent", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    // VN niche 17 = Gaming → no Douyin slug.
    useProfile.mockReturnValue({ data: { primary_niche: 17 } });
    _renderScreen();
    expect(screen.queryByText(/Đang ưu tiên ngách/)).toBeNull();
    // Grid stays at full corpus.
    expect(screen.getByText(/3 video — đã sub VN/)).toBeTruthy();
  });
});


describe("DouyinScreen — D5e §I patterns surface", () => {
  it("renders the §I header + 3 pattern cards when patterns are returned", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    useDouyinPatterns.mockReturnValue({
      data: {
        patterns: [
          {
            id: "pat-1-1", niche_id: 1, week_of: "2026-06-01", rank: 1,
            name_vn: "Routine 3 bước trước khi ngủ",
            name_zh: null,
            hook_template_vi: "3 việc trước khi ___",
            format_signal_vi: "POV cận cảnh, voiceover thì thầm.",
            sample_video_ids: ["w1", "w2", "w3"],
            cn_rise_pct_avg: 30,
            computed_at: "2026-06-01T21:00:00+00:00",
          },
          {
            id: "pat-1-2", niche_id: 1, week_of: "2026-06-01", rank: 2,
            name_vn: "Tôi đã thử 30 ngày",
            name_zh: null,
            hook_template_vi: "Tôi đã thử ___ trong 30 ngày",
            format_signal_vi: "Before/after split-screen, nhạc upbeat.",
            sample_video_ids: ["w1"],
            cn_rise_pct_avg: null,
            computed_at: "2026-06-01T21:00:00+00:00",
          },
          {
            id: "pat-1-3", niche_id: 1, week_of: "2026-06-01", rank: 3,
            name_vn: "Hỏi đáp wellness",
            name_zh: null,
            hook_template_vi: "Có nên ___ trước khi ngủ không?",
            format_signal_vi: "Talking-head, caption lớn, no music.",
            sample_video_ids: ["w2"],
            cn_rise_pct_avg: 12,
            computed_at: "2026-06-01T21:00:00+00:00",
          },
        ],
      },
      isPending: false,
    });
    _renderScreen();
    expect(screen.getByText(/§ I — Pattern signals/)).toBeTruthy();
    expect(screen.getByText("Routine 3 bước trước khi ngủ")).toBeTruthy();
    expect(screen.getByText("Tôi đã thử 30 ngày")).toBeTruthy();
    expect(screen.getByText("Hỏi đáp wellness")).toBeTruthy();
  });

  it("renders the §I loading state while patterns are pending", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    useDouyinPatterns.mockReturnValue({
      data: undefined, isPending: true,
    });
    _renderScreen();
    expect(screen.getByLabelText(/Đang tải Pattern signals/)).toBeTruthy();
  });

  it("hides the §I section entirely when patterns is empty", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    useDouyinPatterns.mockReturnValue({
      data: { patterns: [] }, isPending: false,
    });
    _renderScreen();
    expect(screen.queryByText(/§ I — Pattern signals/)).toBeNull();
  });

  it("scopes patterns to the active niche chip", () => {
    useDouyinFeed.mockReturnValue({
      data: _feed(),
      isPending: false, isError: false, refetch: vi.fn(),
    });
    useDouyinPatterns.mockReturnValue({
      data: {
        patterns: [
          {
            id: "pat-1-1", niche_id: 1, week_of: "2026-06-01", rank: 1,
            name_vn: "Wellness pattern",
            name_zh: null, hook_template_vi: "___ wellness",
            format_signal_vi: "POV", sample_video_ids: ["w1"],
            cn_rise_pct_avg: null, computed_at: null,
          },
          {
            id: "pat-2-1", niche_id: 2, week_of: "2026-06-01", rank: 1,
            name_vn: "Tech pattern",
            name_zh: null, hook_template_vi: "___ tech",
            format_signal_vi: "Talking-head", sample_video_ids: ["t1"],
            cn_rise_pct_avg: null, computed_at: null,
          },
        ],
      },
      isPending: false,
    });
    _renderScreen();
    // Both visible by default.
    expect(screen.getByText("Wellness pattern")).toBeTruthy();
    expect(screen.getByText("Tech pattern")).toBeTruthy();
    // Click Tech chip.
    fireEvent.click(screen.getByRole("button", { name: "Tech" }));
    expect(screen.queryByText("Wellness pattern")).toBeNull();
    expect(screen.getByText("Tech pattern")).toBeTruthy();
  });
});
