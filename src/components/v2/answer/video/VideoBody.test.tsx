/**
 * VideoBody — render-shape regression for the video diagnosis report
 * inside an answer-session container.
 *
 * The body is a 1:1 lift of VideoScreen's render tree (per the user's
 * "use the current flop/win design template" constraint). These tests
 * pin a thin slice — the win/flop branch + the headline render — so
 * future drift between this body and the dedicated /app/video screen
 * surfaces fast. PR-3 will delete VideoScreen entirely; once that
 * lands, this becomes the only surface for the report and these
 * tests guard it directly.
 */
import React from "react";
import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type { VideoReportPayload } from "@/lib/api-types";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
  },
}));

vi.mock("@/lib/logUsage", () => ({ logUsage: vi.fn() }));

// Stub heavy children — we're testing dispatch, headline, and
// win-vs-flop branching, not the full chart/timeline render trees.
vi.mock("@/components/SectionMini", () => ({
  SectionMini: ({ kicker, title }: { kicker: string; title: string }) => (
    <div data-testid={`mini-${kicker}`}>{title}</div>
  ),
}));
vi.mock("@/components/v2/RetentionCurve", () => ({
  RetentionCurve: () => <div data-testid="retention-curve" />,
}));
vi.mock("@/components/v2/Timeline", () => ({
  Timeline: () => <div data-testid="timeline" />,
}));
vi.mock("@/components/v2/HookPhaseCard", () => ({
  HookPhaseGrid: () => <div data-testid="hook-phase-grid" />,
}));
vi.mock("@/components/v2/KpiGrid", () => ({
  KpiGrid: () => <div data-testid="kpi-grid" />,
}));
vi.mock("@/components/v2/IssueCard", () => ({
  IssueCard: ({ issue }: { issue: { title: string } }) => (
    <div data-testid="issue-card">{issue.title}</div>
  ),
}));
vi.mock("@/routes/_app/components/CommentRadarTile", () => ({
  CommentRadarTile: () => <div data-testid="comment-radar-tile" />,
}));
vi.mock("@/routes/_app/components/ThumbnailTile", () => ({
  ThumbnailTile: () => <div data-testid="thumbnail-tile" />,
}));

import { VideoBody } from "./VideoBody";

afterEach(cleanup);

function makeWinReport(overrides: Partial<VideoReportPayload> = {}): VideoReportPayload {
  return {
    video_id: "7630766288574369045",
    mode: "win",
    meta: {
      creator: "creatorx",
      views: 250_000,
      likes: 18_000,
      comments: 800,
      shares: 1_200,
      save_rate: 0.04,
      duration_sec: 28.5,
      thumbnail_url: "https://r2.test/thumbnails/x.png",
      date_posted: "2026-04-15",
      title: "Đây là cách tôi viral",
      niche_label: "Làm đẹp",
      retention_source: "modeled",
    },
    kpis: [],
    segments: [],
    hook_phases: [{ t_range: "0–0.8s", label: "Hook đảo", body: "Câu hỏi đảo neo attention." }],
    lessons: [
      { title: "L1", body: "Body 1" },
      { title: "L2", body: "Body 2" },
      { title: "L3", body: "Body 3" },
    ],
    analysis_headline: "Headline win text",
    analysis_subtext: "Subtext explaining why this video succeeded.",
    flop_issues: null,
    retention_curve: [{ t: 0, pct: 100 }, { t: 1, pct: 65 }],
    niche_benchmark_curve: [{ t: 0, pct: 100 }, { t: 1, pct: 55 }],
    niche_meta: {
      avg_views: 100_000,
      avg_retention: 0.55,
      avg_ctr: 0.04,
      sample_size: 200,
      winners_sample_size: 30,
    },
    ...overrides,
  };
}

function makeFlopReport(overrides: Partial<VideoReportPayload> = {}): VideoReportPayload {
  return {
    ...makeWinReport(),
    mode: "flop",
    analysis_headline: {
      prefix: "Video chỉ đạt ",
      view_accent: "8.4K",
      middle: " view, dưới ngưỡng ngách. ",
      prediction_pos: "~34K",
      suffix: " sau khi sửa hook.",
    },
    analysis_subtext: null,
    flop_issues: [
      {
        sev: "high",
        t: 0,
        end: 2,
        title: "Hook yếu",
        detail: "Hook không neo được attention",
        fix: "Thay bằng câu hỏi đảo",
      },
    ],
    projected_views: 34_000,
    lessons: [],
    ...overrides,
  };
}

function renderInRouter(report: VideoReportPayload) {
  return render(
    <MemoryRouter>
      <VideoBody report={report} />
    </MemoryRouter>,
  );
}

describe("VideoBody render", () => {
  it("renders the win headline as plain text", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByText("Headline win text")).toBeTruthy();
  });

  it("renders the win subtext under the headline", () => {
    renderInRouter(makeWinReport());
    expect(
      screen.getByText("Subtext explaining why this video succeeded."),
    ).toBeTruthy();
  });

  it("renders MỔ VIDEO VIRAL kicker + niche label in win mode", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByText(/MỔ VIDEO VIRAL/)).toBeTruthy();
    expect(screen.getByText("Làm đẹp")).toBeTruthy();
  });

  it("renders the win-mode hook phase + lessons sections", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByTestId("hook-phase-grid")).toBeTruthy();
    expect(screen.getByText(/3 điều bạn có thể copy/)).toBeTruthy();
    expect(screen.getByText("L1")).toBeTruthy();
    expect(screen.getByText("L3")).toBeTruthy();
  });

  it("renders structured flop headline segments with accents", () => {
    renderInRouter(makeFlopReport());
    // Each segment lands as adjacent text — assert by partial matches
    // since they're rendered in nested spans/em.
    expect(screen.getByText(/Video chỉ đạt/)).toBeTruthy();
    expect(screen.getByText("8.4K")).toBeTruthy();
    expect(screen.getByText(/view, dưới ngưỡng ngách/)).toBeTruthy();
    expect(screen.getByText("~34K")).toBeTruthy();
  });

  it("renders flop issues + projected views CTA", () => {
    renderInRouter(makeFlopReport());
    expect(screen.getByText(/CHẨN ĐOÁN VIDEO CỦA BẠN/)).toBeTruthy();
    expect(screen.getByTestId("issue-card")).toBeTruthy();
    expect(screen.getByText("Hook yếu")).toBeTruthy();
    expect(screen.getByText(/Dự đoán nếu áp fix chính/)).toBeTruthy();
    expect(screen.getByText("34.000")).toBeTruthy(); // formatViewsVi(34_000)
  });

  it("renders the diagnosis strip in flop mode (with niche cohort)", () => {
    renderInRouter(makeFlopReport());
    expect(screen.getByText(/So sánh với 30 video thắng/)).toBeTruthy();
  });

  it("renders 'Đang xây dựng pool' fallback when niche cohort < 10", () => {
    const sparse = makeFlopReport({
      niche_meta: {
        avg_views: 0,
        avg_retention: 0.5,
        avg_ctr: 0.04,
        sample_size: 0,
        winners_sample_size: null,
      },
    });
    renderInRouter(sparse);
    expect(screen.getByText(/Đang xây dựng pool/)).toBeTruthy();
  });

  it("renders the TikTok play-button overlay link when creator + video_id present", () => {
    renderInRouter(makeWinReport());
    const link = screen.getByLabelText("Mở video trên TikTok") as HTMLAnchorElement;
    expect(link).toBeTruthy();
    expect(link.getAttribute("href")).toBe(
      "https://www.tiktok.com/@creatorx/video/7630766288574369045",
    );
  });

  it("renders the win-mode action row (Copy hook + Tạo kịch bản)", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByText(/Copy hook/)).toBeTruthy();
    expect(screen.getByText(/Tạo kịch bản từ video này/)).toBeTruthy();
  });

  it("does NOT render the win-mode action row in flop mode", () => {
    renderInRouter(makeFlopReport());
    expect(screen.queryByText(/Copy hook/)).toBeNull();
    expect(screen.queryByText(/Tạo kịch bản từ video này/)).toBeNull();
  });
});
