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
    // Any non-empty URL is enough — tests stub `fetch` directly, so the
    // value is only used to construct the request URL we then assert on.
    VITE_CLOUD_RUN_API_URL: "https://cloud-run.test",
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

describe("useSessionStream — answer_turn TD-4 retry on stream drop", () => {
  let qc: QueryClient;

  beforeEach(() => {
    qc = makeQc();
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
  });

  const ANSWER_PARAMS = {
    mode: "answer_turn" as const,
    answerSessionId: "sess-1",
    query: "trend tuần này",
    turnKind: "primary" as const,
  };

  it("retries with resume params when the done marker never arrives, carrying payload forward", async () => {
    const payload = { kind: "pattern", report: { tldr: "carried" } };
    // Attempt 1: seq=1 payload, then EOF (no done marker) → stream_failed
    const firstChunks = [
      `data: {"stream_id":"sid-1","seq":1,"payload":${JSON.stringify(payload)},"done":false}\n\n`,
    ];
    // Attempt 2: seq=2 done only (what the server's replay buffer would emit
    // for `resume_from_seq=1`: it skips cached chunks up to that seq and
    // emits the trailing done token).
    const secondChunks = [
      `data: {"stream_id":"sid-1","seq":2,"delta":"","done":true}\n\n`,
    ];
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockFetchStream(firstChunks))
      .mockResolvedValueOnce(mockFetchStream(secondChunks));
    vi.stubGlobal("fetch", fetchMock);

    const onFinal = vi.fn();
    const { result } = renderHook(
      () => useSessionStream<typeof payload>({ onFinal }),
      { wrapper: wrapper(qc) },
    );

    let streamResult: Awaited<ReturnType<typeof result.current.stream>> | undefined;
    void (async () => {
      streamResult = await result.current.stream(ANSWER_PARAMS);
    })();

    await waitFor(() => expect(result.current.status).toBe("done"), { timeout: 3000 });
    expect(result.current.finalPayload).toEqual(payload);
    expect(streamResult?.ok).toBe(true);
    if (streamResult?.ok) expect(streamResult.finalPayload).toEqual(payload);
    expect(onFinal).toHaveBeenCalledWith(payload);

    // Exactly two fetches — original plus single retry — and the retry
    // carries `resume_stream_id` + `resume_from_seq` from the captured state.
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const firstUrl = fetchMock.mock.calls[0][0] as string;
    const secondUrl = fetchMock.mock.calls[1][0] as string;
    expect(firstUrl).not.toContain("resume_stream_id");
    expect(secondUrl).toContain("resume_stream_id=sid-1");
    expect(secondUrl).toContain("resume_from_seq=1");
  });

  it("stops after one retry and surfaces stream_failed if the drop persists", async () => {
    // Both attempts drop after seq=1 with no done token.
    const makeChunks = () => [
      `data: {"stream_id":"sid-x","seq":1,"payload":{"kind":"generic"},"done":false}\n\n`,
    ];
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockFetchStream(makeChunks()))
      .mockResolvedValueOnce(mockFetchStream(makeChunks()));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    let streamResult: Awaited<ReturnType<typeof result.current.stream>> | undefined;
    void (async () => {
      streamResult = await result.current.stream(ANSWER_PARAMS);
    })();

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(streamResult?.ok).toBe(false);
    if (streamResult && !streamResult.ok) expect(streamResult.error).toBe("stream_failed");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not retry 402/429 (semantic errors must surface on first attempt)", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 402 }));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    result.current.stream(ANSWER_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(result.current.error).toBe("insufficient_credits");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("does not retry in-band error tokens (e.g. insufficient_credits from the server)", async () => {
    const chunk = `data: {"stream_id":"sid-y","seq":1,"done":true,"error":"insufficient_credits"}\n\n`;
    const fetchMock = vi.fn().mockResolvedValue(mockFetchStream([chunk]));
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useSessionStream(), { wrapper: wrapper(qc) });

    result.current.stream(ANSWER_PARAMS);

    await waitFor(() => expect(result.current.status).toBe("error"), { timeout: 3000 });
    expect(result.current.error).toBe("insufficient_credits");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
