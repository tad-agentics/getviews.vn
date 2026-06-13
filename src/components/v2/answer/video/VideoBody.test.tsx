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
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import type { VideoReportPayload } from "@/lib/api-types";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: "https://r2.test",
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
vi.mock("@/components/v2/HookPhaseCard", () => ({
  HookPhaseGrid: () => <div data-testid="hook-phase-grid" />,
}));
vi.mock("@/components/v2/KpiGrid", () => ({
  // Render deltas so tests can assert the tier_ratio ↔ KPI reconciliation.
  KpiGrid: ({ kpis }: { kpis: { label: string; delta: string }[] }) => (
    <div data-testid="kpi-grid">{kpis.map((k) => `${k.label}:${k.delta}`).join("|")}</div>
  ),
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

import { VideoBody } from "./VideoBody";

afterEach(cleanup);

function makeWinReport(overrides: Partial<VideoReportPayload> = {}): VideoReportPayload {
  return {
    video_id: "7630766288574369045",
    mode: "win",
    performance_tier: "hit",
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
    performance_tier: "flop",
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

  it("renders PHÂN TÍCH VIDEO kicker + niche label in win mode", () => {
    renderInRouter(makeWinReport());
    expect(screen.getByText(/PHÂN TÍCH VIDEO/)).toBeTruthy();
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
    renderInRouter(makeWinReport({ performance_tier: undefined }));
    expect(screen.queryByText("HIT")).toBeNull();
  });

  it("renders the win-mode lessons section (hook phase grid hidden)", () => {
    renderInRouter(makeWinReport());
    expect(screen.queryByTestId("hook-phase-grid")).toBeNull();
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

  it("does not render hook phase grid in flop mode", () => {
    renderInRouter(makeFlopReport());
    expect(screen.queryByTestId("hook-phase-grid")).toBeNull();
    expect(screen.queryByText(/Dòng thời gian hook/)).toBeNull();
  });

  it("renders flop issues + detail/fix + script CTA (no projected views)", () => {
    renderInRouter(makeFlopReport());
    expect(screen.getByText(/Vấn đề cần sửa/)).toBeTruthy();
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

  it("renders hover preview video when R2 clip is available", () => {
    const { container } = renderInRouter(makeWinReport());
    const video = container.querySelector("video");
    expect(video).toBeTruthy();
    expect((video as HTMLVideoElement).muted).toBe(true);
    expect(screen.queryByLabelText("Mở video trên TikTok")).toBeNull();
  });

  it("renders BREAKOUT badge with white text on accent (no gv-kicker gray)", () => {
    renderInRouter(
      makeWinReport({
        meta: {
          ...makeWinReport().meta,
          is_breakout: true,
        },
      }),
    );
    const badge = screen.getByText("BREAKOUT");
    expect(badge.className).toContain("text-white");
    expect(badge.className).not.toContain("gv-kicker");
  });

  it("does not render win-mode hook/script CTAs at top of report", () => {
    renderInRouter(makeWinReport());
    expect(screen.queryByText(/Sao chép hook/)).toBeNull();
    expect(screen.queryByText(/Tạo kịch bản từ video này/)).toBeNull();
  });

  it("renders flop header CTAs (Soi kênh + Viết lại) once near top", () => {
    renderInRouter(makeFlopReport());
    expect(screen.getByText(/Soi kênh @creatorx/)).toBeTruthy();
    expect(screen.getAllByText(/Viết lại kịch bản/)).toHaveLength(1);
  });

  it("shows win layout when stored mode is flop but performance_tier is hit", () => {
    renderInRouter(
      makeFlopReport({
        performance_tier: "hit",
        narrative_vi: {
          headline_vi: "Video đạt breakout 435x nhờ tương tác sâu.",
          ket_luan_nhanh: "",
          van_de_chinh: "",
          loi_chinh_narrative: [],
          dinh_huong_chien_luoc: "",
          lessons: [],
        },
      }),
    );
    expect(screen.getByText(/PHÂN TÍCH VIDEO/)).toBeTruthy();
    expect(screen.getByText(/góc tối ưu tiếp theo/)).toBeTruthy();
    expect(screen.queryByText(/Viết lại kịch bản/)).toBeNull();
  });

  it("shows win layout when flop mode but channel breakout ratio on average tier", () => {
    const base = makeFlopReport();
    renderInRouter(
      makeFlopReport({
        performance_tier: "average",
        meta: {
          ...base.meta,
          views: 406_098,
          creator_median_views: 934,
          target_vs_creator_median: 435,
        },
        narrative_vi: {
          headline_vi: "Video breakout so với kênh.",
          ket_luan_nhanh: "",
          van_de_chinh: "",
          loi_chinh_narrative: [],
          dinh_huong_chien_luoc: "",
          lessons: [],
        },
      }),
    );
    expect(screen.getByText(/PHÂN TÍCH VIDEO/)).toBeTruthy();
    expect(screen.getByText(/góc tối ưu tiếp theo/)).toBeTruthy();
    expect(screen.queryByText(/Viết lại kịch bản/)).toBeNull();
  });

  it("calls onRequestAppendTurn from format card CTA", () => {
    const onRequestAppendTurn = vi.fn();
    renderInRouter(
      makeWinReport({
        format_cards: [
          {
            format_name_vi: "POV mua sắm",
            mechanism_vi: "Góc nhìn thứ nhất",
            view_range: "50K–200K",
            engagement_rate: "8%",
            example_hook_vi: "Mình vừa thử…",
            evidence_aweme_id: null,
            format_examples: [],
          },
        ],
      }),
      { onRequestAppendTurn },
    );
    fireEvent.click(screen.getByRole("button", { name: /Tạo kịch bản theo POV mua sắm/ }));
    expect(onRequestAppendTurn).toHaveBeenCalledWith(
      expect.stringContaining('định dạng "POV mua sắm"'),
    );
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
    // Percentile derives from target_vs_median (1.4× → above median) — the
    // BE string is only a fallback when the ratio is missing (2026-06-12
    // inverted-label fix).
    expect(screen.getByText("trên mức trung bình")).toBeTruthy();
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

  it("omits metadata adjunct block when no enrichment + no creator_median_views", () => {
    const { container } = renderInRouter(makeFlopReport());
    expect(screen.queryByText("Bối cảnh phân tích")).toBeNull();
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

  it("renders enrichment tone inside metadata adjunct block", () => {
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
    expect(screen.getByText("Phân tích bối cảnh & diễn biến")).toBeTruthy();
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
    // Style tags render through the Vietnamese label map — never raw enums
    // (live audit 2026-06-12).
    expect(screen.getByText("Nói trước camera")).toBeTruthy();
    expect(screen.getByText("POV")).toBeTruthy();
    expect(screen.getByText("Cắt cảnh nhanh")).toBeTruthy();
    expect(screen.queryByText("talking_head")).toBeNull();
    expect(screen.queryByText("fast_cuts")).toBeNull();
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
    expect(screen.getByText("Nói trước camera")).toBeTruthy();
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

  it("renders BoostAttributionBlock meta fallback when section absent", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
        meta: {
          ...base.meta,
          boost_attribution: "suspect_medium",
          reference_eligible: false,
        },
      }),
    );
    expect(screen.getByLabelText("Phân loại nguồn lượt xem")).toBeTruthy();
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

  it("shows hook_analysis prose only — no phase grid or timeline embed", () => {
    renderInRouter(
      makeWinReport({
        hook_timeline: [{ t: 0.5, event: "face_enter" }],
        narrative_vi: {
          ...makeWinReport().narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              { section_id: "hook_analysis", title: "Phân tích hook", text: "Hook prose." },
            ],
          },
        },
      }),
    );
    expect(screen.getByText("Hook prose.")).toBeTruthy();
    expect(screen.queryByText(/Dòng thời gian hook/)).toBeNull();
    expect(screen.queryByTestId("hook-phase-grid")).toBeNull();
    expect(screen.getAllByText("Phân tích hook")).toHaveLength(1);
  });

  it("merges sound and script_structure into strength-gap block after hook_analysis", () => {
    const { container } = renderInRouter(
      makeWinReport({
        reference_videos: [
          {
            aweme_id: "222",
            desc: "",
            hook_type: null,
            content_format: null,
            views: 200_000,
            engagement_rate: null,
            author_handle: "@struct",
            thumbnail_url: "https://t/2.jpg",
            tiktok_url: "https://tiktok.com/@struct/video/222",
            source: "corpus",
          },
        ],
        narrative_vi: {
          ...makeWinReport().narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              { section_id: "hook_analysis", title_vi: "Phân tích hook", text_vi: "Hook." },
              {
                section_id: "sound",
                title_vi: "Âm thanh và nhịp điệu",
                text_vi: "Sound prose không hiển thị.",
                findings: [{ title_vi: "Hook im lặng", fix_vi: "Voiceover giây 0." }],
              },
              {
                section_id: "script_structure",
                title_vi: "Dòng thời gian · Cấu trúc video",
                text_vi: "Cấu trúc prose.",
                findings: [
                  {
                    title_vi: "Nhịp cắt nhanh",
                    fix_vi: "Tiếp tục giữ nhịp 1,2s/cảnh.",
                  },
                  {
                    title_vi: "Dead air giữa clip",
                    fix_vi: "Xen cận mỗi 2s.",
                  },
                ],
                embedded_tiles: [
                  {
                    aweme_id: "222",
                    narrative_vi: "Xen cận sản phẩm mỗi 2s — không để cảnh tĩnh quá 1,5s.",
                  },
                ],
              },
            ],
          },
        },
      }),
    );
    expect(screen.getByText("Phân tích cấu trúc Video")).toBeTruthy();
    expect(screen.queryByText("Âm thanh và nhịp điệu")).toBeNull();
    expect(screen.queryByText(/Dòng thời gian · Cấu trúc video/)).toBeNull();
    expect(screen.getByText("Nhịp & cắt")).toBeTruthy();
    expect(screen.getByText("Âm thanh")).toBeTruthy();
    expect(screen.getByText("Sound prose không hiển thị.")).toBeTruthy();
    expect(screen.getAllByText("ĐIỂM MẠNH").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("THIẾU SÓT").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Hook im lặng")).toBeTruthy();
    expect(screen.getByText(/khoảng lặng giữa clip/)).toBeTruthy();
    expect(screen.getByText("Cấu trúc prose.")).toBeTruthy();
    expect(container.querySelector("a[href*='tiktok.com']")).toBeTruthy();
    const headings = screen.getAllByRole("heading", { level: 3 });
    const titles = headings.map((h) => h.textContent ?? "");
    expect(titles.indexOf("Phân tích hook")).toBeLessThan(
      titles.indexOf("Phân tích cấu trúc Video"),
    );
  });

  it("merges persona into structure block alongside sound and script_structure", () => {
    renderInRouter(
      makeWinReport({
        narrative_vi: {
          ...makeWinReport().narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              { section_id: "hook_analysis", title_vi: "Phân tích hook", text_vi: "Hook." },
              {
                section_id: "script_structure",
                title_vi: "Dòng thời gian · Cấu trúc video",
                text_vi: "Cấu trúc prose.",
                findings: [{ title_vi: "Dead air giữa clip", fix_vi: "Xen cận mỗi 2s." }],
              },
              {
                section_id: "sound",
                title_vi: "Âm thanh và nhịp điệu",
                findings: [{ title_vi: "Hook im lặng", fix_vi: "Voiceover giây 0." }],
              },
              {
                section_id: "persona",
                title_vi: "Phong cách và nhân vật",
                text_vi: "Giọng thiếu va chạm.",
                findings: [
                  {
                    title_vi: "Thiếu tính chân thực",
                    fix_vi: "Thêm chi tiết tiêu cực nhỏ.",
                  },
                ],
              },
            ],
          },
        },
      }),
    );
    expect(screen.getByText("Phân tích cấu trúc Video")).toBeTruthy();
    expect(screen.queryByText("Phong cách và nhân vật")).toBeNull();
    expect(screen.getByText("Giọng & persona")).toBeTruthy();
    expect(screen.getByText("Thiếu tính chân thực")).toBeTruthy();
    expect(screen.getByText(/Giọng thiếu va chạm/)).toBeTruthy();
  });

  it("renders script_structure adjunct with fallback prose when segments are not informative", () => {
    renderInRouter(
      makeWinReport({
        segments: [
          { name: "Hook", pct: 12, color_key: "hook" },
          { name: "Body", pct: 88, color_key: "body" },
        ],
        meta: { ...makeWinReport().meta, duration_sec: 28 },
      }),
    );
    expect(screen.getByText(/nhịp kịch bản trong 28 giây/)).toBeTruthy();
    expect(screen.queryByLabelText("Dòng thời gian cấu trúc video")).toBeNull();
    expect(screen.queryByText("BẰNG CHỨNG TRONG CLIP")).toBeNull();
  });

  it("renders stats history inside metadata block when diagnosis sections exist", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
        meta: {
          ...base.meta,
          stats_history: [
            { at: "a", phase: "t0", views: 1000, likes: 50, comments: 10, shares: 5 },
            { at: "b", phase: "t6h", views: 5000, likes: 80, comments: 12, shares: 4 },
            { at: "c", phase: "t24h", views: 5100, likes: 82, comments: 12, shares: 4 },
          ],
          distribution_shape: "spike_then_flat",
        },
        narrative_vi: {
          ...base.narrative_vi!,
          _schema_version: "v6",
          diagnosis_vi: {
            headline_vi: "H",
            sections: [
              { section_id: "diagnosis", title: "Chẩn đoán", text: "**Video đang chạy tốt.**" },
            ],
          },
        },
      }),
    );
    expect(screen.getByText("Phân tích bối cảnh & diễn biến")).toBeTruthy();
    expect(screen.getByLabelText("Diễn biến lượt xem theo thời gian")).toBeTruthy();
    expect(screen.getByText(/Tăng vọt rồi đi ngang/)).toBeTruthy();
    expect(screen.getByText(/Chưa tốt/)).toBeTruthy();
    expect(screen.getByText("1.0K")).toBeTruthy();
  });

  it("renders stats history in metadata adjunct when distribution section is absent", () => {
    const base = makeWinReport();
    renderInRouter(
      makeWinReport({
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
    );
    expect(screen.getByText("Phân tích bối cảnh & diễn biến")).toBeTruthy();
    expect(screen.getByLabelText("Diễn biến lượt xem theo thời gian")).toBeTruthy();
    expect(screen.getByText("2.0K")).toBeTruthy();
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

  // ── tier_ratio ↔ VIEW KPI single source of truth (audit 2026-06-12) ──

  it("overrides the VIEW KPI delta with tier_ratio so chip and KPI agree", () => {
    renderInRouter(
      makeFlopReport({
        performance_tier: "flop",
        tier_ratio: 0.7,
        tier_benchmark_n: 40,
        kpis: [
          { label: "VIEW", value: "64K", delta: "0.6× ngách" },
          { label: "SHARE", value: "120", delta: "lan toả" },
        ],
      }),
    );
    const grid = screen.getByTestId("kpi-grid");
    expect(grid.textContent).toContain("VIEW:0.7× TB format");
    expect(grid.textContent).toContain("SHARE:lan toả");
    // The chip shows the same number.
    expect(screen.getByText("0.7× TB FORMAT")).toBeTruthy();
  });

  it("keeps the BE VIEW delta when tier_ratio is absent", () => {
    renderInRouter(
      makeFlopReport({
        kpis: [{ label: "VIEW", value: "64K", delta: "0.6× ngách" }],
      }),
    );
    expect(screen.getByTestId("kpi-grid").textContent).toContain("VIEW:0.6× ngách");
  });

  // ── "Video này so với kênh bạn" hidden without comparison data ──

  it("hides the standalone channel section when v5 channel context has no per-format data", () => {
    renderInRouter(
      makeFlopReport({
        _schema_version: "v5",
        channel_context: { available: true, sample_size: 1 },
      } as Partial<VideoReportPayload>),
    );
    expect(screen.queryByText("Video này so với kênh bạn")).toBeNull();
  });

  it("shows the standalone channel section when v5 per_format_views has ≥2 formats", () => {
    renderInRouter(
      makeFlopReport({
        _schema_version: "v5",
        channel_context: {
          available: true,
          sample_size: 12,
          median_views: 40_000,
          per_format_views: {
            talking_head: {
              n: 6,
              avg_views: 80_000,
              median_views: 70_000,
              min_views: 20_000,
              max_views: 150_000,
            },
            voiceover: {
              n: 4,
              avg_views: 30_000,
              median_views: 25_000,
              min_views: 10_000,
              max_views: 60_000,
            },
          },
        },
      } as Partial<VideoReportPayload>),
    );
    expect(screen.getByText("Video này so với kênh bạn")).toBeTruthy();
  });

  it("hides the legacy channel section when there are no top/bottom videos", () => {
    renderInRouter(
      makeFlopReport({
        channel_context: { available: true, sample_size: 1, top_videos: [], bottom_videos: [] },
      }),
    );
    expect(screen.queryByText("Video này so với kênh bạn")).toBeNull();
  });

  it("hides CreatorComparisonCard when the payload misses hit/flop cells", () => {
    renderInRouter(
      makeFlopReport({
        creator_comparison: {
          creator_handle: "@creatorx",
          total_posts_analyzed: 2,
          median_views: 0,
          target_percentile: "",
          target_vs_median: 0,
          delta: 0,
          hit: null,
          flop: null,
        } as unknown as VideoReportPayload["creator_comparison"],
      }),
    );
    expect(screen.queryByText("Video này so với kênh bạn")).toBeNull();
    expect(screen.queryByText(/So sánh trong kênh/)).toBeNull();
  });

  it("renders CarouselIntelStrip when carousel_intel present", () => {
    renderInRouter(
      makeWinReport({
        carousel_subformat_label: "So sánh",
        carousel_intel: {
          content_arc: "list",
          slides: [{ index: 0, text_preview: "Slide 1" }],
        },
      }),
    );
    expect(screen.getByText(/Logic lướt · 1 slide/)).toBeTruthy();
    expect(screen.getByText("Slide 1")).toBeTruthy();
  });
});
