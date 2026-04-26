/**
 * PR-cleanup-C Studio Home — StudioHero ranked-list render-test.
 *
 * Replaces the HomeMorningRitual + NextVideosCard pair with the
 * design pack's single ranked-list layout (home.jsx:1154-1248).
 */
import { cleanup, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DailyRitual, RitualScript } from "@/hooks/useDailyRitual";

const mockUseDailyRitual = vi.fn();
vi.mock("@/hooks/useDailyRitual", () => ({
  useDailyRitual: (...args: unknown[]) => mockUseDailyRitual(...args),
}));

const { StudioHero } = await import("./StudioHero");

beforeEach(() => {
  mockUseDailyRitual.mockReset();
});

afterEach(() => {
  cleanup();
});

const sampleScript = (overrides: Partial<RitualScript> = {}): RitualScript => ({
  hook_type_en: "comparison",
  hook_type_vi: "So sánh",
  title_vi: "Mình vừa test tai 2 triệu và thật sự…",
  why_works: "Pattern so sánh giá đang ăn nhất tuần qua trong ngách Tech.",
  retention_est_pct: 72,
  shot_count: 6,
  length_sec: 32,
  ...overrides,
});

const sampleRitual = (overrides: Partial<DailyRitual> = {}): DailyRitual => ({
  generated_for_date: "2026-04-26",
  niche_id: 4,
  adequacy: "hook_effectiveness",
  scripts: [sampleScript(), sampleScript({ hook_type_en: "story", title_vi: "Câu chuyện thất bại" })],
  generated_at: new Date().toISOString(),
  ...overrides,
});

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("StudioHero", () => {
  it("renders a row per ritual script with rank, hook badge, and serif title", () => {
    mockUseDailyRitual.mockReturnValue({
      data: sampleRitual({
        scripts: [
          sampleScript({ title_vi: "First hook" }),
          sampleScript({ title_vi: "Second hook" }),
        ],
      }),
      emptyReason: null,
      isPending: false,
      refetch: vi.fn(),
    });
    const { getAllByRole, getByText } = wrap(<StudioHero nicheId={4} />);
    const rows = getAllByRole("button");
    expect(rows).toHaveLength(2);
    expect(getByText(/First hook/)).toBeTruthy();
    expect(getByText(/Second hook/)).toBeTruthy();
    expect(getByText("HOOK #1")).toBeTruthy();
    expect(getByText("HOOK #2")).toBeTruthy();
    // Pad-zero rank labels.
    expect(getByText("01")).toBeTruthy();
    expect(getByText("02")).toBeTruthy();
  });

  it("renders the SCRIPT SẴN pill with shot count + length per row", () => {
    mockUseDailyRitual.mockReturnValue({
      data: sampleRitual({
        scripts: [sampleScript({ shot_count: 5, length_sec: 22 })],
      }),
      emptyReason: null,
      isPending: false,
      refetch: vi.fn(),
    });
    const { getByText } = wrap(<StudioHero nicheId={4} />);
    expect(getByText(/SCRIPT SẴN · 5 shot · 22s/)).toBeTruthy();
  });

  it("renders the retention estimate + MỞ SCRIPT CTA", () => {
    mockUseDailyRitual.mockReturnValue({
      data: sampleRitual({
        scripts: [sampleScript({ retention_est_pct: 65 })],
      }),
      emptyReason: null,
      isPending: false,
      refetch: vi.fn(),
    });
    const { getByText } = wrap(<StudioHero nicheId={4} />);
    expect(getByText(/▲ ~65%/)).toBeTruthy();
    expect(getByText(/MỞ SCRIPT/)).toBeTruthy();
  });

  it("renders an empty stub when ritual data is null", () => {
    mockUseDailyRitual.mockReturnValue({
      data: null,
      emptyReason: "ritual_no_row",
      isPending: false,
      refetch: vi.fn(),
    });
    const { getByText } = wrap(<StudioHero nicheId={4} />);
    expect(getByText(/Đang tạo kịch bản cho ngày đầu/)).toBeTruthy();
  });

  it("renders the niche-stale variant of the empty stub", () => {
    mockUseDailyRitual.mockReturnValue({
      data: null,
      emptyReason: "ritual_niche_stale",
      isPending: false,
      refetch: vi.fn(),
    });
    const { getByText } = wrap(<StudioHero nicheId={4} />);
    expect(getByText(/Kịch bản mới đang chuẩn bị cho ngách này/)).toBeTruthy();
  });

  it("renders pulse-style skeletons while pending", () => {
    mockUseDailyRitual.mockReturnValue({
      data: null,
      emptyReason: null,
      isPending: true,
      refetch: vi.fn(),
    });
    const { container } = wrap(<StudioHero nicheId={4} />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });
});
