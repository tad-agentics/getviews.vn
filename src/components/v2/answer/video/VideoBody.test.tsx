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
vi.mock("@/components/v2/Timeline", () => ({
  Timeline: () => <div data-testid="timeline" />,
}));
vi.mock("@/components/v2/HookPhaseCard", () => ({
  HookPhaseGrid: () => <div data-testid="hook-phase-grid" />,
}));
vi.mock("@/components/v2/KpiGrid", () => ({
  KpiGrid: () => <div data-testid="kpi-grid" />,
}));
vi.mock("@/components/ui/collapsible", () => ({
  Collapsible: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CollapsibleTrigger: ({ children }: { children: React.ReactNode }) => (
    <button type="button">{children}</button>
  ),
  CollapsibleContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/routes/_app/components/CommentRadarTile", () => ({
  CommentRadarTile: () => <div data-testid="comment-radar-tile" />,
}));
vi.mock("@/routes/_app/components/ThumbnailTile", () => ({
  ThumbnailTile: () => <div data-testid="thumbnail-tile" />,
}));
vi.mock("@/components/v2/answer/video/VideoDeepUpsell", () => ({
  VideoDeepUpsell: ({
    lockedSections,
  }: {
    lockedSections: { title_vi: string; signal_count?: number }[];
  }) => (
    <div data-testid="video-deep-upsell">
      {lockedSections.map((s) => (
        <span key={s.title_vi}>
          {s.title_vi}
          {s.signal_count ? ` +${s.signal_count}` : ""}
        </span>
      ))}
    </div>
  ),
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
    errors: [],
    narrative_vi: {
      headline_vi: "Headline win text",
      ket_luan_nhanh: "Kết luận nhanh cho win.",
      van_de_chinh: "",
      loi_chinh_narrative: [],
      dinh_huong_chien_luoc: "",
      lessons: [
        { title: "L1", body: "Body 1" },
        { title: "L2", body: "Body 2" },
        { title: "L3", body: "Body 3" },
      ],
    },
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
  const base = makeWinReport();
  return {
    ...base,
    mode: "flop",
    narrative_vi: {
      headline_vi: "Video chỉ đạt 8.4K view, dưới ngưỡng ngách — ~34K sau khi sửa hook.",
      ket_luan_nhanh: "",
      van_de_chinh: "Vấn đề chính flop",
      loi_chinh_narrative: [],
      dinh_huong_chien_luoc: "",
      lessons: [],
    },
    errors: [
      {
        error_id: "ERR_hook",
        sev: "high",
        t: 0,
        end: 2,
        title: "Hook yếu",
        detail: "Hook không neo được attention",
        fix: "Thay bằng câu hỏi đảo",
      },
    ],
    ...overrides,
  };
}

function renderInRouter(
  report: VideoReportPayload,
  videoBodyProps: Omit<React.ComponentProps<typeof VideoBody>, "report"> = {},
) {
  return render(
    <MemoryRouter>
      <VideoBody report={report} {...videoBodyProps} />
    </MemoryRouter>,
  );
}

describe("VideoBody render", () => {
  it("renders diagnosis_v6 sections and omits duplicate van_de_chinh body", () => {
    renderInRouter(
      makeWinReport({
        narrative_vi: {
          headline_vi: "H",
          ket_luan_nhanh: "Kết luận nhanh cho win.",
          van_de_chinh: "KHÔNG HIỂN THỊ KHI V6",
          loi_chinh_narrative: [],
          dinh_huong_chien_luoc: "",
          lessons: [],
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              {
                section_id: "diagnosis",
                title: "Phần chẩn đoán",
                text: "Nội dung chi tiết ở đây.",
              },
            ],
          },
        },
      }),
    );
    expect(screen.getByText("Phần chẩn đoán")).toBeTruthy();
    expect(screen.getByText("Nội dung chi tiết ở đây.")).toBeTruthy();
    expect(screen.queryByText("KHÔNG HIỂN THỊ KHI V6")).toBeNull();
  });

  it("renders the win headline from narrative_vi.headline_vi", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByText("Headline win text")).toBeTruthy();
  });

  it("renders ket_luan_nhanh callout in win mode when present", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByText("Kết luận nhanh cho win.")).toBeTruthy();
  });

  it("renders MỔ VIDEO VIEW CAO kicker + niche label in win mode", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByText(/MỔ VIDEO VIEW CAO/)).toBeTruthy();
    expect(screen.getByText("Làm đẹp")).toBeTruthy();
  });

  it("renders the HIT performance tier chip when performance_tier='hit'", () => {
    renderInRouter(makeWinReport({ performance_tier: "hit" }));
    expect(screen.getByText("HIT")).toBeTruthy();
  });

  it("renders the FLOP performance tier chip when performance_tier='flop' (flop mode)", () => {
    renderInRouter(makeFlopReport({ performance_tier: "flop" }));
    expect(screen.getByText("FLOP")).toBeTruthy();
  });

  it("renders TRUNG BÌNH chip for performance_tier='average'", () => {
    renderInRouter(makeWinReport({ performance_tier: "average" }));
    expect(screen.getByText("TRUNG BÌNH")).toBeTruthy();
  });

  it("hides the performance tier chip when performance_tier='unknown'", () => {
    renderInRouter(makeWinReport({ performance_tier: "unknown" }));
    expect(screen.queryByText("HIT")).toBeNull();
    expect(screen.queryByText("FLOP")).toBeNull();
    expect(screen.queryByText("TRUNG BÌNH")).toBeNull();
  });

  it("hides the performance tier chip when performance_tier is missing", () => {
    renderInRouter(makeWinReport());
    expect(screen.queryByText("HIT")).toBeNull();
  });

  it("renders the win-mode hook phase + lessons sections", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByTestId("hook-phase-grid")).toBeTruthy();
    expect(screen.getByText(/3 điều bạn có thể copy/)).toBeTruthy();
    expect(screen.getByText("L1")).toBeTruthy();
    expect(screen.getByText("L3")).toBeTruthy();
  });

  it("renders flop headline from narrative_vi.headline_vi", () => {
    renderInRouter(makeFlopReport());
    expect(
      screen.getByText(
        "Video chỉ đạt 8.4K view, dưới ngưỡng ngách — ~34K sau khi sửa hook.",
      ),
    ).toBeTruthy();
  });

  it("renders hook phase grid in flop mode when hook_phases are present", () => {
    renderInRouter(makeFlopReport());
    expect(screen.getByTestId("hook-phase-grid")).toBeTruthy();
    // Copy was tightened: "3 giây đầu — nhịp mở dễ mất người xem" →
    // "3 giây đầu dễ mất người xem". Test asserts the current form.
    expect(screen.getByText(/3 giây đầu dễ mất người xem/)).toBeTruthy();
  });

  it("renders flop issues + detail/fix + script CTA (no projected views)", () => {
    renderInRouter(makeFlopReport());
    expect(screen.getByText(/CHẨN ĐOÁN/)).toBeTruthy();
    expect(screen.getByText("Hook yếu")).toBeTruthy();
    expect(screen.getByText(/Hook không neo được attention/)).toBeTruthy();
    expect(screen.queryByText(/Dự đoán nếu áp fix chính/)).toBeNull();
    expect(screen.getByText(/Viết lại kịch bản/)).toBeTruthy();
  });

  it("renders the diagnosis strip in flop mode (with niche cohort)", () => {
    renderInRouter(makeFlopReport());
    expect(screen.getByText(/So sánh với 30 video thắng trong mảng/)).toBeTruthy();
    expect(screen.getByText(/Mảng trung bình:/)).toBeTruthy();
  });

  it("flips diagnosis strip to 'cùng format' when benchmark_axis = content_class", () => {
    // A.2.4 — when BE returns benchmark_axis="content_class" (sharper cohort
    // from content_class_intelligence MV), labels switch from niche-wide
    // copy to content-class copy so creators know the cohort is narrower.
    const cc = makeFlopReport({
      niche_meta: {
        avg_views: 100_000,
        avg_retention: 0.55,
        avg_ctr: 0.04,
        sample_size: 200,
        winners_sample_size: 30,
        benchmark_axis: "content_class",
      },
    });
    renderInRouter(cc);
    expect(screen.getByText(/So sánh với 30 video cùng định dạng/)).toBeTruthy();
    expect(screen.getByText(/Cùng định dạng TB:/)).toBeTruthy();
  });

  it("shows en dash for cohort TB views when avg_views is zero and winners pool exists", () => {
    const r = makeFlopReport({
      niche_meta: {
        avg_views: 0,
        avg_retention: 0.55,
        avg_ctr: 0.04,
        sample_size: 200,
        winners_sample_size: 30,
      },
    });
    renderInRouter(r);
    expect(screen.getByText(/Mảng trung bình:\s*—/)).toBeTruthy();
  });

  it("shows en dash for cohort TB views when avg_views is null", () => {
    const r = makeFlopReport({
      niche_meta: {
        avg_views: null,
        avg_retention: 0.55,
        avg_ctr: 0.04,
        sample_size: 200,
        winners_sample_size: 30,
      },
    });
    renderInRouter(r);
    expect(screen.getByText(/Mảng trung bình:\s*—/)).toBeTruthy();
  });

  it("renders 'Chưa có nhóm đối chiếu' fallback when niche cohort < 10", () => {
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
    expect(screen.getByText(/Chưa có nhóm đối chiếu/)).toBeTruthy();
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
    expect(screen.getByText(/Sao chép hook/)).toBeTruthy();
    expect(screen.getByText(/Tạo kịch bản từ video này/)).toBeTruthy();
  });

  it("does NOT render the win-mode action row in flop mode", () => {
    renderInRouter(makeFlopReport());
    expect(screen.queryByText(/Sao chép hook/)).toBeNull();
    expect(screen.queryByText(/Tạo kịch bản từ video này/)).toBeNull();
  });

  // ── CreatorComparisonCard (Lightreel hit/flop adoption from b7d4bc8) ──

  it("renders CreatorComparisonCard when creator_comparison is present", () => {
    const withComparison = makeFlopReport({
      creator_comparison: {
        creator_handle: "@creatorx",
        total_posts_analyzed: 12,
        median_views: 90_000,
        target_percentile: "top 35%",
        target_vs_median: 1.4,
        delta: 24,
        hit: {
          video_id: "v_hit",
          tiktok_url: "https://www.tiktok.com/@creatorx/video/v_hit",
          views: 1_200_000,
        },
        flop: {
          video_id: "v_flop",
          tiktok_url: "https://www.tiktok.com/@creatorx/video/v_flop",
          views: 50_000,
        },
      },
    });
    renderInRouter(withComparison);
    // Kicker carries the creator handle inline with the section title.
    expect(screen.getByText(/So sánh trong kênh · @creatorx/i)).toBeTruthy();
    expect(screen.getByText("Video có views cao nhất")).toBeTruthy();
    expect(screen.getByText("Video có views thấp nhất")).toBeTruthy();
    // Hit views formatted as 1.2M (formatViews threshold)
    expect(screen.getByText("1.2M")).toBeTruthy();
    // Flop views formatted as 50K
    expect(screen.getByText("50K")).toBeTruthy();
    // Delta multiplier
    expect(screen.getByText("24×")).toBeTruthy();
    expect(
      screen.getByText(/Tỉ lệ views cao nhất so với thấp nhất trong mẫu/),
    ).toBeTruthy();
    const tiktokLinks = screen.getAllByRole("link", { name: /Xem video/ });
    expect(tiktokLinks).toHaveLength(2);
    expect(tiktokLinks[0]?.getAttribute("href")).toBe(
      "https://www.tiktok.com/@creatorx/video/v_hit",
    );
    // Percentile rendering
    expect(screen.getByText("top 35%")).toBeTruthy();
    // Cohort copy "X video" is part of a larger sentence — partial match.
    expect(screen.getByText(/12 video/)).toBeTruthy();
  });

  it("renders creator comparison thumbnails and caption excerpt when present", () => {
    const withComparison = makeFlopReport({
      creator_comparison: {
        creator_handle: "@creatorx",
        total_posts_analyzed: 5,
        median_views: 50_000,
        target_percentile: "top 35%",
        target_vs_median: 1.0,
        delta: 10,
        hit: {
          video_id: "a",
          tiktok_url: "https://www.tiktok.com/@creatorx/video/a",
          views: 100_000,
          thumbnail_url: "https://example.com/thumb-a.jpg",
          hook_type: "Caption hit hay",
        },
        flop: {
          video_id: "b",
          tiktok_url: "https://www.tiktok.com/@creatorx/video/b",
          views: 10_000,
          thumbnail_url: "https://example.com/thumb-b.jpg",
          hook_type: "Caption flop",
        },
      },
    });
    const { container } = renderInRouter(withComparison);
    expect(container.querySelector('img[src="https://example.com/thumb-a.jpg"]')).toBeTruthy();
    expect(container.querySelector('img[src="https://example.com/thumb-b.jpg"]')).toBeTruthy();
    expect(screen.getByText("Caption hit hay")).toBeTruthy();
    expect(screen.getByText("Caption flop")).toBeTruthy();
  });

  // Note: the "renders soft fallback when creator_comparison is null
  // but creator is known" test was removed because commit 767cc4c
  // ("hide CreatorComparisonUnavailable empty state — ChannelProofBlock
  // already covers channel data") deliberately removed that render
  // path. The unavailable card export is no longer mounted; the next
  // test below asserts the new behaviour.

  it("omits any creator-comparison block when both comparison and creator are missing", () => {
    const withoutCreator = makeFlopReport({
      creator_comparison: null,
      meta: { ...makeFlopReport().meta, creator: "" },
    });
    renderInRouter(withoutCreator);
    expect(screen.queryByText(/So sánh trong kênh/i)).toBeNull();
  });

  it("omits ContextStrip entirely when no enrichment + no creator_median_views", () => {
    const { container } = renderInRouter(makeFlopReport());
    expect(container.querySelector("[aria-label='Bối cảnh phân tích']")).toBeNull();
    expect(screen.queryByText(/BỐI CẢNH PHÂN TÍCH/)).toBeNull();
  });

  it("renders target_vs_creator_median in the ContextStrip", () => {
    const base = makeFlopReport();
    const withRatio = makeFlopReport({
      meta: {
        ...base.meta,
        creator_median_views: 100_000,
        target_vs_creator_median: 0.6,
      },
    });
    renderInRouter(withRatio);
    expect(screen.getByText(/SO VỚI KÊNH BẠN/)).toBeTruthy();
    expect(screen.getByText(/0,6× kênh trung bình/)).toBeTruthy();
    expect(screen.getByText(/Trung vị 100\.0K view/)).toBeTruthy();
  });

  it("renders enrichment tone in ContextStrip", () => {
    renderInRouter(
      makeWinReport({
        enrichment: {
          pain_points: [],
          promotion_type: "organic",
          style_tags: [],
          tone: "entertaining",
        },
      }),
    );
    expect(screen.getByText(/GIỌNG ĐIỆU/)).toBeTruthy();
    expect(screen.getByText("Giải trí")).toBeTruthy();
  });

  it("renders enrichment chips, audience, and pain points", () => {
    renderInRouter(
      makeFlopReport({
        enrichment: {
          target_audience: "phụ nữ 25–34 vùng đô thị",
          pain_points: ["da dầu mụn ẩn", "ngân sách hạn chế", "thời gian eo hẹp"],
          promotion_type: "brand_deal",
          style_tags: ["talking_head", "POV", "fast_cuts"],
        },
      }),
    );
    expect(screen.getByText("phụ nữ 25–34 vùng đô thị")).toBeTruthy();
    expect(screen.getByText("da dầu mụn ẩn")).toBeTruthy();
    expect(screen.getByText("Đặt hàng nhãn")).toBeTruthy();
    expect(screen.getByText("talking_head")).toBeTruthy();
  });

  it("hides promotion chip when promotion_type is organic but still shows style tags", () => {
    renderInRouter(
      makeFlopReport({
        enrichment: {
          target_audience: null,
          pain_points: [],
          promotion_type: "organic",
          style_tags: ["talking_head"],
        },
      }),
    );
    // No promotion-type chip — `Tự sản xuất` shouldn't render for organic.
    expect(screen.queryByText("Tự sản xuất")).toBeNull();
    expect(screen.getByText("talking_head")).toBeTruthy();
  });

  it("shows minh chứng fallback when comparison videos have no TikTok URL", () => {
    const withMissingUrls = makeFlopReport({
      creator_comparison: {
        creator_handle: "@creatorx",
        total_posts_analyzed: 8,
        median_views: 60_000,
        target_percentile: "median",
        target_vs_median: 1.0,
        delta: 4,
        hit: { video_id: null, tiktok_url: null, views: 240_000 },
        flop: { video_id: null, tiktok_url: null, views: 60_000 },
      },
    });
    renderInRouter(withMissingUrls);
    expect(screen.getAllByText(/Chưa có link TikTok cho video này/).length).toBe(2);
    expect(screen.queryAllByRole("link", { name: /Xem video/ })).toHaveLength(0);
  });

  it("renders locked-section teasers when basic depth and showDeepUpsell", () => {
    render(
      <MemoryRouter>
        <VideoBody
          report={makeWinReport({
            analysis_depth: "basic",
            locked_sections: [
              {
                section_id: "sound",
                title_vi: "Âm thanh và nhịp điệu",
                signal_count: 2,
              },
            ],
          })}
          analysisDepth="basic"
          showDeepUpsell
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("video-deep-upsell")).toBeTruthy();
    expect(screen.getByText(/Âm thanh và nhịp điệu \+2/)).toBeTruthy();
  });

  it("hides BoostAttributionBlock meta fallback on basic depth", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
        analysis_depth: "basic",
        meta: {
          ...base.meta,
          boost_attribution: "suspect_medium",
          reference_eligible: false,
        },
      }),
    );
    expect(screen.queryByLabelText("Phân loại nguồn view")).toBeNull();
  });

  it("renders CommentRadarTile when on-demand report includes comment_radar", () => {
    renderInRouter(
      makeWinReport({
        source: "on_demand",
        comment_radar: {
          sampled: 12,
          total_available: 48,
          sentiment: { positive_pct: 40, negative_pct: 10, neutral_pct: 50 },
          purchase_intent: { count: 2, top_phrases: ["mua ở đâu"] },
          questions_asked: 3,
          language: "vi",
        },
      }),
    );
    expect(screen.getByTestId("comment-radar-tile")).toBeTruthy();
  });

  it("hides deep upsell for deep analysis depth", () => {
    render(
      <MemoryRouter>
        <VideoBody
          report={makeWinReport({ analysis_depth: "deep" })}
          analysisDepth="deep"
          showDeepUpsell
        />
      </MemoryRouter>,
    );
    expect(screen.queryByTestId("video-deep-upsell")).toBeNull();
  });

  it("renders HookTimelineStrip after hook_analysis section", () => {
    renderInRouter(
      makeWinReport({
        hook_timeline: [{ t: 0.5, event: "face_enter" }],
        narrative_vi: {
          ...makeWinReport().narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              { section_id: "hook_analysis", title: "Hook", text: "Hook prose." },
            ],
          },
        },
      }),
    );
    expect(screen.getByText(/Dòng thời gian hook/)).toBeTruthy();
    expect(screen.getByText(/Khuôn mặt xuất hiện/)).toBeTruthy();
  });

  it("renders StatsHistoryStrip after distribution section on deep depth", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
        analysis_depth: "deep",
        meta: {
          ...base.meta,
          stats_history: [
            { at: "a", phase: "t0", views: 1000, likes: 50, comments: 10, shares: 5 },
            { at: "b", phase: "t6h", views: 5000, likes: 80, comments: 12, shares: 4 },
          ],
          distribution_shape: "spike_then_flat",
        },
        narrative_vi: {
          ...base.narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              { section_id: "distribution", title: "Phân phối", text: "Dist prose." },
            ],
          },
        },
      }),
      { analysisDepth: "deep" },
    );
    expect(screen.getByLabelText("Diễn biến lượt xem theo thời gian")).toBeTruthy();
    expect(screen.getByText(/Tăng vọt rồi đi ngang/)).toBeTruthy();
    expect(screen.getByText("1.0K")).toBeTruthy();
  });

  it("renders StatsHistoryStrip fallback when distribution section is absent on deep depth", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
        analysis_depth: "deep",
        meta: {
          ...base.meta,
          stats_history: [
            { at: "a", phase: "t0", views: 2000, likes: 40, comments: 8, shares: 2 },
            { at: "b", phase: "t24h", views: 9000, likes: 90, comments: 15, shares: 6 },
          ],
        },
        narrative_vi: {
          ...base.narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              { section_id: "diagnosis", title: "Chẩn đoán", text: "Body." },
            ],
          },
        },
      }),
      { analysisDepth: "deep" },
    );
    expect(screen.getByLabelText("Diễn biến lượt xem theo thời gian")).toBeTruthy();
    expect(screen.getByText("2.0K")).toBeTruthy();
  });

  it("hides StatsHistoryStrip on basic depth even when stats_history present", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
        analysis_depth: "basic",
        meta: {
          ...base.meta,
          stats_history: [
            { at: "a", phase: "t0", views: 2000, likes: 40, comments: 8, shares: 2 },
            { at: "b", phase: "t24h", views: 9000, likes: 90, comments: 15, shares: 6 },
          ],
        },
      }),
      { analysisDepth: "basic" },
    );
    expect(screen.queryByLabelText("Diễn biến lượt xem theo thời gian")).toBeNull();
  });

  it("renders BoostAttributionBlock after boost_attribution section", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
        meta: {
          ...base.meta,
          boost_attribution: "suspect_medium",
          reference_eligible: false,
        },
        narrative_vi: {
          ...base.narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              {
                section_id: "boost_attribution",
                title: "Boost",
                text: "Prose.",
                findings: [{ title_vi: "View spike", body_vi: "ER thấp so cohort." }],
              },
            ],
          },
        },
      }),
    );
    expect(screen.getByLabelText("Phân loại nguồn lượt xem")).toBeTruthy();
    expect(screen.getByText(/Loại khỏi nhóm tham chiếu tự nhiên/)).toBeTruthy();
    expect(screen.getAllByText("View spike").length).toBeGreaterThanOrEqual(1);
  });

  it("renders CarouselIntelStrip when carousel_intel present on deep depth", () => {
    renderInRouter(
      makeWinReport({
        analysis_depth: "deep",
        carousel_subformat_label: "So sánh",
        carousel_intel: {
          content_arc: "list",
          slides: [{ index: 0, text_preview: "Slide 1" }],
        },
      }),
      { analysisDepth: "deep" },
    );
    expect(screen.getByText(/Logic lướt · 1 slide/)).toBeTruthy();
    expect(screen.getByText("Slide 1")).toBeTruthy();
  });

  it("hides CarouselIntelStrip on basic depth", () => {
    renderInRouter(
      makeWinReport({
        analysis_depth: "basic",
        carousel_intel: {
          content_arc: "list",
          slides: [{ index: 0, text_preview: "Slide 1" }],
        },
      }),
      { analysisDepth: "basic" },
    );
    expect(screen.queryByText(/Logic lướt · 1 slide/)).toBeNull();
    expect(screen.queryByText("Slide 1")).toBeNull();
  });
});
