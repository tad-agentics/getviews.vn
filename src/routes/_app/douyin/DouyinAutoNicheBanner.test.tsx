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
    expect(screen.getByText(/Đang ưu tiên ngách/)).toBeTruthy();
    expect(screen.getByText("Wellness")).toBeTruthy();
    expect(screen.getByText(/42 video khớp/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Bỏ ưu tiên ngách/ })).toBeTruthy();
  });

  it("calls onDismiss when the X button is clicked", () => {
    const onDismiss = vi.fn();
    render(
      <DouyinAutoNicheBanner
        nicheLabel="Wellness"
        matchCount={1}
        onDismiss={onDismiss}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Bỏ ưu tiên ngách/ }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
