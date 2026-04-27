/**
 * D4a (2026-06-04) — useDouyinFeed hook tests.
 *
 * Mocks ``globalThis.fetch`` + ``supabase.auth.getSession`` so tests
 * don't hit the network. Each test exercises one slice of the hook:
 * URL/headers shape, response parsing, error paths (401 → session
 * expired, missing config, network error).
 */

import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";

import type { DouyinFeedResponse } from "@/lib/api-types";

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
const { useDouyinFeed } = await import("./useDouyinFeed");

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


// ── Happy path ──────────────────────────────────────────────────────


describe("useDouyinFeed", () => {
  it("fetches /douyin/feed with the JWT and returns the payload", async () => {
    const payload: DouyinFeedResponse = {
      niches: [
        { id: 1, slug: "wellness", name_vn: "Wellness",
          name_zh: "养生", name_en: "Wellness" },
      ],
      videos: [
        {
          video_id: "v1",
          douyin_url: "https://www.douyin.com/video/v1",
          niche_id: 1,
          creator_handle: "alice", creator_name: "Alice",
          thumbnail_url: null, video_url: null, video_duration: null,
          views: 100, likes: 10, saves: 5, engagement_rate: 5.5,
          posted_at: null,
          title_zh: "睡前3件事", title_vi: "3 việc trước khi ngủ",
          sub_vi: null, hashtags_zh: [],
          adapt_level: "green", adapt_reason: "Universal.",
          eta_weeks_min: 2, eta_weeks_max: 4,
          cn_rise_pct: null, translator_notes: [],
          synth_computed_at: null, indexed_at: null,
        },
      ],
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(payload),
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinFeed(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data).toEqual(payload);

    const fetchCall = vi.mocked(globalThis.fetch).mock.calls[0];
    const [url, init] = fetchCall ?? [];
    expect(url).toBe("https://cloud-run.test/douyin/feed");
    expect((init as RequestInit | undefined)?.method).toBe("GET");
    expect((init as RequestInit | undefined)?.headers).toMatchObject({
      Authorization: "Bearer fake-jwt",
    });
  });

  it("is disabled when VITE_CLOUD_RUN_API_URL is empty", async () => {
    // Re-mock env with empty cloud-run URL.
    vi.doMock("@/lib/env", () => ({
      env: {
        VITE_SUPABASE_URL: "https://test.supabase.co",
        VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
        VITE_CLOUD_RUN_API_URL: "",
        VITE_R2_PUBLIC_URL: undefined,
      },
    }));
    vi.resetModules();
    const { useDouyinFeed: useDouyinFeed2 } = await import("./useDouyinFeed");

    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinFeed2(), { wrapper: wrapper(qc) });

    // Wait a tick — no fetch should be triggered.
    await new Promise((r) => setTimeout(r, 50));
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe("idle");

    vi.doUnmock("@/lib/env");
  });

  it("is disabled when enabled=false (caller-controlled gate)", async () => {
    const fetchSpy = vi.fn();
    globalThis.fetch = fetchSpy;
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderHook(() => useDouyinFeed(false), { wrapper: wrapper(qc) });
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
    const { result } = renderHook(() => useDouyinFeed(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toMatch(/Chưa đăng nhập/);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("surfaces error on non-OK response", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("internal error"),
      json: () => Promise.resolve({ detail: "internal error" }),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinFeed(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
  });

  it("triggers session-expired path on 401", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve("unauthorized"),
      json: () => Promise.resolve({ detail: "unauthorized" }),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useDouyinFeed(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toMatch(/session_expired/);
  });
});
