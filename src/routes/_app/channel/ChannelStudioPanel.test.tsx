/**
 * ChannelStudioPanel smoke tests — Studio-embedded channel analysis (§6).
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

vi.mock("@/lib/logUsage", () => ({ logUsage: vi.fn() }));

const mockUseChannelDiagnose = vi.fn();
vi.mock("@/hooks/useChannelDiagnose", () => ({
  useChannelDiagnose: () => mockUseChannelDiagnose(),
}));

const mockUseChannelQuickPeek = vi.fn();
vi.mock("@/hooks/useChannelQuickPeek", () => ({
  useChannelQuickPeek: (...args: unknown[]) => mockUseChannelQuickPeek(...args),
}));

const mockUseProfile = vi.fn();
vi.mock("@/hooks/useProfile", () => ({
  useProfile: () => mockUseProfile(),
}));

vi.mock("@/hooks/useCreatorNiches", () => ({
  useCreatorNiches: () => ({
    data: [{ id: 1, slug: "beauty", name: "Làm đẹp", description: null, display_order: 1 }],
    isPending: false,
  }),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    user: { id: "u", email: "a@b.vn" },
    session: { user: { id: "u" } },
    loading: false,
    signOut: vi.fn(),
  }),
}));

import { ChannelStudioPanel } from "./components/ChannelStudioPanel";
import type { ChannelDiagnoseState } from "@/hooks/useChannelDiagnose";

function renderPanel(searchParams = "", defaultHandle?: string | null) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/app/channel${searchParams}`]}>
        <ChannelStudioPanel defaultHandle={defaultHandle ?? null} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ChannelStudioPanel", () => {
  const mockDiagnoseIdle = {
    status: "idle" as const,
    trajectoryShape: null,
    sections: [],
    recommendations: [],
    scoreCard: null,
    channelFindings: [],
    channelPersona: null,
    peerSource: null as ChannelDiagnoseState["peerSource"],
    finalPayload: null,
    error: null,
    heartbeatCount: 0,
    streamId: null,
    lastSeq: 0,
    activeStepIndex: -1,
    activeStepLabel: "",
    activeSectionId: null,
    start: vi.fn(),
    abort: vi.fn(),
    reset: vi.fn(),
  };

  beforeEach(() => {
    mockUseChannelDiagnose.mockReset();
    mockUseChannelQuickPeek.mockReset();
    mockUseProfile.mockReset();
    mockUseProfile.mockReturnValue({
      data: { creator_niche_id: 1, credits_remaining: 10, tiktok_handle: null },
      isPending: false,
    });
    mockUseChannelDiagnose.mockReturnValue(mockDiagnoseIdle);
    mockUseChannelQuickPeek.mockReturnValue({
      data: {
        finding_id: "channel_view_ceiling_300",
        teaser: "Có dấu hiệu trần view.",
        median_views: 1200,
        dominant_hook: "bold_claim",
        breakout_video: { video_id: "123", views: 5000 },
        findings: [{ finding_id: "channel_view_ceiling_300", teaser: "Có dấu hiệu trần view.", strength: "high" }],
        corpus_video_count: 12,
        channel_summary: {
          avg_views: 1200,
          engagement_rate_pct: 4.2,
          posts_per_week: 3.5,
        },
        niche_benchmarks: {
          channel_count: 10,
          avg_views_p50: 800,
          avg_views_p75: 1500,
          engagement_p50: 0.03,
          engagement_p75: 0.05,
          posts_per_week_p50: 2,
          posts_per_week_p75: 4,
        },
      },
      isLoading: false,
      isError: false,
    });
  });
  afterEach(cleanup);

  it("renders handle input when no handle is set", () => {
    renderPanel();
    expect(screen.getByLabelText(/Handle hoặc URL kênh TikTok/)).toBeTruthy();
  });

  it("renders Cơ bản panel by default when handle is set", () => {
    renderPanel("?handle=sammie.tech");
    expect(screen.getByText(/Soi kênh · Cơ bản/)).toBeTruthy();
    expect(screen.getByText(/trần view/)).toBeTruthy();
  });

  it("uses profile default handle when query param absent", () => {
    renderPanel("", "mychannel");
    expect(screen.getByText(/Soi kênh · Cơ bản/)).toBeTruthy();
  });

  it("shows upsell when deep-linked to Chuyên sâu without enough credits", () => {
    mockUseProfile.mockReturnValue({
      data: { creator_niche_id: 1, credits_remaining: 1, tiktok_handle: null },
      isPending: false,
    });
    renderPanel("?handle=sammie.tech&depth=deep");
    expect(screen.getByText(/Cần 3 credit để chạy Chuyên sâu/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Chuyển Cơ bản/i })).toBeTruthy();
  });

  it("allows handle submit when Chuyên sâu selected but credits are low", () => {
    mockUseProfile.mockReturnValue({
      data: { creator_niche_id: 1, credits_remaining: 1, tiktok_handle: null },
      isPending: false,
    });
    renderPanel("?depth=deep");
    fireEvent.change(screen.getByLabelText(/Handle hoặc URL kênh TikTok/), {
      target: { value: "@creator" },
    });
    const submit = screen.getByRole("button", { name: /Phân tích/i }) as HTMLButtonElement;
    expect(submit.disabled).toBe(false);
  });

  it("renders narrative sections when diagnosis has sections", () => {
    mockUseChannelDiagnose.mockReturnValue({
      ...mockDiagnoseIdle,
      status: "done" as const,
      trajectoryShape: "stagnant" as const,
      sections: [{ section_id: "verdict", title: "Kết luận", text: "Kênh đang trì trệ." }],
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
        cache_hit: false,
      },
    });
    renderPanel("?handle=sammie.tech&depth=deep");
    expect(screen.getByText(/Kết luận/)).toBeTruthy();
  });
});
