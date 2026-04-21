/**
 * TriggersPanel — dialog state machine regression.
 *
 * The state transitions are load-bearing:
 *
 *   closed → (Run click on no-params job) → confirm → (Xác nhận chạy)
 *     → running → mutateAsync resolves → result
 *   closed → (Run click on `ingest`) → inline form → (Chạy ingest)
 *     → confirm → ...
 *   confirm → (Hủy) → closed
 *   running → mutateAsync rejects → error
 *
 * A regression that flips the confirm/run order would let a single
 * click fire a batch job that costs Gemini + EnsembleData credits —
 * the confirm block is the operator's last chance to bail.
 */
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
  },
}));

const mockUseAdminTriggerCatalog = vi.fn();
const mockMutateAsync = vi.fn();
vi.mock("@/hooks/useAdminTriggers", () => ({
  useAdminTriggerCatalog: () => mockUseAdminTriggerCatalog(),
  useAdminTrigger: () => ({ mutateAsync: mockMutateAsync }),
}));

import { TriggersPanel } from "./TriggersPanel";

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TriggersPanel />
    </QueryClientProvider>,
  );
}

const STUB_CATALOG = [
  {
    id: "ingest",
    label: "Corpus ingest (/batch/ingest)",
    body_schema: { niche_ids: "int[] | null", deep_pool: "bool" },
    heavy: true,
  },
  {
    id: "analytics",
    label: "Weekly analytics",
    body_schema: {},
    heavy: true,
  },
];

beforeEach(() => {
  mockUseAdminTriggerCatalog.mockReturnValue({
    data: STUB_CATALOG,
    isLoading: false,
    isError: false,
  });
  mockMutateAsync.mockReset();
});
afterEach(cleanup);

describe("TriggersPanel", () => {
  it("renders a card per catalog entry with a Run button", () => {
    renderPanel();
    expect(screen.getByText("Corpus ingest (/batch/ingest)")).toBeTruthy();
    expect(screen.getByText("Weekly analytics")).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Run" }).length).toBe(2);
  });

  it("no-param job → Run opens confirm directly (no inline form)", () => {
    renderPanel();
    // Click the Run button on the analytics card (second one).
    const runs = screen.getAllByRole("button", { name: "Run" });
    fireEvent.click(runs[1]);

    // Confirm prompt is now on screen, mutateAsync hasn't been called yet.
    // "Chạy" and the job label live in different DOM nodes — asserting the
    // confirm button's presence is a strong-enough proxy for "confirm state".
    expect(screen.getByRole("button", { name: "Xác nhận chạy" })).toBeTruthy();
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("param job (ingest) → Run opens inline form first, then confirm on submit", () => {
    renderPanel();
    const runs = screen.getAllByRole("button", { name: "Run" });
    fireEvent.click(runs[0]);

    // Inline form for niche_ids + deep_pool is visible.
    expect(screen.getByPlaceholderText("1, 3, 7")).toBeTruthy();
    // Confirm block hasn't appeared yet.
    expect(screen.queryByRole("button", { name: "Xác nhận chạy" })).toBeNull();

    // Submit the form (empty = all niches, deep_pool false).
    fireEvent.click(screen.getByRole("button", { name: "Chạy ingest" }));

    // Now confirm appears with the captured body.
    expect(screen.getByRole("button", { name: "Xác nhận chạy" })).toBeTruthy();
    expect(screen.getByText(/"niche_ids": null/)).toBeTruthy();
    expect(screen.getByText(/"deep_pool": false/)).toBeTruthy();
  });

  it("ingest form rejects non-numeric niche_ids and keeps the form open", () => {
    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[0]);

    const input = screen.getByPlaceholderText("1, 3, 7") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "1, abc, 7" } });
    fireEvent.click(screen.getByRole("button", { name: "Chạy ingest" }));

    // Validation error is visible; confirm block didn't appear.
    expect(screen.getByText(/Chỉ nhập các ID số dương/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Xác nhận chạy" })).toBeNull();
  });

  it("Hủy on confirm closes without calling mutateAsync", () => {
    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Hủy" }));

    expect(mockMutateAsync).not.toHaveBeenCalled();
    // Run button is back.
    expect(screen.getAllByRole("button", { name: "Run" }).length).toBe(2);
  });

  it("confirms → running → success transitions to the result block with the JSON", async () => {
    mockMutateAsync.mockResolvedValue({
      ok: true,
      analytics: { creators_updated: 4, videos_updated: 17, errors: [] },
    });

    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận chạy" }));

    // mutateAsync called with the analytics job id and empty body.
    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({ job: "analytics", body: {} });
    });

    // Result block renders with the response JSON.
    await screen.findByText(/Xong — kết quả/);
    expect(screen.getByText(/creators_updated/)).toBeTruthy();
  });

  it("confirms → running → error transitions to the error block with the message", async () => {
    mockMutateAsync.mockRejectedValue(new Error("ensemble_daily_budget_exceeded: over limit"));

    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận chạy" }));

    await screen.findByText(/ensemble_daily_budget_exceeded/);
  });
});
