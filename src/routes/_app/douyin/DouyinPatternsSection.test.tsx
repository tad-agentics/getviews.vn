/**
 * D5e (2026-06-05) — DouyinPatternsSection render tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { DouyinNiche, DouyinPattern } from "@/lib/api-types";

import { DouyinPatternsSection } from "./DouyinPatternsSection";


beforeEach(() => {
  // Pin "today" so the freshness caveat tests don't drift.
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-06-08T12:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
  cleanup();
});


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

  it("renders the error banner with retry button when isError is true", () => {
    const onRetry = vi.fn();
    render(
      <DouyinPatternsSection
        patterns={[]}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
        isError={true}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText(/Không tải được Pattern signals/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Thử lại/ }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("hides the retry button when onRetry isn't provided", () => {
    render(
      <DouyinPatternsSection
        patterns={[]}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
        isError={true}
      />,
    );
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Thử lại/ })).toBeNull();
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

  it("renders the week_of label as DD/MM/YYYY in the header", () => {
    render(
      <DouyinPatternsSection
        patterns={[
          _pattern(1, 1, { week_of: "2026-06-01" }),
          _pattern(1, 2, { week_of: "2026-06-01" }),
          _pattern(1, 3, { week_of: "2026-06-01" }),
        ]}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
      />,
    );
    expect(screen.getByText(/Tuần 01\/06\/2026/)).toBeTruthy();
    // No staleness caveat — computed_at is 2026-06-01 (≤ 13 days old vs.
    // pinned "today" = 2026-06-08).
    expect(screen.queryByText(/có thể chưa cập nhật/)).toBeNull();
  });

  it("picks the most recent week_of when patterns span multiple weeks", () => {
    render(
      <DouyinPatternsSection
        patterns={[
          _pattern(1, 1, { week_of: "2026-05-25" }),
          _pattern(1, 2, { week_of: "2026-06-01" }),
          _pattern(1, 3, { week_of: "2026-06-01" }),
        ]}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
      />,
    );
    expect(screen.getByText(/Tuần 01\/06\/2026/)).toBeTruthy();
    expect(screen.queryByText(/Tuần 25\/05\/2026/)).toBeNull();
  });

  it("surfaces the staleness caveat when computed_at is older than 13 days", () => {
    render(
      <DouyinPatternsSection
        patterns={[
          _pattern(1, 1, {
            week_of: "2026-05-18",
            computed_at: "2026-05-18T21:00:00+00:00",  // 21 days before pinned "today"
          }),
          _pattern(1, 2, {
            week_of: "2026-05-18",
            computed_at: "2026-05-18T21:00:00+00:00",
          }),
          _pattern(1, 3, {
            week_of: "2026-05-18",
            computed_at: "2026-05-18T21:00:00+00:00",
          }),
        ]}
        niches={_NICHES}
        activeNicheSlug={null}
        isLoading={false}
      />,
    );
    expect(screen.getByText(/có thể chưa cập nhật/)).toBeTruthy();
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
