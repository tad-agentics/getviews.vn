/**
 * PR-cleanup-C Studio Home — StudioHero ranked-list render-test.
 *
 * Replaces the HomeMorningRitual + NextVideosCard pair with the
 * design pack's single ranked-list layout (home.jsx:1154-1248).
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { DailyRitual, RitualScript } from "@/hooks/useDailyRitual";

const mockUseDailyRitual = vi.fn();
vi.mock("@/hooks/useDailyRitual", () => ({
  useDailyRitual: (...args: unknown[]) => mockUseDailyRitual(...args),
}));

const mockUseRitualEvidenceVideos = vi.fn();
vi.mock("@/hooks/useRitualEvidenceVideos", () => ({
  useRitualEvidenceVideos: (...args: unknown[]) => mockUseRitualEvidenceVideos(...args),
}));

const { StudioHero } = await import("./StudioHero");

beforeEach(() => {
  mockUseDailyRitual.mockReset();
  mockUseRitualEvidenceVideos.mockReset();
  // Default: no evidence loaded — tests that need data override.
  mockUseRitualEvidenceVideos.mockReturnValue({
    data: undefined,
    isPending: false,
    isError: false,
  });
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
      isError: false,
      error: undefined,
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
      isError: false,
      error: undefined,
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
      isError: false,
      error: undefined,
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
      isError: false,
      error: undefined,
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
      isError: false,
      error: undefined,
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
      isError: false,
      error: undefined,
      refetch: vi.fn(),
    });
    const { container } = wrap(<StudioHero nicheId={4} />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("renders the 'Xem N video tương tự' trigger only when evidence_video_ids has rows (L2.2 Sprint 4)", () => {
    mockUseDailyRitual.mockReturnValue({
      data: sampleRitual({
        scripts: [
          sampleScript({
            title_vi: "With evidence",
            evidence_video_ids: ["v1", "v2", "v3", "v4"],
          }),
          sampleScript({ title_vi: "Without evidence" }),
        ],
      }),
      emptyReason: null,
      isPending: false,
      isError: false,
      error: undefined,
      refetch: vi.fn(),
    });
    const { getAllByText } = wrap(<StudioHero nicheId={4} />);
    const triggers = getAllByText(/Xem 4 video tương tự/);
    // Only the first script has evidence — exactly one trigger renders.
    expect(triggers).toHaveLength(1);
  });

  it("expands the evidence strip and renders thumbnails when the trigger is clicked", () => {
    mockUseDailyRitual.mockReturnValue({
      data: sampleRitual({
        scripts: [
          sampleScript({
            title_vi: "Test row",
            evidence_video_ids: ["v1", "v2"],
          }),
        ],
      }),
      emptyReason: null,
      isPending: false,
      isError: false,
      error: undefined,
      refetch: vi.fn(),
    });
    // Strip starts collapsed (enabled=false) → returns empty.
    // After click: enabled=true → returns rows. Mock branches on the
    // ``enabled`` arg to keep the contract tight.
    mockUseRitualEvidenceVideos.mockImplementation(
      (_ids: string[], enabled: boolean) =>
        enabled
          ? {
              data: [
                {
                  video_id: "v1",
                  thumbnail_url: "https://example.com/v1.jpg",
                  creator_handle: "creator_a",
                  views: 1_500_000,
                },
                {
                  video_id: "v2",
                  thumbnail_url: null,
                  creator_handle: null,
                  views: 25_000,
                },
              ],
              isPending: false,
              isError: false,
            }
          : { data: undefined, isPending: false, isError: false },
    );
    const { getByText, queryByText, container } = wrap(<StudioHero nicheId={4} />);
    // Pre-click: thumbnails not in DOM.
    expect(queryByText("1.5M")).toBeNull();
    fireEvent.click(getByText(/Xem 2 video tương tự/));
    // Post-click: views labels render for both items.
    expect(getByText("1.5M")).toBeTruthy();
    expect(getByText("25.0K")).toBeTruthy();
    // The handle-bearing row renders as an anchor to the original TikTok URL;
    // the handle-less row falls back to a div (no link).
    const anchors = container.querySelectorAll("a[href*='tiktok.com']");
    expect(anchors).toHaveLength(1);
    expect(anchors[0]?.getAttribute("href")).toBe(
      "https://www.tiktok.com/@creator_a/video/v1",
    );
  });

  it("strips nested quotes from title_vi and English mechanism prefix from why_works", () => {
    mockUseDailyRitual.mockReturnValue({
      data: sampleRitual({
        scripts: [
          sampleScript({
            title_vi: '""Hôm nay đi mua serum?"',
            why_works:
              "identification — viewer đặt mình vào tình huống thử nghiệm thực tế của creator",
          }),
        ],
      }),
      emptyReason: null,
      isPending: false,
      isError: false,
      error: undefined,
      refetch: vi.fn(),
    });
    const { getByText, queryByText } = wrap(<StudioHero nicheId={4} />);
    expect(getByText(/Hôm nay đi mua serum/)).toBeTruthy();
    expect(queryByText(/identification —/)).toBeNull();
    expect(getByText(/viewer đặt mình vào tình huống/)).toBeTruthy();
  });

  it("renders a fetch-failure banner instead of the empty cron stub when the ritual query errors", () => {
    mockUseDailyRitual.mockReturnValue({
      data: null,
      emptyReason: null,
      isPending: false,
      isError: true,
      error: new Error("HTTP 500"),
      refetch: vi.fn(),
    });
    const { getByText } = wrap(<StudioHero nicheId={4} />);
    expect(getByText(/Server trả lỗi \(HTTP 500\)/)).toBeTruthy();
    expect(() => getByText(/Đang tạo kịch bản cho ngày đầu/)).toThrow();
  });
});
