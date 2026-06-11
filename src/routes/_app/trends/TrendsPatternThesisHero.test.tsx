/**
 * Trends — TrendsPatternThesisHero render-test.
 *
 * L2.2 Sprint 7c reshape — hero now leads with creator-friendly
 * Vietnamese copy ("X công thức đang bứt phá trong ngách … tuần này"),
 * not analyst-coded weekly_instance_count metrics. Reuses
 * useTopPatterns to mirror what the §I grid actually shows.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TopPattern, TopPatternsScope } from "@/hooks/useTopPatterns";

const heroScope: TopPatternsScope = { contentClassIds: [10], legacyNicheId: 4 };

const mockUseTopPatterns = vi.fn();
vi.mock("@/hooks/useTopPatterns", () => ({
  useTopPatterns: (...args: unknown[]) => mockUseTopPatterns(...args),
}));

const { TrendsPatternThesisHero } = await import("./TrendsPatternThesisHero");

beforeEach(() => {
  mockUseTopPatterns.mockReset();
});

afterEach(() => {
  cleanup();
});

const samplePattern = (overrides: Partial<TopPattern> = {}): TopPattern => ({
  id: "p1",
  display_name: "Hướng dẫn + mặt người",
  weekly_instance_count: 0,
  weekly_instance_count_prev: 0,
  niche_video_count: 3,
  instance_count: 8,
  niche_spread: [4],
  avg_views: 200_000,
  lift_vs_niche: 2.4,
  sample_hook: "Mình dùng iPad Pro 6 tháng rồi và…",
  videos: [
    {
      video_id: "v1",
      thumbnail_url: "https://media.getviews.vn/thumbnails/v1.webp",
      creator_handle: "an.tech",
      views: 250_000,
      tiktok_url: null,
    },
  ],
  video_pool: [
    {
      video_id: "v1",
      thumbnail_url: "https://media.getviews.vn/thumbnails/v1.webp",
      creator_handle: "an.tech",
      views: 250_000,
      tiktok_url: null,
    },
  ],
  tier: "strong",
  structure: ["Mở: câu hỏi cá nhân (0-2s)", "Setup", "Body", "Payoff"],
  why: "why",
  careful: "careful",
  angles: null,
  ...overrides,
});

describe("TrendsPatternThesisHero", () => {
  it("renders the week kicker + niche name (uppercased)", () => {
    mockUseTopPatterns.mockReturnValue({ data: [samplePattern()] });
    const { getByText } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Công nghệ"
        weekKicker="TUẦN 17 · 22.4—28.4"
        weekAnalyzedCount={301}
        totalAnalyzedInNiche={47288}
      />,
    );
    expect(getByText(/TUẦN 17 · 22\.4—28\.4 · NGÁCH CÔNG NGHỆ/)).toBeTruthy();
  });

  it("leads with strong-tier count when ≥1 strong pattern exists (Sprint 7c)", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [
        samplePattern({ id: "a", tier: "strong" }),
        samplePattern({ id: "b", tier: "strong" }),
        samplePattern({ id: "c", tier: "early" }),
      ],
    });
    const { getByRole } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={137}
        totalAnalyzedInNiche={324}
      />,
    );
    const h1 = getByRole("heading", { level: 1 });
    expect(h1.textContent).toContain("2 công thức");
    expect(h1.textContent).toContain("đang bứt phá trong ngách Skincare tuần này");
    expect(h1.textContent).toContain("(+1 dấu hiệu sớm)");
  });

  it("falls back to early-tier framing when no strong patterns exist", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [
        samplePattern({ id: "a", tier: "early", lift_vs_niche: 2.0 }),
      ],
    });
    const { getByRole } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={null}
        totalAnalyzedInNiche={null}
      />,
    );
    const h1 = getByRole("heading", { level: 1 });
    expect(h1.textContent).toContain("1 dấu hiệu sớm");
    expect(h1.textContent).toContain("đang bứt phá trong ngách Skincare tuần này");
    expect(h1.textContent).toContain("đáng theo dõi");
  });

  it("shows the 'no nổi bật' empty headline when no patterns of any tier exist", () => {
    mockUseTopPatterns.mockReturnValue({ data: [] });
    const { getByRole, getByText } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Tài chính"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={50}
        totalAnalyzedInNiche={300}
      />,
    );
    const h1 = getByRole("heading", { level: 1 });
    expect(h1.textContent).toContain("Tuần này chưa thấy công thức nổi bật trong ngách Tài chính");
    // Body text invites patience, doesn't blame the user.
    expect(getByText(/Đang theo dõi/)).toBeTruthy();
  });

  it("renders the top pattern spotlight using structure[0] (Mở: prefix stripped)", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [
        samplePattern({
          structure: ["Mở: câu hỏi cá nhân về sản phẩm (0-2s)", "Setup", "Body", "Payoff"],
          tier: "strong",
          lift_vs_niche: 2.4,
        }),
      ],
    });
    const { getByText } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={137}
        totalAnalyzedInNiche={324}
      />,
    );
    expect(getByText(/câu hỏi cá nhân về sản phẩm \(0-2s\)/)).toBeTruthy();
    expect(getByText(/Đứng đầu/)).toBeTruthy();
  });

  it("describes lift in plain Vietnamese ('ăn gấp X lần view trung bình ngách'), not '↑ X×' jargon", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [samplePattern({ tier: "strong", lift_vs_niche: 2.4 })],
    });
    const { getByText, queryByText } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={137}
        totalAnalyzedInNiche={324}
      />,
    );
    expect(getByText(/Ăn gấp 2\.4 lần view trung bình ngách/)).toBeTruthy();
    expect(queryByText(/↑ 2\.4×/)).toBeNull();
  });

  it("flags early-tier lift descriptions with 'đang theo dõi'", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [samplePattern({ tier: "early", lift_vs_niche: 13.7 })],
    });
    const { getByText } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={null}
        totalAnalyzedInNiche={null}
      />,
    );
    expect(getByText(/Ăn gấp 14 lần view trung bình ngách \(đang theo dõi\)/)).toBeTruthy();
  });

  it("renders the corpus caption with both total and weekly when both present", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [samplePattern()],
    });
    const { getByText } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={137}
        totalAnalyzedInNiche={324}
      />,
    );
    expect(getByText(/Cơ sở dữ liệu · 324 video ngách · 137 mới tuần này/)).toBeTruthy();
  });

  it("hides the corpus caption when both counts are null", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [samplePattern()],
    });
    const { container } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={null}
        totalAnalyzedInNiche={null}
      />,
    );
    expect(container.textContent).not.toContain("Cơ sở dữ liệu");
  });

  it("never surfaces the broken weekly_instance_count metrics from the old hero", () => {
    // Sprint 7c regression guard — the old hero leaked "0 pattern đang có
    // nhịp" / "TỔNG PATTERN" / "ĐỘ MỚI" / "Pattern còn cửa khai thác".
    // None of these analyst-coded labels should reappear.
    mockUseTopPatterns.mockReturnValue({ data: [samplePattern()] });
    const { container } = render(
      <TrendsPatternThesisHero
        patternScope={heroScope}
        nicheLabel="Skincare"
        weekKicker="TUẦN 19"
        weekAnalyzedCount={137}
        totalAnalyzedInNiche={324}
      />,
    );
    expect(container.textContent).not.toContain("đang có nhịp");
    expect(container.textContent).not.toContain("TỔNG PATTERN");
    expect(container.textContent).not.toContain("ĐỘ MỚI");
    expect(container.textContent).not.toContain("còn cửa khai thác");
  });
});
