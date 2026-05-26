/**
 * NicheInsightCard tests — locks in the null-safe contract that lets the
 * same component render in both IdeasBody (Wave-2 PR #4 original
 * surface) and PatternBody (Wave-2 PR #5 follow-up: Layer 0 was being
 * fetched on every pattern turn but never displayed).
 *
 * The card is intentionally cheap to drop in — these tests just guard
 * the visibility rules so a future refactor doesn't accidentally
 * re-orphan the data.
 */

import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { NicheInsightData } from "@/lib/api-types";
import { NicheInsightCard } from "./NicheInsightCard";

afterEach(cleanup);

function make(overrides: Partial<NicheInsightData> = {}): NicheInsightData {
  return {
    insight_text: "Beauty creators tăng tốc khi đẩy demo trong 2 giây đầu.",
    execution_tip: "Mở bằng kết quả before/after, hold POV, kết bằng CTA xem lại.",
    top_formula_hook: "POV demo",
    top_formula_format: "before/after",
    week_of: "2026-05-04",
    staleness_risk: "LOW",
    ...overrides,
  };
}

describe("NicheInsightCard", () => {
  it("renders the execution_tip + composed formula badge when populated", () => {
    render(<NicheInsightCard insight={make()} />);
    expect(screen.getByText(/Mở bằng kết quả before\/after/)).toBeTruthy();
    expect(screen.getByText(/POV demo × before\/after/)).toBeTruthy();
    expect(screen.getByText(/Gợi ý mảng nội dung tuần này/)).toBeTruthy();
  });

  it("renders nothing when execution_tip is missing — protects against rendering an empty card", () => {
    const { container } = render(
      <NicheInsightCard insight={make({ execution_tip: null })} />,
    );
    // Card should be entirely absent — not just hidden via class.
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when execution_tip is whitespace-only", () => {
    const { container } = render(
      <NicheInsightCard insight={make({ execution_tip: "   " })} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when insight is null (cron hasn't populated this niche yet)", () => {
    const { container } = render(<NicheInsightCard insight={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when insight is undefined (older payloads predate the field)", () => {
    const { container } = render(<NicheInsightCard insight={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("falls back to a single formula side when only the hook is present", () => {
    render(
      <NicheInsightCard
        insight={make({ top_formula_hook: "POV demo", top_formula_format: null })}
      />,
    );
    expect(screen.getByText(/POV demo/)).toBeTruthy();
    expect(screen.queryByText(/×/)).toBeNull();
  });

  it("hides the formula badge entirely when both sides are missing", () => {
    render(
      <NicheInsightCard
        insight={make({ top_formula_hook: null, top_formula_format: null })}
      />,
    );
    expect(screen.queryByText(/Công thức thắng/)).toBeNull();
  });
});
