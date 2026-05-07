/**
 * L2.2 Sprint 6a — FunnelPanel render tests.
 *
 * Pins the visual contract for the L2.2 measurement surface so a
 * future copy / event-name tweak doesn't silently break the funnel.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render } from "@testing-library/react";

import type { AdminFunnelResponse } from "@/hooks/useAdminFunnel";

const funnelState: {
  data: AdminFunnelResponse | undefined;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
} = {
  data: undefined,
  isPending: false,
  isError: false,
  error: null,
};
const useAdminFunnelMock = vi.fn();

vi.mock("@/hooks/useAdminFunnel", () => ({
  useAdminFunnel: (...args: unknown[]) => useAdminFunnelMock(...args),
}));

const { FunnelPanel } = await import("./FunnelPanel");

const baseResponse = (overrides: Partial<AdminFunnelResponse> = {}): AdminFunnelResponse => ({
  ok: true,
  as_of: "2026-05-07T00:00:00Z",
  days: 7,
  totals: {
    answer_session_create: 100,
    daily_ritual_script_clicked: 40,
    script_generate: 25,
    script_save: 12,
    daily_ritual_evidence_expanded: 18,
    daily_ritual_evidence_thumb_clicked: 9,
    pattern_card_clicked: 30,
  },
  unique_users: {
    answer_session_create: 35,
    daily_ritual_script_clicked: 22,
    script_save: 10,
    daily_ritual_evidence_expanded: 15,
    pattern_card_clicked: 18,
  },
  daily_top_actions: {
    answer_session_create: { "2026-05-05": 30, "2026-05-06": 35, "2026-05-07": 35 },
    script_save: { "2026-05-05": 4, "2026-05-06": 5, "2026-05-07": 3 },
  },
  conversion: {},
  ...overrides,
});

beforeEach(() => {
  useAdminFunnelMock.mockReset();
  useAdminFunnelMock.mockImplementation(() => funnelState);
  funnelState.data = baseResponse();
  funnelState.isPending = false;
  funnelState.isError = false;
  funnelState.error = null;
});

afterEach(() => {
  cleanup();
});

describe("FunnelPanel", () => {
  it("renders a loading skeleton while pending", () => {
    funnelState.isPending = true;
    funnelState.data = undefined;
    const { getByLabelText } = render(<FunnelPanel />);
    expect(getByLabelText("Đang tải funnel")).toBeTruthy();
  });

  it("renders an error message when the query fails", () => {
    funnelState.isError = true;
    funnelState.error = new Error("admin_required");
    funnelState.data = undefined;
    const { getByText } = render(<FunnelPanel />);
    expect(getByText(/Không tải được funnel/)).toBeTruthy();
    expect(getByText(/admin_required/)).toBeTruthy();
  });

  it("renders the L2.2 hot-path funnel with conversion percentages between steps", () => {
    const { getByText } = render(<FunnelPanel />);
    // Step labels are present.
    expect(getByText(/Sessions opened/)).toBeTruthy();
    expect(getByText(/Ritual click → script studio/)).toBeTruthy();
    expect(getByText(/Script generated/)).toBeTruthy();
    expect(getByText(/Script saved/)).toBeTruthy();
    // Step 2 = 40 / 100 prior step → 40% conversion.
    expect(getByText(/40% chuyển đổi từ bước trước/)).toBeTruthy();
    // Step 4 = 12 / 25 prior step → 48% conversion.
    expect(getByText(/48% chuyển đổi từ bước trước/)).toBeTruthy();
  });

  it("renders the enrichment uptake cards with computed percentages", () => {
    const { getByText } = render(<FunnelPanel />);
    // 18 / 40 = 45%
    expect(getByText("45%")).toBeTruthy();
    // 9 / 18 = 50%
    expect(getByText("50%")).toBeTruthy();
    // Pattern card has no clean denominator — count + uniques shown.
    expect(getByText(/30 click · 18 người/)).toBeTruthy();
  });

  it("falls back to em-dash when an enrichment denominator is zero", () => {
    funnelState.data = baseResponse({
      totals: { ...baseResponse().totals, daily_ritual_evidence_expanded: 0 },
    });
    const { container } = render(<FunnelPanel />);
    // 9 / 0 → null pct → "—" rendered.
    expect(container.textContent).toContain("—");
  });

  it("lists every L2.2 watchlist event with its count + uniques", () => {
    const { getByText } = render(<FunnelPanel />);
    expect(getByText(/Ritual · click vào script/)).toBeTruthy();
    expect(getByText(/Trends · click pattern card/)).toBeTruthy();
    expect(getByText(/Studio · script_save/)).toBeTruthy();
    // Action codes are surfaced for ops grep.
    expect(getByText("daily_ritual_evidence_thumb_clicked")).toBeTruthy();
  });

  it("re-runs the query with the chosen window when toggled", () => {
    const { getByRole } = render(<FunnelPanel />);
    fireEvent.click(getByRole("tab", { name: "30 ngày" }));
    // Latest call was made with days=30.
    expect(useAdminFunnelMock.mock.calls.at(-1)?.[0]).toBe(30);
  });

  it("renders a 'no sessions' empty stub when the head of the funnel is zero", () => {
    funnelState.data = baseResponse({ totals: { script_save: 1 } });
    const { getByText } = render(<FunnelPanel />);
    expect(getByText(/Chưa có session nào trong cửa sổ/)).toBeTruthy();
  });
});
