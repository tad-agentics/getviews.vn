/**
 * PR-T5 Trends — TrendsDouyinCard render-test.
 *
 * Reference: design pack ``screens/trends.jsx`` lines 351-384.
 */
import { cleanup, fireEvent, render } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import { TrendsDouyinCard } from "./TrendsDouyinCard";

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
  it("renders the kicker, mid-line, and caption per design", () => {
    const { getByText } = wrap();
    expect(getByText(/TÍN HIỆU SỚM · DOUYIN → VN/)).toBeTruthy();
    expect(getByText(/Pattern đang nổ ở TQ · video đã sub VN/)).toBeTruthy();
    expect(getByText(/Đi trước VN 4–10 tuần · không cần VPN/)).toBeTruthy();
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
