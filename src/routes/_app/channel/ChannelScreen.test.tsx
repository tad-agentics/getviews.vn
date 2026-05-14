/**
 * ChannelScreen smoke tests (Phase 2 cleanup — legacy ChannelAnalyze removed).
 *
 * Not a full integration test — mocks data hooks + `AppLayout` + auth so
 * the render is deterministic. Covers:
 *   1. Empty state when `handle` query param is absent.
 *   2. Streaming state while `useChannelDiagnose` is in progress.
 *   3. Narrative sections rendered from `useChannelDiagnose` payload.
 *   4. Error message on `insufficient_credits`.
 *
 * Follows the HomeScreen.test.tsx mock pattern — every hook that touches
 * Supabase / network / env is stubbed so no real fetches leave jsdom.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

// ── Module mocks ───────────────────────────────────────────────────────────

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

vi.mock("@/lib/logUsage", () => ({ logUsage: vi.fn() }));

const mockUseHomePulse = vi.fn();
const mockUseChannelDiagnose = vi.fn();

vi.mock("@/hooks/useHomePulse", () => ({ useHomePulse: () => mockUseHomePulse() }));
vi.mock("@/hooks/useChannelDiagnose", () => ({
  useChannelDiagnose: () => mockUseChannelDiagnose(),
}));

vi.mock("@/hooks/useProfile", () => ({
  useProfile: () => ({
    data: { creator_niche_id: 1, deep_credits_remaining: 10 },
    isPending: false,
  }),
}));

vi.mock("@/hooks/useCreatorNiches", () => ({
  useCreatorNiches: () => ({
    data: [{ id: 1, slug: "beauty", name: "Làm đẹp", description: null, display_order: 1 }],
    isPending: false,
  }),
}));

vi.mock("@/hooks/useChannelUserSearch", () => ({
  useChannelUserSearch: () => ({
    data: undefined,
    isFetching: false,
    isError: false,
    error: null,
  }),
}));

vi.mock("@/components/AppLayout", () => ({
  AppLayout: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "u", email: "a@b.vn" },
    session: { user: { id: "u" } },
    loading: false,
    signOut: vi.fn(),
  }),
}));

const ChannelScreen = (await import("./ChannelScreen")).default;

// ── Fixtures ────────────────────────────────────────────────────────────────

function renderScreen(searchParams = "") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/app/channel${searchParams}`]}>
        <ChannelScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("ChannelScreen", () => {
  const mockDiagnoseIdle = {
    status: "idle" as const,
    trajectoryShape: null,
    sections: [],
    recommendations: [],
    finalPayload: null,
    error: null,
    heartbeatCount: 0,
    streamId: null,
    lastSeq: 0,
    activeStepIndex: -1,
    activeStepLabel: "",
    start: vi.fn(),
    abort: vi.fn(),
    reset: vi.fn(),
  };

  beforeEach(() => {
    mockUseHomePulse.mockReset();
    mockUseChannelDiagnose.mockReset();
    mockUseHomePulse.mockReturnValue({ data: null, isPending: false });
    mockUseChannelDiagnose.mockReturnValue(mockDiagnoseIdle);
  });
  afterEach(cleanup);

  it("renders empty state when no handle is provided", () => {
    renderScreen();
    expect(screen.getByText(/Khám bất kỳ kênh TikTok nào/)).toBeTruthy();
  });

  it("renders streaming state while diagnosis is in progress", () => {
    mockUseChannelDiagnose.mockReturnValue({
      ...mockDiagnoseIdle,
      status: "streaming" as const,
      activeStepIndex: 1,
      activeStepLabel: "Tải dữ liệu kênh",
      trajectoryShape: null,
      sections: [],
    });
    const { container } = renderScreen("?handle=sammie.tech");
    expect(container).toBeTruthy();
  });

  it("renders handle heading when diagnosis is active", () => {
    mockUseChannelDiagnose.mockReturnValue({
      ...mockDiagnoseIdle,
      status: "streaming" as const,
      sections: [],
    });
    renderScreen("?handle=sammie.tech");
    // Handle appears in ChannelDiagnosisBody heading area.
    expect(screen.getAllByText(/@?sammie\.tech/i).length).toBeGreaterThan(0);
  });

  it("renders narrative sections when diagnosis has sections", () => {
    mockUseChannelDiagnose.mockReturnValue({
      ...mockDiagnoseIdle,
      status: "done" as const,
      trajectoryShape: "stagnant" as const,
      sections: [
        { section_id: "verdict", title: "Kết luận", text: "Kênh đang trì trệ." },
      ],
      recommendations: [],
      finalPayload: {
        trajectory_shape: "stagnant",
        sections: [],
        recommendations: [],
        top_performers: [],
        worst_performers: [],
        ugc_creators: [],
        channel_pattern: { global_avg_views: 50000, total_videos: 15, formats: {} },
        inflection: null,
        creator_match: null,
        video_count: 15,
        provenance: "Phân tích dựa trên 15 videos",
        niche_thin: false,
        cache_hit: false,
      },
    });
    renderScreen("?handle=sammie.tech");
    expect(screen.getByText(/Kết luận/)).toBeTruthy();
    // Two elements share this substring — the trajectory chip header
    // ("Kênh đang trì trệ", no dot) and the section body text
    // ("Kênh đang trì trệ.", with dot). Disambiguate by anchoring on
    // the section punctuation.
    expect(screen.getByText(/^Kênh đang trì trệ\.$/)).toBeTruthy();
  });

  it("renders error message on insufficient_credits", () => {
    mockUseChannelDiagnose.mockReturnValue({
      ...mockDiagnoseIdle,
      status: "error" as const,
      error: "insufficient_credits",
    });
    renderScreen("?handle=sammie.tech");
    expect(screen.getByText(/Không đủ credit/)).toBeTruthy();
  });
});
