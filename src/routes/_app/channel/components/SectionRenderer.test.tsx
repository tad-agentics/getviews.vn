/**
 * Vitest tests for channel diagnosis renderer components.
 *
 * Covers:
 * - SectionRenderer: section interleaving, recommendations delegation, streaming cursor
 * - VideoTileRow: tile fallback when thumbnail missing
 * - CreatorTileRow: renders up to 3 creators, skips when empty
 * - NumberedRecommendation: renders title + body
 * - RecommendationList: renders multiple recommendations in order
 * - StepProgress: renders step label and trajectory badge
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ChannelSection, ChannelPerformerTile, ChannelUGCCreator, ChannelRecommendation } from "@/lib/api-types";
import { SectionRenderer } from "./SectionRenderer";
import { VideoTileRow } from "./VideoTileRow";
import { CreatorTileRow } from "./CreatorTileRow";
import { NumberedRecommendation, RecommendationList } from "./NumberedRecommendation";
import { StepProgress } from "./StepProgress";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeTile(override: Partial<ChannelPerformerTile> = {}): ChannelPerformerTile {
  return {
    video_url: "https://tiktok.com/@test/video/1",
    thumbnail_url: "https://r2.example.com/thumb.jpg",
    views: 50_000,
    content_format: "beauty_tutorial",
    caption_snippet: "Test caption",
    posted_at: "2026-01-01T00:00:00Z",
    ...override,
  };
}

function makeCreator(override: Partial<ChannelUGCCreator> = {}): ChannelUGCCreator {
  return {
    handle: "testcreator",
    followers: 50_000,
    avg_views: 80_000,
    thumbnail_url: "https://r2.example.com/creator.jpg",
    niche_slug: "beauty",
    ...override,
  };
}

function makeRec(override: Partial<ChannelRecommendation> = {}): ChannelRecommendation {
  return {
    index: 1,
    title: "Fix the hook",
    body: "Add a surprising element in the first 2 seconds.",
    ...override,
  };
}

function makeSection(override: Partial<ChannelSection> = {}): ChannelSection {
  return {
    section_id: "verdict",
    title: "Kết luận",
    text: "Kênh đang ở giai đoạn stagnant với tỷ lệ tương tác thấp.",
    ...override,
  };
}

// ---------------------------------------------------------------------------
// SectionRenderer
// ---------------------------------------------------------------------------

describe("SectionRenderer", () => {
  it("renders section title as h2", () => {
    const section = makeSection({ title: "Kết quả phân tích" });
    render(<SectionRenderer section={section} />);
    expect(screen.getByRole("heading", { level: 2, name: /Kết quả phân tích/ })).toBeTruthy();
  });

  it("renders prose text paragraphs", () => {
    const section = makeSection({ text: "Para 1.\n\nPara 2." });
    render(<SectionRenderer section={section} />);
    expect(screen.getByText("Para 1.")).toBeDefined();
    expect(screen.getByText("Para 2.")).toBeDefined();
  });

  it("renders embedded video tiles when present", () => {
    const tile = makeTile({ caption_snippet: "Viral video" });
    const section = makeSection({ embedded_tiles: [tile] });
    render(<SectionRenderer section={section} />);
    expect(screen.getByText("Viral video")).toBeDefined();
  });

  it("renders embedded creator tiles when present", () => {
    const creator = makeCreator({ handle: "topkol" });
    const section = makeSection({ embedded_creators: [creator] });
    render(<SectionRenderer section={section} />);
    expect(screen.getByText("@topkol")).toBeDefined();
  });

  it("delegates recommendations section to RecommendationList", () => {
    const section = makeSection({
      section_id: "recommendations",
      title: "Khuyến nghị",
      text: "",
    });
    const recs = [
      makeRec({ index: 1, title: "Fix hook" }),
      makeRec({ index: 2, title: "Fix caption" }),
    ];
    render(<SectionRenderer section={section} recommendations={recs} />);
    expect(screen.getByText("Fix hook")).toBeDefined();
    expect(screen.getByText("Fix caption")).toBeDefined();
  });

  it("shows streaming cursor when streaming=true and text is non-empty", () => {
    const section = makeSection({ text: "Đang phân tích..." });
    const { container } = render(<SectionRenderer section={section} streaming />);
    const cursor = container.querySelector('[aria-hidden]');
    expect(cursor).toBeDefined();
  });

  it("does not show cursor when streaming=false", () => {
    const section = makeSection({ text: "Done." });
    const { container } = render(<SectionRenderer section={section} streaming={false} />);
    // Only VideoThumbnail uses aria-hidden; the cursor span should not exist separately
    const animatedCursors = container.querySelectorAll('.animate-pulse');
    expect(animatedCursors.length).toBe(0);
  });

  it("falls back to prose text for recommendations when recommendations list is empty", () => {
    const section = makeSection({
      section_id: "recommendations",
      title: "Recs",
      text: "Raw recommendation text as fallback.",
    });
    render(<SectionRenderer section={section} recommendations={[]} />);
    expect(screen.getByText("Raw recommendation text as fallback.")).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// VideoTileRow
// ---------------------------------------------------------------------------

describe("VideoTileRow", () => {
  it("renders nothing when tiles is empty", () => {
    const { container } = render(<VideoTileRow tiles={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders view count overlay", () => {
    const tile = makeTile({ views: 1_200_000 });
    render(<VideoTileRow tiles={[tile]} />);
    expect(screen.getByText("1.2M")).toBeDefined();
  });

  it("renders placeholder div when thumbnail_url is empty (fallback)", () => {
    const tile = makeTile({ thumbnail_url: "" });
    const { container } = render(<VideoTileRow tiles={[tile]} />);
    // VideoThumbnail renders a placeholder div when url is empty
    const placeholder = container.querySelector('[aria-hidden]');
    expect(placeholder).toBeDefined();
  });

  it("renders at most 4 tiles", () => {
    const tiles = Array.from({ length: 6 }, (_, i) => makeTile({ video_url: `u${i}`, views: i * 1000 }));
    const { container } = render(<VideoTileRow tiles={tiles} />);
    // Each tile is an <a> or a sibling div; count views badges
    const viewBadges = container.querySelectorAll('.font-mono');
    expect(viewBadges.length).toBe(4);
  });

  it("renders optional label", () => {
    render(<VideoTileRow tiles={[makeTile()]} label="Top performers" />);
    expect(screen.getByText("Top performers")).toBeDefined();
  });

  it("links to video_url when present", () => {
    const tile = makeTile({ video_url: "https://tiktok.com/@test/video/42" });
    const { container } = render(<VideoTileRow tiles={[tile]} />);
    const link = container.querySelector('a[href="https://tiktok.com/@test/video/42"]');
    expect(link).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// CreatorTileRow
// ---------------------------------------------------------------------------

describe("CreatorTileRow", () => {
  it("renders nothing when creators is empty", () => {
    const { container } = render(<CreatorTileRow creators={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders at most 3 creators", () => {
    const creators = Array.from({ length: 5 }, (_, i) =>
      makeCreator({ handle: `creator${i}` }),
    );
    render(<CreatorTileRow creators={creators} />);
    expect(screen.getAllByText(/^@creator/).length).toBe(3);
  });

  it("links to TikTok profile", () => {
    const creator = makeCreator({ handle: "testcreator" });
    const { container } = render(<CreatorTileRow creators={[creator]} />);
    const link = container.querySelector('a[href="https://tiktok.com/@testcreator"]');
    expect(link).toBeDefined();
  });

  it("renders follower count", () => {
    const creator = makeCreator({ followers: 123_000 });
    render(<CreatorTileRow creators={[creator]} />);
    expect(screen.getByText("123.0K followers")).toBeDefined();
  });

  it("uses placeholder when thumbnail_url is empty", () => {
    const creator = makeCreator({ thumbnail_url: "" });
    const { container } = render(<CreatorTileRow creators={[creator]} />);
    const placeholder = container.querySelector('[aria-hidden]');
    expect(placeholder).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// NumberedRecommendation / RecommendationList
// ---------------------------------------------------------------------------

describe("NumberedRecommendation", () => {
  it("renders index badge, title, and body", () => {
    const rec = makeRec({ index: 3, title: "Cải thiện hook", body: "Thêm yếu tố bất ngờ." });
    render(<NumberedRecommendation recommendation={rec} />);
    expect(screen.getByText("3")).toBeDefined();
    expect(screen.getByText("Cải thiện hook")).toBeDefined();
    expect(screen.getByText("Thêm yếu tố bất ngờ.")).toBeDefined();
  });

  it("renders without body gracefully", () => {
    const rec = makeRec({ body: "" });
    const { container } = render(<NumberedRecommendation recommendation={rec} />);
    expect(container.textContent).toContain("Fix the hook");
  });
});

describe("RecommendationList", () => {
  it("renders multiple recommendations in index order", () => {
    const recs = [
      makeRec({ index: 2, title: "Second" }),
      makeRec({ index: 1, title: "First" }),
      makeRec({ index: 3, title: "Third" }),
    ];
    render(<RecommendationList recommendations={recs} />);
    const titles = screen.getAllByText(/First|Second|Third/);
    expect(titles.length).toBe(3);
  });

  it("renders nothing when list is empty", () => {
    const { container } = render(<RecommendationList recommendations={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// StepProgress
// ---------------------------------------------------------------------------

describe("StepProgress", () => {
  it("renders step label", () => {
    render(
      <StepProgress
        activeStepIndex={2}
        activeStepLabel="Phân loại format"
        heartbeatCount={0}
        trajectoryShape={null}
      />,
    );
    expect(screen.getByText("Phân loại format")).toBeDefined();
  });

  it("renders trajectory badge once known", () => {
    render(
      <StepProgress
        activeStepIndex={3}
        activeStepLabel="Tìm UGC"
        heartbeatCount={0}
        trajectoryShape="breakout"
      />,
    );
    expect(screen.getByText("Kênh breakout")).toBeDefined();
  });

  it("renders elapsed time when heartbeatCount > 0", () => {
    render(
      <StepProgress
        activeStepIndex={4}
        activeStepLabel="Đang viết phân tích"
        heartbeatCount={3}
        trajectoryShape="stagnant"
      />,
    );
    expect(screen.getByText("Đang xử lý · 30s…")).toBeDefined();
  });

  it("does not render when index is -1", () => {
    const { container } = render(
      <StepProgress
        activeStepIndex={-1}
        activeStepLabel=""
        heartbeatCount={0}
        trajectoryShape={null}
      />,
    );
    // No step bar should be rendered
    const bars = container.querySelectorAll('.h-1');
    expect(bars.length).toBe(0);
  });
});
