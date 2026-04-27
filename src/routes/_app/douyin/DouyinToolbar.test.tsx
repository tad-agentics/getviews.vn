/**
 * D4c (2026-06-04) — Toolbar interaction tests.
 *
 * Confirms the toolbar emits the expected ``DouyinFilters`` shape on
 * each user input. Pure controlled component — no provider plumbing
 * required.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { DouyinToolbar } from "./DouyinToolbar";
import { INITIAL_FILTERS, type DouyinFilters } from "./douyinFilters";


afterEach(() => cleanup());


function _renderToolbar(initial: Partial<DouyinFilters> = {}) {
  const onFiltersChange = vi.fn();
  const filters: DouyinFilters = { ...INITIAL_FILTERS, ...initial };
  render(
    <DouyinToolbar
      filters={filters}
      onFiltersChange={onFiltersChange}
      savedCount={2}
    />,
  );
  return { onFiltersChange, filters };
}


describe("DouyinToolbar", () => {
  it("renders the search input + 4 adapt chips + sort select + saved toggle", () => {
    _renderToolbar();
    expect(screen.getByLabelText(/Tìm trong Kho Douyin/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Tất cả/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /XANH/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /VÀNG/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /ĐỎ/ })).toBeTruthy();
    expect(screen.getByLabelText(/Sắp xếp video/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Kho cá nhân/ })).toBeTruthy();
  });

  it("emits a filters object with the new search string on input", () => {
    const { onFiltersChange } = _renderToolbar();
    fireEvent.change(screen.getByLabelText(/Tìm trong Kho Douyin/), {
      target: { value: "yoga" },
    });
    expect(onFiltersChange).toHaveBeenLastCalledWith({
      ...INITIAL_FILTERS,
      search: "yoga",
    });
  });

  it("flips the adapt-level filter when a chip is clicked", () => {
    const { onFiltersChange } = _renderToolbar();
    fireEvent.click(screen.getByRole("button", { name: /XANH/ }));
    expect(onFiltersChange).toHaveBeenLastCalledWith({
      ...INITIAL_FILTERS,
      adaptLevel: "green",
    });
  });

  it("emits the new sort key on select change", () => {
    const { onFiltersChange } = _renderToolbar();
    fireEvent.change(screen.getByLabelText(/Sắp xếp video/), {
      target: { value: "views" },
    });
    expect(onFiltersChange).toHaveBeenLastCalledWith({
      ...INITIAL_FILTERS,
      sort: "views",
    });
  });

  it("toggles savedOnly when the Kho cá nhân pill is clicked", () => {
    const { onFiltersChange } = _renderToolbar();
    fireEvent.click(screen.getByRole("button", { name: /Kho cá nhân/ }));
    expect(onFiltersChange).toHaveBeenLastCalledWith({
      ...INITIAL_FILTERS,
      savedOnly: true,
    });
  });

  it("renders the saved count next to the toggle when > 0", () => {
    _renderToolbar();
    // savedCount=2 is set in the helper.
    expect(screen.getByText(/· 2/)).toBeTruthy();
  });

  it("reflects the active adapt chip via aria-pressed", () => {
    _renderToolbar({ adaptLevel: "yellow" });
    const yellow = screen.getByRole("button", { name: /VÀNG/ });
    expect(yellow.getAttribute("aria-pressed")).toBe("true");
    const green = screen.getByRole("button", { name: /XANH/ });
    expect(green.getAttribute("aria-pressed")).toBe("false");
  });
});
