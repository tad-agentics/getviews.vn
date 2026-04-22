/**
 * Persist the in-flight answer-turn stream's resume handles across tab
 * reloads. Paired with Cloud Run's 120s in-memory replay buffer (TD-4)
 * so a crash mid-stream doesn't re-bill credits on reconnect.
 *
 * Flow:
 *   1. Every time the SSE reader advances ``stream_id`` / ``seq`` we
 *      snapshot them here (tab-scoped).
 *   2. On successful ``done`` (or semantic error like
 *      ``insufficient_credits``) we clear the entry.
 *   3. AnswerScreen's bootstrap effect reads the entry on mount. If the
 *      URL session matches and the snapshot is younger than
 *      ``RESUME_MAX_AGE_MS``, the stream is re-issued with
 *      ``resume_stream_id`` + ``resume_from_seq`` — Cloud Run replays
 *      the token stream from its buffer, does not re-run Gemini, and
 *      does not decrement credits a second time.
 *
 * Why ``sessionStorage`` not ``localStorage``: resume is a within-tab
 * recovery, not a cross-browser feature. ``sessionStorage`` evaporates
 * when the tab closes, which is exactly the semantics we want.
 *
 * ``RESUME_MAX_AGE_MS`` is deliberately 30s below the 120s server TTL
 * so clock drift / trip-time doesn't push a resume outside the replay
 * window.
 */

const KEY = "gv:pending-answer-stream-v1";
const RESUME_MAX_AGE_MS = 90_000;

export type PendingAnswerTurnKind =
  | "primary"
  | "timing"
  | "creators"
  | "script"
  | "generic";

export interface PendingAnswerStream {
  sessionId: string;
  streamId: string;
  seq: number;
  query: string;
  turnKind: PendingAnswerTurnKind;
  /** ``Date.now()`` when the stream was first opened. */
  startedAt: number;
}

function safeStorage(): Storage | null {
  try {
    return typeof sessionStorage === "undefined" ? null : sessionStorage;
  } catch {
    return null;
  }
}

export function savePendingAnswerStream(entry: PendingAnswerStream): void {
  const store = safeStorage();
  if (!store) return;
  try {
    store.setItem(KEY, JSON.stringify(entry));
  } catch {
    /* quota exceeded, SSR, or disabled — ignore */
  }
}

export function clearPendingAnswerStream(): void {
  const store = safeStorage();
  if (!store) return;
  try {
    store.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Read the pending entry for ``sessionId``. Returns ``null`` when no
 * entry exists, when it belongs to a different session, when it's
 * missing resume handles, or when it's older than the replay TTL.
 * Stale entries are cleared as a side-effect.
 */
export function loadPendingAnswerStream(
  sessionId: string,
  now: number = Date.now(),
): PendingAnswerStream | null {
  const store = safeStorage();
  if (!store) return null;
  let raw: string | null;
  try {
    raw = store.getItem(KEY);
  } catch {
    return null;
  }
  if (!raw) return null;
  let parsed: PendingAnswerStream;
  try {
    parsed = JSON.parse(raw) as PendingAnswerStream;
  } catch {
    clearPendingAnswerStream();
    return null;
  }
  if (parsed.sessionId !== sessionId) return null;
  if (!parsed.streamId || parsed.seq <= 0) return null;
  if (typeof parsed.startedAt !== "number" || now - parsed.startedAt > RESUME_MAX_AGE_MS) {
    clearPendingAnswerStream();
    return null;
  }
  return parsed;
}

export const PENDING_ANSWER_STREAM_KEY = KEY;
export const PENDING_ANSWER_STREAM_MAX_AGE_MS = RESUME_MAX_AGE_MS;
