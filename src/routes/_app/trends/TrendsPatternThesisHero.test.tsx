/**
 * PR-T2 Trends — TrendsPatternThesisHero render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 331-348.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NichePatternStats } from "@/hooks/useNichePatternStats";

const mockUseNichePatternStats = vi.fn();
vi.mock("@/hooks/useNichePatternStats", () => ({
  useNichePatternStats: (...args: unknown[]) => mockUseNichePatternStats(...args),
}));

const { TrendsPatternThesisHero } = await import("./TrendsPatternThesisHero");

beforeEach(() => {
  mockUseNichePatternStats.mockReset();
});

afterEach(() => {
  cleanup();
});

const sampleStats: NichePatternStats = {
  total: 14,
  patterns_active_this_week: 7,
  fresh: 9,
  fresh_pct: "64%",
};

const defaultCounts = { weekAnalyzedCount: 301, totalAnalyzedInNiche: 47288 };

describe("TrendsPatternThesisHero", () => {
  it("renders the week kicker, niche name, and pattern-first H1", () => {
    mockUseNichePatternStats.mockReturnValue({ data: sampleStats });
    const { getByText, getByRole } = render(
      <TrendsPatternThesisHero
        nicheId={4}
        nicheLabel="Công nghệ"
        weekKicker="TUẦN 17 · 22.4—28.4"
        weekAnalyzedCount={301}
        totalAnalyzedInNiche={47288}
      />,
    );
    expect(getByText(/TUẦN 17 · 22\.4—28\.4 · NGÁCH CÔNG NGHỆ/)).toBeTruthy();
    const h1 = getByRole("heading", { level: 1 });
    expect(h1.textContent).toContain("7 pattern");
    expect(h1.textContent).toContain("đang có nhịp trong ngách");
    expect(h1.textContent).toContain("301 video mới vào kho");
    expect(h1.textContent).toContain("47.288");
  });

  it("renders the 3-stat strip: pattern week, total patterns, fresh %", () => {
    mockUseNichePatternStats.mockReturnValue({ data: sampleStats });
    const { getAllByText } = render(
      <TrendsPatternThesisHero
        nicheId={4}
        nicheLabel="Công nghệ"
        weekKicker="TUẦN 17"
        {...defaultCounts}
      />,
    );
    expect(getAllByText("PATTERN ~7 NGÀY").length).toBeGreaterThan(0);
    expect(getAllByText("TỔNG PATTERN").length).toBeGreaterThan(0);
    expect(getAllByText("7").length).toBeGreaterThan(0);
    expect(getAllByText("14").length).toBeGreaterThan(0);
    expect(getAllByText("ĐỘ MỚI").length).toBeGreaterThan(0);
    expect(getAllByText("64%").length).toBeGreaterThan(0);
  });

  it("renders em-dash placeholders when stats and counts are unavailable", () => {
    mockUseNichePatternStats.mockReturnValue({ data: null });
    const { getByRole, getAllByText } = render(
      <TrendsPatternThesisHero
        nicheId={4}
        nicheLabel="Công nghệ"
        weekKicker="TUẦN 17"
        weekAnalyzedCount={null}
        totalAnalyzedInNiche={null}
      />,
    );
    const h1 = getByRole("heading", { level: 1 });
    expect(h1.textContent).toMatch(/—\s*pattern/);
    expect(h1.textContent).toContain("đang có nhịp");
    expect(getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });

  it("uppercases the niche label in the kicker line", () => {
    mockUseNichePatternStats.mockReturnValue({ data: sampleStats });
    const { getByText } = render(
      <TrendsPatternThesisHero
        nicheId={4}
        nicheLabel="ẩm thực"
        weekKicker="TUẦN 17"
        weekAnalyzedCount={50}
        totalAnalyzedInNiche={1000}
      />,
    );
    expect(getByText(/NGÁCH ẨM THỰC/)).toBeTruthy();
  });

  it("uses the accent color span on the leading pattern count", () => {
    mockUseNichePatternStats.mockReturnValue({ data: sampleStats });
    const { getByText } = render(
      <TrendsPatternThesisHero
        nicheId={4}
        nicheLabel="Công nghệ"
        weekKicker="TUẦN 17"
        {...defaultCounts}
      />,
    );
    const span = getByText(/7 pattern/);
    expect(span.tagName).toBe("SPAN");
    expect(span.className).toMatch(/gv-accent/);
  });
});
