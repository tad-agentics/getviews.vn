/**
 * TrendsRail — breakout rail UX + preview-before-analyze flow.
 */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TrendsRailPayload } from "@/hooks/useTrendsRailVideos";

const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockUseTrendsRailVideos = vi.fn();
vi.mock("@/hooks/useTrendsRailVideos", async () => {
  const actual = await vi.importActual<typeof import("@/hooks/useTrendsRailVideos")>(
    "@/hooks/useTrendsRailVideos",
  );
  return {
    ...actual,
    useTrendsRailVideos: (...args: unknown[]) => mockUseTrendsRailVideos(...args),
  };
});

const { TrendsRail } = await import("./TrendsRail");

beforeEach(() => {
  mockUseTrendsRailVideos.mockReset();
  mockNavigate.mockReset();
});

afterEach(() => {
  cleanup();
});

const samplePayload = (overrides: Partial<TrendsRailPayload> = {}): TrendsRailPayload => ({
  videos: [
    {
      video_id: "b1",
      thumbnail_url: "https://t/1.jpg",
      creator_handle: "an.tech",
      tiktok_url: "https://www.tiktok.com/@an.tech/video/b1",
      views: 250_000,
      posted_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      indexed_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
      hook_phrase: "Breakout one",
      hook_type: "question",
      breakout_multiplier: 2.4,
      content_format: "talking_head",
    },
  ],
  meta: { usedFallback: false, eligibleCount: 3 },
  ...overrides,
});

function wrap(node: React.ReactNode) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe("TrendsRail", () => {
  it("renders nothing when neither junction nor legacy niche is set", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: undefined, isPending: false });
    const { container } = wrap(
      <TrendsRail contentClassIds={[]} nicheScopeLabel="Làm đẹp" />,
    );
    expect(container.querySelector("[data-testid='trends-rail']")).toBeNull();
  });

  it("passes legacyNicheId to hook when junction is empty", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: samplePayload(), isPending: false });
    wrap(<TrendsRail contentClassIds={[]} legacyNicheId={7} nicheScopeLabel="Làm đẹp" />);
    expect(mockUseTrendsRailVideos).toHaveBeenCalledWith(
      expect.objectContaining({ contentClassIds: [], legacyNicheId: 7 }),
    );
  });

  it("renders honest breakout copy, multiplier, and format chip on rows", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: samplePayload(), isPending: false });
    wrap(<TrendsRail contentClassIds={[1, 2]} nicheScopeLabel="Làm đẹp" />);
    expect(screen.getByText("Video organic đáng xem")).toBeTruthy();
    expect(screen.getByText(/Top 5 breakout đăng trong 14 ngày/)).toBeTruthy();
    expect(screen.getByText("Breakout one")).toBeTruthy();
    expect(screen.getByText("2.4×")).toBeTruthy();
    expect(screen.getByText("Talking head")).toBeTruthy();
  });

  it("shows fallback disclaimer when pool used unfiltered fill", () => {
    mockUseTrendsRailVideos.mockReturnValue({
      data: samplePayload({ meta: { usedFallback: true, eligibleCount: 1 } }),
      isPending: false,
    });
    wrap(<TrendsRail contentClassIds={[1]} nicheScopeLabel="Làm đẹp" />);
    expect(screen.getByTestId("trends-rail-fallback-note")).toBeTruthy();
  });

  it("opens preview on row click; analyze navigates with handoff (not immediate on row click)", async () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: samplePayload(), isPending: false });
    wrap(<TrendsRail contentClassIds={[1]} nicheScopeLabel="Làm đẹp" />);
    fireEvent.click(screen.getByText("Breakout one"));
    await waitFor(() => {
      expect(screen.getByText("Giải mã video này")).toBeTruthy();
    });
    expect(mockNavigate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Giải mã video này"));
    expect(mockNavigate).toHaveBeenCalledTimes(1);
    expect(mockNavigate.mock.calls[0]![0]).toContain("from=trends");
  });

  it("renders skeletons while pending", () => {
    mockUseTrendsRailVideos.mockReturnValue({ data: undefined, isPending: true });
    const { container } = wrap(<TrendsRail contentClassIds={[1]} />);
    expect(container.querySelectorAll(".animate-pulse").length).toBe(3);
  });
});
