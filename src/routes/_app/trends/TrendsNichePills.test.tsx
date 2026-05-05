/**
 * TrendsNichePills tests — PR4 of single-niche refactor (2026-05-05).
 *
 * Surface contract:
 *   1. Pills render for every niche in the input.
 *   2. Order is Vietnamese alphabetical (locale-aware).
 *   3. ``activeId`` highlights the matching pill (aria-pressed=true).
 *   4. Clicking a pill calls ``onSelect`` with that niche's id.
 *   5. ``disabled`` prop disables every pill (no clicks fire).
 */

import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { TrendsNichePills } from "./TrendsNichePills";

const NICHES = [
  { id: 5, name: "Tài chính" },
  { id: 1, name: "Ẩm thực" },
  { id: 3, name: "Beauty" },
];

afterEach(() => {
  cleanup();
});

describe("TrendsNichePills", () => {
  it("renders one pill per niche, alphabetically (vi locale)", () => {
    render(
      <TrendsNichePills niches={NICHES} activeId={null} onSelect={() => {}} />,
    );
    const pills = screen.getAllByRole("button");
    expect(pills.map((p) => p.textContent)).toEqual([
      "Ẩm thực",
      "Beauty",
      "Tài chính",
    ]);
  });

  it("highlights the active pill via aria-pressed", () => {
    render(
      <TrendsNichePills niches={NICHES} activeId={3} onSelect={() => {}} />,
    );
    const beauty = screen.getByRole("button", { name: "Beauty" });
    const amthuc = screen.getByRole("button", { name: "Ẩm thực" });
    expect(beauty.getAttribute("aria-pressed")).toBe("true");
    expect(amthuc.getAttribute("aria-pressed")).toBe("false");
  });

  it("calls onSelect with the niche id on click", () => {
    const onSelect = vi.fn();
    render(
      <TrendsNichePills niches={NICHES} activeId={null} onSelect={onSelect} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Tài chính" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(5);
  });

  it("disabled prop blocks clicks", () => {
    const onSelect = vi.fn();
    render(
      <TrendsNichePills
        niches={NICHES}
        activeId={null}
        onSelect={onSelect}
        disabled
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Beauty" }));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("renders nothing when niches list is empty", () => {
    const { container } = render(
      <TrendsNichePills niches={[]} activeId={null} onSelect={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
