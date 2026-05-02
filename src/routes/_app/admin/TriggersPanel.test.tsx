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
    VITE_CLOUD_RUN_BATCH_URL: "https://cloud-run.test",
  },
}));

const mockUseAdminTriggerCatalog = vi.fn();
const mockMutateAsync = vi.fn();
const mockUseAdminJobPoll = vi.fn();
vi.mock("@/hooks/useAdminTriggers", () => ({
  useAdminTriggerCatalog: () => mockUseAdminTriggerCatalog(),
  useAdminTrigger: () => ({ mutateAsync: mockMutateAsync }),
  useAdminJobPoll: (jobId: string | null) => mockUseAdminJobPoll(jobId),
}));

import { TriggersPanel } from "./TriggersPanel";

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const ui = (
    <QueryClientProvider client={qc}>
      <TriggersPanel />
    </QueryClientProvider>
  );
  const r = render(ui);
  // Return a reRender helper the tests can use to force a re-render
  // after flipping the useAdminJobPoll mock's return value — without
  // this, the hook only re-evaluates on prop/state changes of its
  // parent, which never happen here once the dialog state settles.
  return { ...r, reRenderSame: () => r.rerender(ui) };
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
  // Default: poll returns "no data yet" — tests that care override.
  mockUseAdminJobPoll.mockReturnValue({ data: undefined });
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

  it("confirm → 202 accepted → polling state (awaiting worker)", async () => {
    mockMutateAsync.mockResolvedValue({
      ok: true,
      job_id: "job-abc",
      status: "queued",
    });

    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận chạy" }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({ job: "analytics", body: {} });
    });
    // Polling state visible — shows the "đã nhận" copy + short job id.
    await screen.findByText(/đã nhận/i);
    expect(screen.getByText(/job_id · job-abc/)).toBeTruthy();
  });

  it("polling → row becomes ok → result block renders with result_json", async () => {
    mockMutateAsync.mockResolvedValue({ ok: true, job_id: "job-ok", status: "queued" });
    // Return the terminal-ok row from the outset — the JobRow's
    // useEffect sees it on the first render after entering the
    // polling state and transitions straight to the result block.
    mockUseAdminJobPoll.mockReturnValue({
      data: {
        ok: true,
        job: {
          id: "job-ok",
          result_status: "ok",
          result_json: { ok: true, analytics: { creators_updated: 4 } },
          error_message: null,
          action: "trigger.analytics",
          params_json: {},
          duration_ms: 1234,
          user_id: null,
          created_at: new Date().toISOString(),
        },
      },
    });

    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận chạy" }));

    await screen.findByText(/Xong — kết quả/);
    expect(screen.getByText(/creators_updated/)).toBeTruthy();
  });

  it("polling → row becomes error → error block renders with error_message", async () => {
    mockMutateAsync.mockResolvedValue({ ok: true, job_id: "job-err", status: "queued" });
    mockUseAdminJobPoll.mockReturnValue({
      data: {
        ok: true,
        job: {
          id: "job-err",
          result_status: "error",
          result_json: null,
          error_message: "ensemble_daily_budget_exceeded: over limit",
          action: "trigger.analytics",
          params_json: {},
          duration_ms: 800,
          user_id: null,
          created_at: new Date().toISOString(),
        },
      },
    });

    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận chạy" }));

    await screen.findByText(/ensemble_daily_budget_exceeded/);
  });

  it("backend sync fallback (no job_id) → skips polling, renders result immediately", async () => {
    mockMutateAsync.mockResolvedValue({
      ok: true,
      job_id: null,
      status: "ok",
      result: { ok: true, analytics: { creators_updated: 9 } },
    });

    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận chạy" }));

    // No polling UI — jumps straight to the result block.
    await screen.findByText(/Xong — kết quả/);
    expect(screen.queryByText(/job_id ·/)).toBeNull();
  });

  it("mutateAsync reject → error block", async () => {
    mockMutateAsync.mockRejectedValue(new Error("http_500"));

    renderPanel();
    fireEvent.click(screen.getAllByRole("button", { name: "Run" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận chạy" }));

    await screen.findByText(/http_500/);
  });
});
