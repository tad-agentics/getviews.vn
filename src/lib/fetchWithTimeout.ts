/**
 * Wrap `fetch` with an AbortSignal-backed timeout.
 *
 * The four Cloud Run analysis hooks (video / channel / script / kol)
 * had no deadline on their fetches. If Gemini stalls or the Cloud Run
 * container is slow-booting, the UI sits on "Đang tải…" forever — users
 * assume the app is frozen. This helper caps that wait at a bounded
 * time and throws a named error the screen can surface cleanly.
 *
 * Why a timeout and not a max-retries loop: analysis calls are
 * expensive (Gemini + EnsembleData credits). Auto-retrying a timed-out
 * call would double the cost for marginal success odds. The operator
 * clicks "Thử lại" when they actually want another attempt.
 *
 * Design notes:
 *   - Merges an externally-supplied `init.signal` with our deadline so
 *     a caller's cancellation (e.g. React-Query unmount) still fires.
 *   - Default 30s matches Cloud Run's free-tier request budget;
 *     callers that know their job is longer (e.g. `/video/analyze` can
 *     legitimately take 45-60s on a cold start) pass `{ timeoutMs }`.
 *   - Errors propagate with `err.name = "FetchTimeout"` so the shared
 *     `analysisErrorCopy` helper can render a specific message.
 */
export interface FetchWithTimeoutInit extends RequestInit {
  /** Deadline in ms. Defaults to 30_000 (30 seconds). */
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 30_000;

export async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: FetchWithTimeoutInit = {},
): Promise<Response> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal: externalSignal, ...rest } = init;

  const controller = new AbortController();

  // Forward external cancellation into our controller so React-Query's
  // cleanup still aborts the request on unmount.
  const onExternalAbort = () => controller.abort(externalSignal?.reason);
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort(externalSignal.reason);
    else externalSignal.addEventListener("abort", onExternalAbort, { once: true });
  }

  const timeoutId = setTimeout(() => {
    const err = new Error(`fetch_timeout_${timeoutMs}ms`);
    err.name = "FetchTimeout";
    controller.abort(err);
  }, timeoutMs);

  try {
    return await fetch(input, { ...rest, signal: controller.signal });
  } catch (err) {
    // When the abort was triggered by our timeout, surface that as a
    // named error instead of the generic AbortError the platform
    // raises. Lets `analysisErrorCopy` render a specific message.
    if (err instanceof DOMException && err.name === "AbortError") {
      const reason = controller.signal.reason;
      if (reason instanceof Error && reason.name === "FetchTimeout") {
        throw reason;
      }
      // External caller aborted — propagate as-is.
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
    if (externalSignal) externalSignal.removeEventListener("abort", onExternalAbort);
  }
}
