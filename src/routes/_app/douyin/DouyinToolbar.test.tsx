/**
 * D4c (2026-06-04) — Toolbar interaction tests.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { DouyinToolbar } from "./DouyinToolbar";
import { INITIAL_FILTERS, type DouyinFilters } from "./douyinFilters";


afterEach(cleanup);


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
  it("renders the search input + sort select + saved toggle", () => {
    _renderToolbar();
    expect(screen.getByLabelText(/Tìm trong Kho Douyin/)).toBeTruthy();
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
});
