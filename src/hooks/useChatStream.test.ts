/**
 * useChatStream — SSE parsing regression tests.
 *
 * Covers the line-buffer logic introduced in cc9d137 that prevents partial
 * SSE lines from being silently dropped when a chunk boundary falls mid-JSON.
 *
 * All tests are fully offline: fetch() and supabase are mocked.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// ── Module mocks (hoisted before imports) ────────────────────────────────────

// vi.hoisted runs before vi.mock factories so we can reference this in the factory.
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

import { useChatStream } from "./useChatStream";

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

describe("useChatStream — SSE line buffer", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = makeQc();
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
  });

  it("parses a complete SSE line in a single chunk", async () => {
    const chunk = `data: {"stream_id":"abc","seq":1,"delta":"hello","done":false}\n\ndata: {"stream_id":"abc","seq":2,"delta":"","done":true}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream([chunk])));

    const { result } = renderHook(() => useChatStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("done"), { timeout: 3000 });
    expect(result.current.text).toBe("hello");
  });

  it("handles SSE line split across two chunks", async () => {
    // The JSON payload is split exactly mid-way — buffer must join before parsing.
    const part1 = `data: {"stream_id":"abc","seq":1,"delta":"hel`;
    const part2 = `lo","done":false}\n\ndata: {"stream_id":"abc","seq":2,"delta":"","done":true}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream([part1, part2])));

    const { result } = renderHook(() => useChatStream(), { wrapper: wrapper(qc) });

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

    const { result } = renderHook(() => useChatStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("done"), { timeout: 3000 });
    expect(result.current.error).toBeNull();
  });

  it("returns error on 402 insufficient credits", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 402 })),
    );

    const { result } = renderHook(() => useChatStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(result.current.error).toBe("insufficient_credits");
  });

  it("handles stream error token", async () => {
    const chunk = `data: {"error":"analysis_timeout","done":true}\n\n`;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(mockFetchStream([chunk])));

    const { result } = renderHook(() => useChatStream(), { wrapper: wrapper(qc) });

    result.current.stream(BASE_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(result.current.error).toBe("analysis_timeout");
  });
});
