import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { DouyinAutoNicheBanner } from "./DouyinAutoNicheBanner";


afterEach(() => cleanup());


describe("DouyinAutoNicheBanner", () => {
  it("renders the niche label + match count + dismiss button", () => {
    const onDismiss = vi.fn();
    render(
      <DouyinAutoNicheBanner
        nicheLabel="Wellness"
        matchCount={42}
        onDismiss={onDismiss}
      />,
    );
    expect(screen.getByText(/Đang lọc theo ngách bạn theo dõi/)).toBeTruthy();
    expect(screen.getByText("Wellness")).toBeTruthy();
    expect(screen.getByText(/42 video/)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /Mở rộng để xem tất cả ngách/ }),
    ).toBeTruthy();
  });

  it("calls onDismiss when the dismiss button is clicked", () => {
    const onDismiss = vi.fn();
    render(
      <DouyinAutoNicheBanner
        nicheLabel="Wellness"
        matchCount={1}
        onDismiss={onDismiss}
      />,
    );
    fireEvent.click(
      screen.getByRole("button", { name: /Mở rộng để xem tất cả ngách/ }),
    );
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
