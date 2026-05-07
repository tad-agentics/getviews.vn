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
  niche_video_count: 5,
  instance_count: 30,
  niche_spread: [4],
  avg_views: 200_000,
  lift_vs_niche: 2.0,
  sample_hook: "Sample",
  videos: [],
  // Sprint 5 — only deck-synthesized patterns reach the FE.
  structure: ["Mở: hook (0-2s)", "Setup", "Body", "Payoff"],
  why: "Why it works.",
  careful: "Be careful.",
  angles: null,
  ...overrides,
});

describe("TrendsPatternGrid", () => {
  it("renders the §I header with the Sprint 5 reshape heading", () => {
    mockUseTopPatterns.mockReturnValue({ data: [samplePattern("p1")], isPending: false });
    const { getByText } = render(<TrendsPatternGrid nicheId={4} />);
    expect(getByText("§ I — PATTERN")).toBeTruthy();
    expect(getByText(/Công thức từ video viral trong ngách/)).toBeTruthy();
    expect(getByText(/CLICK → HỌC FULL DECK/)).toBeTruthy();
  });

  it("renders one card per pattern", () => {
    mockUseTopPatterns.mockReturnValue({
      data: [samplePattern("p1"), samplePattern("p2"), samplePattern("p3")],
      isPending: false,
    });
    const { getAllByLabelText } = render(<TrendsPatternGrid nicheId={4} />);
    const cards = getAllByLabelText(/Mở công thức:/);
    expect(cards).toHaveLength(3);
  });

  it("renders a 6-cell skeleton while pending", () => {
    mockUseTopPatterns.mockReturnValue({ data: undefined, isPending: true });
    const { container } = render(<TrendsPatternGrid nicheId={4} />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(6);
  });

  it("renders the Sprint 5 empty-state copy when no qualified patterns are returned", () => {
    mockUseTopPatterns.mockReturnValue({ data: [], isPending: false });
    const { getByText } = render(<TrendsPatternGrid nicheId={4} />);
    expect(getByText(/Chưa đủ công thức có lift cao/)).toBeTruthy();
  });
});
