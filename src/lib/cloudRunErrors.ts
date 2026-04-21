/**
 * Read an error body from a non-2xx Cloud Run response.
 *
 * FastAPI wraps ``raise HTTPException(detail="…")`` as ``{"detail":"…"}``;
 * our own handlers sometimes emit ``{"error":"…"}``. A plain ``text()``
 * call would show the user the raw JSON, which looks like a bug. This
 * helper pulls the human-facing string out of either shape, and falls
 * back to the raw body or ``HTTP <status>`` so the error is never empty.
 *
 * Shared by the four Cloud Run analysis hooks (video / channel / script /
 * kol) + the script save / draft / export hooks — keeps error copy
 * consistent and removes duplicate JSON-parsing boilerplate.
 */
export async function readErrorDetail(res: Response): Promise<string> {
  const raw = await res.text();
  if (!raw) return `HTTP ${res.status}`;
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown; error?: unknown };
    if (typeof parsed.detail === "string" && parsed.detail.trim()) return parsed.detail;
    if (typeof parsed.error === "string" && parsed.error.trim()) return parsed.error;
  } catch {
    /* body is not JSON — fall through to raw */
  }
  return raw;
}
