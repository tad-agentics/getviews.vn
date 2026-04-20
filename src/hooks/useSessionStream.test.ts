/**
 * useSessionStream — SSE parsing regression + payload-delivery tests.
 *
 * Covers the line-buffer logic (prevents partial SSE lines from being
 * silently dropped at chunk boundaries) plus the `onFinal` callback that
 * delivers report payloads to `/answer` consumers.
 *
 * All tests are fully offline: fetch() and supabase are mocked.
 */

import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// ── Module mocks (hoisted before imports) ────────────────────────────────────

const { mockGetSession } = vi.hoisted(() => ({
  mockGetSession: vi.fn().mockResolvedValue({
    data: { session: { access_token: "test-token" } },
  }),
}));

vi.mock("@/lib/env", () => ({
  env: {
    VITE_SUPABASE_URL: "https://test.supabase.co",
    VITE_SUPABASE_PUBLISHABLE_KEY: "test-key",
    VITE_CLOUD_RUN_API_URL: undefined,
  },
}));

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: { getSession: mockGetSession },
  },
}));

vi.mock("@/hooks/useChatSession", () => ({
  chatKeys: {
    messages: (id: string) => ["chat", "messages", id],
    sessions: () => ["chat", "sessions"],
    session: (id: string) => ["chat", "session", id],
  },
}));

import { useSessionStream } from "./useSessionStream";

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function wrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

/** Build a mock fetch Response whose body streams the given string chunks. */
function mockFetchStream(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder();
  let i = 0;
  const stream = new ReadableStream({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encoder.encode(chunks[i++]));
      } else {
        controller.close();
      }
    },
  });
  return new Response(stream, { status, headers: { "Content-Type": "text/event-stream" } });
}

const BASE_PARAMS = {
  sessionId: "session-1",
  query: "test",
  intentType: "follow_up_unclassifiable", // not in CLOUD_RUN_INTENTS → hits /api/chat
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useSessionStream — SSE line buffer", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = makeQc();
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
  });

  it("parses a complete SSE line in a single chunk", async () => {
    const chunk = `data: {"stream_id":"abc","seq":1,"delta":"hello","done":false}\n\ndata: {"stream_id":"abc","seq":2,"delta":"","done":true}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream([chunk])));

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("done"), { timeout: 3000 });
    expect(result.current.text).toBe("hello");
  });

  it("handles SSE line split across two chunks", async () => {
    // The JSON payload is split exactly mid-way — buffer must join before parsing.
    const part1 = `data: {"stream_id":"abc","seq":1,"delta":"hel`;
    const part2 = `lo","done":false}\n\ndata: {"stream_id":"abc","seq":2,"delta":"","done":true}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream([part1, part2])));

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("done"), { timeout: 3000 });
    expect(result.current.text).toBe("hello");
  });

  it("sets status to done when the done token arrives", async () => {
    const chunks = [
      `data: {"stream_id":"abc","seq":1,"delta":"world","done":false}\n\n`,
      `data: {"stream_id":"abc","seq":2,"delta":"","done":true}\n\n`,
    ];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream(chunks)));

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("done"), { timeout: 3000 });
    expect(result.current.error).toBeNull();
  });

  it("returns error on 402 insufficient credits", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 402 })),
    );

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(result.current.error).toBe("insufficient_credits");
  });

  it("handles stream error token", async () => {
    const chunk = `data: {"error":"analysis_timeout","done":true}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream([chunk])));

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(result.current.error).toBe("analysis_timeout");
  });
});

describe("useSessionStream — report payload delivery", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = makeQc();
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
  });

  it("surfaces finalPayload and fires onFinal when a payload token precedes done", async () => {
    const payload = { kind: "pattern", report: { tldr: "example" } };
    const chunks = [
      `data: {"stream_id":"a","seq":1,"payload":${JSON.stringify(payload)},"done":false}\n\n`,
      `data: {"stream_id":"a","seq":2,"done":true}\n\n`,
    ];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream(chunks)));

    const onFinal = vi.fn();
    const { result } = renderHook(
      () => useSessionStream<typeof payload>({ onFinal }),
      { wrapper: wrapper(qc) },
    );

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("done"), { timeout: 3000 });
    expect(result.current.finalPayload).toEqual(payload);
    expect(onFinal).toHaveBeenCalledOnce();
    expect(onFinal).toHaveBeenCalledWith(payload);
  });

  it("does not fire onFinal when the stream errors", async () => {
    const chunk = `data: {"error":"timeout","done":true}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream([chunk])));

    const onFinal = vi.fn();
    const { result } = renderHook(
      () => useSessionStream({ onFinal }),
      { wrapper: wrapper(qc) },
    );

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(result.current.finalPayload).toBeNull();
    expect(onFinal).not.toHaveBeenCalled();
  });
});
