/**
 * PR-T3 Trends — TrendsPatternGrid render-test.
 */
import { cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TopPattern } from "@/hooks/useTopPatterns";

const mockUseTopPatterns = vi.fn();
vi.mock("@/hooks/useTopPatterns", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useTopPatterns")>(
    "@/hooks/useTopPatterns",
  );
  return {
    ...actual,
    useTopPatterns: (...args: unknown[]) => mockUseTopPatterns(...args),
  };
});

const { TrendsPatternGrid } = await import("./TrendsPatternGrid");

beforeEach(() => {
  mockUseTopPatterns.mockReset();
});

afterEach(() => {
  cleanup();
});

const samplePattern = (id: string, overrides: Partial<TopPattern> = {}): TopPattern => ({
  id,
  display_name: `Pattern ${id}`,
  weekly_instance_count: 10,
  weekly_instance_count_prev: 4,
  instance_count: 30,
  niche_spread: [4],
  avg_views: 100_000,
  sample_hook: "Sample",
  videos: [],
  structure: null,
  why: null,
  careful: null,
  angles: null,
  ...overrides,
});

describe("TrendsPatternGrid", () => {
  it("renders the §I header + heading + click hint", () => {
    // Header copy was updated from "đang sống · cập nhật mỗi tuần" to
    // "đang chạy tốt" + a click-hint. The "cập nhật mỗi tuần" caption
    // was dropped entirely. Test now mirrors the actual TrendsPatternGrid
    // header chrome (lines 35-44 in TrendsPatternGrid.tsx).
    mockUseTopPatterns.mockReturnValue({ data: [samplePattern("p1")], isPending: false });
    const { getByText } = render(<TrendsPatternGrid nicheId={4} />);
    expect(getByText("§ I — PATTERN")).toBeTruthy();
    expect(getByText(/6 công thức đang chạy tốt/)).toBeTruthy();
    expect(getByText(/CLICK PATTERN → MỞ FULL DECK/)).toBeTruthy();
  });

  it("renders one card per pattern", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [samplePattern("p1"), samplePattern("p2"), samplePattern("p3")],
      isPending: false,
    });
    const { getAllByLabelText } = render(<TrendsPatternGrid nicheId={4} />);
    const cards = getAllByLabelText(/Mở pattern:/);
    expect(cards).toHaveLength(3);
  });

  it("renders a 6-cell skeleton while pending", () => {
    mockUseTopPatterns.mockReturnValue({ data: undefined, isPending: true });
    const { container } = render(<TrendsPatternGrid nicheId={4} />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(6);
  });

  it("renders an empty stub when no patterns are returned", () => {
    mockUseTopPatterns.mockReturnValue({ data: [], isPending: false });
    const { getByText } = render(<TrendsPatternGrid nicheId={4} />);
    expect(getByText(/Chưa đủ pattern/)).toBeTruthy();
  });
});
