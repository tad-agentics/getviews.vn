/**
 * PR-T5 Trends — TrendsDouyinCard render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 351-384.
 *
 * D7 (2026-06-06) — the card now pulls live counts from
 * ``useDouyinFeed`` + ``useDouyinPatterns``. We mock both hooks so
 * tests stay deterministic and avoid the network.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const useDouyinFeed = vi.fn();
vi.mock("@/hooks/useDouyinFeed", () => ({
  useDouyinFeed: () => useDouyinFeed(),
}));

const useDouyinPatterns = vi.fn();
vi.mock("@/hooks/useDouyinPatterns", () => ({
  useDouyinPatterns: () => useDouyinPatterns(),
}));

const { TrendsDouyinCard } = await import("./TrendsDouyinCard");

beforeEach(() => {
  useDouyinFeed.mockReset();
  useDouyinPatterns.mockReset();
  // Default: empty data — card renders count-less fallback copy.
  useDouyinFeed.mockReturnValue({ data: undefined });
  useDouyinPatterns.mockReturnValue({ data: undefined });
});

afterEach(() => {
  cleanup();
});

function LocationProbe() {
  const location = useLocation();
  return <span data-testid="probe">{location.pathname}</span>;
}

function wrap() {
  return render(
    <MemoryRouter initialEntries={["/app/trends"]}>
      <Routes>
        <Route path="/app/trends" element={<TrendsDouyinCard />} />
        <Route path="/app/douyin" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("TrendsDouyinCard", () => {
  it("renders the kicker, count-less mid-line, and caption when feed/patterns are empty", () => {
    const { getByText } = wrap();
    expect(getByText(/TÍN HIỆU SỚM · DOUYIN → VN/)).toBeTruthy();
    expect(getByText(/Pattern đang nổ ở TQ · video đã sub VN/)).toBeTruthy();
    expect(getByText(/Đi trước VN 4–10 tuần · không cần VPN/)).toBeTruthy();
  });

  it("renders the live count line when both hooks have data", () => {
    useDouyinFeed.mockReturnValue({
      data: { niches: [], videos: new Array(16).fill(null) },
    });
    useDouyinPatterns.mockReturnValue({
      data: { patterns: new Array(3).fill(null) },
    });
    const { getByText } = wrap();
    expect(
      getByText(/3 pattern đang nổ ở TQ · 16 video đã sub VN/),
    ).toBeTruthy();
  });

  it("navigates to /app/douyin on click", () => {
    const { getByLabelText, getByTestId } = wrap();
    fireEvent.click(getByLabelText(/Mở Kho Douyin/));
    expect(getByTestId("probe").textContent).toBe("/app/douyin");
  });

  it("renders the archive icon avatar with ink bg + accent fill", () => {
    const { container } = wrap();
    // The avatar is the first <span aria-hidden> child of the button.
    const avatar = container.querySelector('button > span > span[aria-hidden="true"]');
    expect(avatar?.className).toMatch(/gv-ink/);
    expect(avatar?.className).toMatch(/gv-accent/);
  });
});
