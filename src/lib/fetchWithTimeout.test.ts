/**
 * fetchWithTimeout — deadline + abort plumbing.
 *
 * Three invariants worth pinning:
 *   1. A response that arrives inside the deadline resolves normally.
 *   2. A stuck request throws a named `FetchTimeout` error after the
 *      deadline, not a generic AbortError (which would look like user
 *      cancellation to every error handler downstream).
 *   3. An external AbortSignal still wins when aborted before the
 *      deadline — we don't leak React-Query's unmount cancellation.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchWithTimeout } from "./fetchWithTimeout";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("fetchWithTimeout", () => {
  it("resolves normally when the response arrives before the deadline", async () => {
    const fake = new Response("ok", { status: 200 });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(fake),
    );
    const res = await fetchWithTimeout("https://example.test/healthy", { timeoutMs: 1_000 });
    expect(res.status).toBe(200);
  });

  it("throws FetchTimeout with a descriptive message when the deadline elapses", async () => {
    // A fetch that never resolves — relies on our timeout firing.
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: RequestInfo | URL, init?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            // Platform fetch throws a DOMException("AbortError") on abort;
            // mimic that so fetchWithTimeout's catch branch runs.
            const err = new DOMException("Aborted", "AbortError");
            reject(err);
          });
        });
      }),
    );

    let err: unknown;
    try {
      await fetchWithTimeout("https://example.test/stuck", { timeoutMs: 10 });
    } catch (e) {
      err = e;
    }
    expect(err).toBeInstanceOf(Error);
    expect((err as Error).name).toBe("FetchTimeout");
    expect((err as Error).message).toMatch(/fetch_timeout_10ms/);
  });

  it("propagates an external AbortSignal cancellation instead of masking it", async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: RequestInfo | URL, init?: RequestInit) => {
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        });
      }),
    );

    const pending = fetchWithTimeout("https://example.test/slow", {
      signal: controller.signal,
      timeoutMs: 10_000,
    });
    // Caller aborts via React-Query-style unmount long before the deadline.
    controller.abort();

    let err: unknown;
    try {
      await pending;
    } catch (e) {
      err = e;
    }
    // External abort isn't remapped — the caller sees the native
    // AbortError so their cancellation logic still kicks in.
    expect(err).toBeInstanceOf(DOMException);
    expect((err as DOMException).name).toBe("AbortError");
  });
});
