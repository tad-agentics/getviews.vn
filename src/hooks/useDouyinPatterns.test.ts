/**
 * D5d (2026-06-05) — useDouyinPatterns hook tests.
 *
 * Mirrors ``useDouyinFeed.test.ts`` — mocks ``globalThis.fetch`` +
 * ``supabase.auth.getSession`` so tests stay deterministic.
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";

import type { DouyinPatternsResponse } from "@/lib/api-types";

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
    VITE_R2_PUBLIC_URL: undefined,
  },
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
    },
  },
}));

vi.mock("@/lib/authErrors", () => ({
  throwSessionExpired: vi.fn((reason: string) => {
    const err = new Error(`session_expired:${reason}`);
    err.name = "SessionExpired";
    throw err;
  }),
}));

const { supabase } = await import("@/lib/supabase");
const { useDouyinPatterns } = await import("./useDouyinPatterns");

function wrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

const _originalFetch = globalThis.fetch;

beforeEach(() => {
  vi.mocked(supabase.auth.getSession).mockResolvedValue({
    data: { session: { access_token: "fake-jwt", user: { id: "u1" } } as never },
    error: null,
  });
});

afterEach(() => {
  globalThis.fetch = _originalFetch;
  vi.clearAllMocks();
});


describe("useDouyinPatterns", () => {
  it("fetches /douyin/patterns with the JWT and returns the payload", async () => {
    const payload: DouyinPatternsResponse = {
      patterns: [
        {
          id: "pat-1",
          niche_id: 1,
          week_of: "2026-06-01",
          rank: 1,
          name_vn: "Routine 3 bước trước khi ngủ",
          name_zh: "睡前仪式",
          hook_template_vi: "3 việc trước khi ___",
          format_signal_vi: "POV cận cảnh, voiceover thì thầm.",
          sample_video_ids: ["v1", "v2", "v3"],
          cn_rise_pct_avg: 35.0,
          computed_at: "2026-06-01T21:00:00+00:00",
        },
      ],
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(payload),
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinPatterns(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data).toEqual(payload);

    const fetchCall = vi.mocked(globalThis.fetch).mock.calls[0];
    const [url, init] = fetchCall ?? [];
    expect(url).toBe("https://cloud-run.test/douyin/patterns");
    expect((init as RequestInit | undefined)?.method).toBe("GET");
    expect((init as RequestInit | undefined)?.headers).toMatchObject({
      Authorization: "Bearer fake-jwt",
    });
  });

  it("is disabled when enabled=false (caller-controlled gate)", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderHook(() => useDouyinPatterns(false), { wrapper: wrapper(qc) });
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("surfaces error when no session is available", async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    });
    globalThis.fetch = vi.fn();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinPatterns(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toMatch(/Chưa đăng nhập/);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("triggers session-expired path on 401", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve("unauthorized"),
      json: () => Promise.resolve({ detail: "unauthorized" }),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinPatterns(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toMatch(/session_expired/);
  });

  it("surfaces error on non-OK response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("internal error"),
      json: () => Promise.resolve({ detail: "internal error" }),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinPatterns(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });

  it("returns empty array on a no-rows response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ patterns: [] } satisfies DouyinPatternsResponse),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinPatterns(), { wrapper: wrapper(qc) });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.patterns).toEqual([]);
  });
});
