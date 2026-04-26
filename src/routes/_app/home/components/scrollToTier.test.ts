/**
 * PR-4 Studio Home — scrollToSuggestionsTier helper.
 *
 * Plain DOM lookup of ``[data-tier=...]`` + ``scrollIntoView``. Test
 * that it gracefully returns false when the anchor is missing and
 * forwards the options object when found.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { scrollToSuggestionsTier } from "./scrollToTier";

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("scrollToSuggestionsTier", () => {
  it("returns false when no anchor with the tier id exists", () => {
    const ok = scrollToSuggestionsTier("01");
    expect(ok).toBe(false);
  });

  it("calls scrollIntoView and returns true when the anchor exists", () => {
    const target = document.createElement("section");
    target.dataset.tier = "01";
    document.body.appendChild(target);
    const spy = vi.fn();
    target.scrollIntoView = spy as unknown as Element["scrollIntoView"];

    const ok = scrollToSuggestionsTier("01");
    expect(ok).toBe(true);
    expect(spy).toHaveBeenCalledOnce();
  });

  it("forwards custom ScrollIntoViewOptions", () => {
    const target = document.createElement("section");
    target.dataset.tier = "02";
    document.body.appendChild(target);
    const spy = vi.fn();
    target.scrollIntoView = spy as unknown as Element["scrollIntoView"];

    scrollToSuggestionsTier("02", { behavior: "auto", block: "center" });
    expect(spy).toHaveBeenCalledWith({ behavior: "auto", block: "center" });
  });

  it("uses smooth start as the default scroll options", () => {
    const target = document.createElement("section");
    target.dataset.tier = "03";
    document.body.appendChild(target);
    const spy = vi.fn();
    target.scrollIntoView = spy as unknown as Element["scrollIntoView"];

    scrollToSuggestionsTier("03");
    expect(spy).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
  });
});
