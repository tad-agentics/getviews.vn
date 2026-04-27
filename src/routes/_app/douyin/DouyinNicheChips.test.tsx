/**
 * D4b (2026-06-04) — DouyinNicheChips tests.
 *
 * Renders the chip strip and verifies:
 *   • "Tất cả" chip is the leading default-active option.
 *   • Active state highlights the matching chip.
 *   • onSelect fires with the right slug (or null for "Tất cả").
 */

import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { DouyinNiche } from "@/lib/api-types";
import { DouyinNicheChips } from "./DouyinNicheChips";

afterEach(cleanup);


function _niches(): DouyinNiche[] {
  return [
    { id: 1, slug: "wellness", name_vn: "Wellness", name_zh: "养生", name_en: "Wellness" },
    { id: 2, slug: "tech", name_vn: "Tech", name_zh: "科技", name_en: "Tech" },
  ];
}


describe("DouyinNicheChips", () => {
  it("renders 'Tất cả' + one chip per niche", () => {
    render(
      <DouyinNicheChips
        niches={_niches()}
        activeSlug={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Tất cả" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Wellness" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Tech" })).toBeTruthy();
  });

  it("highlights 'Tất cả' as the active chip when activeSlug is null", () => {
    render(
      <DouyinNicheChips
        niches={_niches()}
        activeSlug={null}
        onSelect={vi.fn()}
      />,
    );
    const allChip = screen.getByRole("button", { name: "Tất cả" });
    expect(allChip.getAttribute("aria-pressed")).toBe("true");
    const techChip = screen.getByRole("button", { name: "Tech" });
    expect(techChip.getAttribute("aria-pressed")).toBe("false");
  });

  it("highlights the matching slug when activeSlug is set", () => {
    render(
      <DouyinNicheChips
        niches={_niches()}
        activeSlug="tech"
        onSelect={vi.fn()}
      />,
    );
    const techChip = screen.getByRole("button", { name: "Tech" });
    expect(techChip.getAttribute("aria-pressed")).toBe("true");
    const allChip = screen.getByRole("button", { name: "Tất cả" });
    expect(allChip.getAttribute("aria-pressed")).toBe("false");
  });

  it("calls onSelect with the slug when a niche chip is clicked", () => {
    const onSelect = vi.fn();
    render(
      <DouyinNicheChips
        niches={_niches()}
        activeSlug={null}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tech" }));
    expect(onSelect).toHaveBeenCalledWith("tech");
  });

  it("calls onSelect with null when 'Tất cả' is clicked", () => {
    const onSelect = vi.fn();
    render(
      <DouyinNicheChips
        niches={_niches()}
        activeSlug="tech"
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tất cả" }));
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("renders just 'Tất cả' when niches is empty", () => {
    render(
      <DouyinNicheChips
        niches={[]}
        activeSlug={null}
        onSelect={vi.fn()}
      />,
    );
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(1);
    expect(buttons[0]?.textContent).toBe("Tất cả");
  });
});
