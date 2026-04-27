/**
 * EnsembleCreditsPanel — admin DevOps surface (Phase D.6.2). Renders
 * four big-number counters + a 14-day bar sparkline with runway
 * projection. Multiple branch states (loading, error, empty, with-
 * budget, without-budget, low-runway) — these tests pin the visual
 * shape so a copy / token tweak doesn't silently regress.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type {
  EnsembleCreditsResponse,
  EnsembleDailyUnits,
} from "@/hooks/useEnsembleCredits";
import type { EnsembleCallSitesResponse } from "@/hooks/useEnsembleCallSites";
import type { EnsembleHistoryResponse } from "@/hooks/useEnsembleHistory";

import { EnsembleCreditsPanel } from "./EnsembleCreditsPanel";

type QueryStub<T> = {
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  data: T | undefined;
};

const creditsState: QueryStub<EnsembleCreditsResponse> = {
  isLoading: false,
  isError: false,
  error: null,
  data: undefined,
};

const callSitesState: QueryStub<EnsembleCallSitesResponse> = {
  isLoading: false,
  isError: false,
  error: null,
  data: undefined,
};

const historyState: QueryStub<EnsembleHistoryResponse> = {
  isLoading: false,
  isError: false,
  error: null,
  data: undefined,
};

vi.mock("@/hooks/useEnsembleCredits", () => ({
  useEnsembleCredits: () => creditsState,
}));
vi.mock("@/hooks/useEnsembleCallSites", () => ({
  useEnsembleCallSites: () => callSitesState,
}));
vi.mock("@/hooks/useEnsembleHistory", () => ({
  useEnsembleHistory: () => historyState,
}));

function day(
  date: string,
  units: number,
  overrides: Partial<EnsembleDailyUnits> = {},
): EnsembleDailyUnits {
  return { date, units, ok: true, ...overrides };
}

function fillCredits(over: Partial<EnsembleCreditsResponse> = {}): EnsembleCreditsResponse {
  return {
    ok: true,
    as_of: "2026-04-27T00:00:00Z",
    monthly_budget: null,
    days: [],
    ...over,
  };
}

beforeEach(() => {
  Object.assign(creditsState, {
    isLoading: false,
    isError: false,
    error: null,
    data: undefined,
  });
  Object.assign(callSitesState, {
    isLoading: false,
    isError: false,
    error: null,
    data: undefined,
  });
  Object.assign(historyState, {
    isLoading: false,
    isError: false,
    error: null,
    data: undefined,
  });
});

afterEach(cleanup);

describe("EnsembleCreditsPanel — branches", () => {
  it("renders a skeleton while the credits query is loading", () => {
    creditsState.isLoading = true;
    render(<EnsembleCreditsPanel />);
    expect(
      screen.getByRole("status", { name: /Đang tải ensemble credits/i }),
    ).toBeTruthy();
  });

  it("renders config-missing copy when the backend reports ensemble_token_unset", () => {
    creditsState.isError = true;
    creditsState.error = new Error("ensemble_token_unset");
    render(<EnsembleCreditsPanel />);
    expect(screen.getByText(/ENSEMBLE_DATA_API_KEY chưa được cấu hình/)).toBeTruthy();
  });

  it("renders generic danger copy on any other error", () => {
    creditsState.isError = true;
    creditsState.error = new Error("http_503");
    render(<EnsembleCreditsPanel />);
    expect(screen.getByText(/Không tải được EnsembleData usage/)).toBeTruthy();
  });

  it("renders Projection · 30d + 'Chưa đặt' when no monthly_budget is configured", () => {
    creditsState.data = fillCredits({
      days: [day("2026-04-25", 100), day("2026-04-26", 200), day("2026-04-27", 300)],
      monthly_budget: null,
    });
    render(<EnsembleCreditsPanel />);
    expect(screen.getByText("Projection · 30d")).toBeTruthy();
    expect(screen.getByText("Chưa đặt")).toBeTruthy();
    // "Today" → 300; rendered with vi-VN locale formatting.
    expect(screen.getByText("300")).toBeTruthy();
  });

  it("renders Tháng này + Runway when monthly_budget is configured", () => {
    creditsState.data = fillCredits({
      days: Array.from({ length: 7 }, (_, i) =>
        day(`2026-04-${21 + i}`, 1_000),
      ),
      monthly_budget: 50_000,
    });
    render(<EnsembleCreditsPanel />);
    expect(screen.getByText("Tháng này")).toBeTruthy();
    expect(screen.getByText("Runway")).toBeTruthy();
    // 7 days × 1000 units = 7000 used; runway = (50000-7000) / (1000) = 43d.
    expect(screen.getByText("43d")).toBeTruthy();
  });

  it("flags Runway with the danger tone when < 7 days remain", () => {
    creditsState.data = fillCredits({
      // 7 days × 4500 = 31_500 used; 50_000 budget; remaining 18_500;
      // projection 4500 * 30 = 135_000; runway = 18500 / 4500 ≈ 4d.
      days: Array.from({ length: 7 }, (_, i) =>
        day(`2026-04-${21 + i}`, 4_500),
      ),
      monthly_budget: 50_000,
    });
    const { container } = render(<EnsembleCreditsPanel />);
    const runwayValue = screen.getByText("4d");
    expect(runwayValue.className).toMatch(/--gv-danger/);
    // Sanity — only one runway counter on screen.
    expect(container.textContent).toContain("Runway");
  });

  it("renders one bar per day in the 14-day chart and dims failed days", () => {
    creditsState.data = fillCredits({
      days: [
        day("2026-04-25", 1000),
        day("2026-04-26", 0, { ok: false, error: "timeout" }),
        day("2026-04-27", 1500),
      ],
      monthly_budget: null,
    });
    render(<EnsembleCreditsPanel />);
    const chart = screen.getByRole("img", {
      name: /EnsembleData daily usage trend/i,
    });
    // Each ``<div>`` directly inside the chart frames one day.
    const bars = chart.querySelectorAll(":scope > div");
    expect(bars.length).toBe(3);
    // The failed day's title surfaces the error code so an operator
    // can hover-debug without leaving the panel.
    expect(chart.querySelector('[title*="lỗi: timeout"]')).toBeTruthy();
  });
});
