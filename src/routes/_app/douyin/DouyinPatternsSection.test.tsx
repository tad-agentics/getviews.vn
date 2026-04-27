/**
 * D5e (2026-06-05) — DouyinPatternsSection render tests.
 */

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { DouyinNiche, DouyinPattern } from "@/lib/api-types";

import { DouyinPatternsSection } from "./DouyinPatternsSection";


afterEach(() => cleanup());


const _NICHES: DouyinNiche[] = [
  { id: 1, slug: "wellness", name_vn: "Wellness", name_zh: "养生", name_en: "Wellness" },
  { id: 2, slug: "tech", name_vn: "Tech", name_zh: "科技", name_en: "Tech" },
];


function _pattern(
  niche_id: number,
  rank: 1 | 2 | 3,
  overrides: Partial<DouyinPattern> = {},
): DouyinPattern {
  return {
    id: `pat-${niche_id}-${rank}`,
    niche_id,
    week_of: "2026-06-01",
    rank,
    name_vn: `Pattern ${niche_id}/${rank}`,
    name_zh: null,
    hook_template_vi: "3 việc trước khi ___",
    format_signal_vi: "POV cận cảnh, voiceover thì thầm.",
    sample_video_ids: ["v1", "v2", "v3"],
    cn_rise_pct_avg: 25.0,
    computed_at: "2026-06-01T21:00:00+00:00",
    ...overrides,
  };
}


describe("DouyinPatternsSection", () => {
  it("renders the loading state when isLoading is true", () => {
    render(
      <DouyinPatternsSection
        patterns={[]}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={true}
      />,
    );
    expect(screen.getByLabelText(/Đang tải Pattern signals/)).toBeTruthy();
  });

  it("renders nothing when patterns is empty (no cron / no data)", () => {
    const { container } = render(
      <DouyinPatternsSection
        patterns={[]}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders one row per niche when no chip filter is active", () => {
    const patterns: DouyinPattern[] = [
      _pattern(1, 1), _pattern(1, 2), _pattern(1, 3),
      _pattern(2, 1), _pattern(2, 2), _pattern(2, 3),
    ];
    render(
      <DouyinPatternsSection
        patterns={patterns}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
      />,
    );
    expect(screen.getByText(/§ I — Pattern signals/)).toBeTruthy();
    // Per-niche heading rows.
    expect(screen.getByText("Wellness")).toBeTruthy();
    expect(screen.getByText("Tech")).toBeTruthy();
    // 6 cards total.
    expect(screen.getAllByText(/Pattern \d+\/\d+/).length).toBe(6);
  });

  it("scopes to the active niche when a chip is selected (no per-niche heading)", () => {
    const patterns: DouyinPattern[] = [
      _pattern(1, 1), _pattern(1, 2), _pattern(1, 3),
      _pattern(2, 1), _pattern(2, 2), _pattern(2, 3),
    ];
    render(
      <DouyinPatternsSection
        patterns={patterns}
        niches={_NICHES}
        activeNicheSlug="tech"
        isLoading={false}
      />,
    );
    // Only Tech rows visible.
    expect(screen.getByText("Pattern 2/1")).toBeTruthy();
    expect(screen.getByText("Pattern 2/2")).toBeTruthy();
    expect(screen.getByText("Pattern 2/3")).toBeTruthy();
    expect(screen.queryByText("Pattern 1/1")).toBeNull();
    // The per-niche heading is suppressed for single-niche filters.
    expect(screen.queryByText("Tech")).toBeNull();
  });

  it("renders nothing when the active niche has no patterns", () => {
    const { container } = render(
      <DouyinPatternsSection
        patterns={[_pattern(1, 1), _pattern(1, 2), _pattern(1, 3)]}
        niches={_NICHES}
        activeNicheSlug="tech"
        isLoading={false}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("orders rows by rank within each niche group", () => {
    // Patterns supplied in shuffled order.
    const patterns: DouyinPattern[] = [
      _pattern(1, 3), _pattern(1, 1), _pattern(1, 2),
    ];
    const { container } = render(
      <DouyinPatternsSection
        patterns={patterns}
        niches={_NICHES}
        activeNicheSlug="wellness"
        isLoading={false}
      />,
    );
    const ranks = Array.from(
      container.querySelectorAll("article[data-rank]"),
    ).map((el) => el.getAttribute("data-rank"));
    expect(ranks).toEqual(["1", "2", "3"]);
  });

  it("orders niche groups by niche_id ASC", () => {
    const patterns: DouyinPattern[] = [
      _pattern(2, 1), _pattern(2, 2), _pattern(2, 3),
      _pattern(1, 1), _pattern(1, 2), _pattern(1, 3),
    ];
    const { container } = render(
      <DouyinPatternsSection
        patterns={patterns}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
      />,
    );
    const articles = Array.from(container.querySelectorAll("article[data-niche-id]"));
    const niches = articles.map((el) => el.getAttribute("data-niche-id"));
    // First 3 articles are niche 1, next 3 are niche 2.
    expect(niches).toEqual(["1", "1", "1", "2", "2", "2"]);
  });
});
