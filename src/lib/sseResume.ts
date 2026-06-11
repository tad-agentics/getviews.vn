/**
 * Persist the in-flight answer-turn stream's resume handles across tab
 * reloads. Paired with Cloud Run's 60s in-memory replay buffer (TD-4)
 * so a same-pod reconnect within the window doesn't re-bill credits.
 *
 * Caveat: the replay buffer is per-instance
 * (cloud-run/getviews_pipeline/session_store.py:40,
 * _STREAM_REPLAY_TTL_SEC = 60.0). A cross-pod reconnect (cold
 * container) misses the buffer and falls through to a fresh Gemini
 * run — credits aren't double-billed (the pending entry's
 * creditsUsed isn't replayed against the user) but the user does
 * wait through a new synthesis pass.
 *
 * Flow:
 *   1. Every time the SSE reader advances ``stream_id`` / ``seq`` we
 *      snapshot them here (tab-scoped).
 *   2. On successful ``done`` (or semantic error like
 *      ``insufficient_credits``) we clear the entry.
 *   3. AnswerScreen's bootstrap effect reads the entry on mount. If the
 *      URL session matches and the snapshot is younger than
 *      ``RESUME_MAX_AGE_MS``, the stream is re-issued with
 *      ``resume_stream_id`` + ``resume_from_seq``.
 *
 * Why ``sessionStorage`` not ``localStorage``: resume is a within-tab
 * recovery, not a cross-browser feature. ``sessionStorage`` evaporates
 * when the tab closes, which is exactly the semantics we want.
 *
 * ``RESUME_MAX_AGE_MS`` is deliberately 15s below the 60s server TTL
 * so clock drift / trip-time doesn't push a resume outside the replay
 * window (mismatched values previously claimed 120s server TTL while
 * the real ttl was 60s — every reload >60s actually hit fresh Gemini).
 */

const KEY = "gv:pending-answer-stream-v1";
const RESUME_MAX_AGE_MS = 45_000;

/** Client-side mirror of ``answer_session.append_turn`` credit accounting. */
export function optimisticAnswerCreditsUsed(
  turnKind: PendingAnswerTurnKind,
  sessionFormat?: string | null,
): number {
  if (turnKind === "script") return 3;
  if (turnKind === "primary") {
    if (sessionFormat === "script") return 3;
    if (sessionFormat === "video") return 2;
    return 1;
  }
  return 0;
}

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
  /** Billable credits for this turn — aligns with ``answer_turns.credits_used``. */
  creditsUsed: number;
  /** Session row ``format`` — when ``creditsUsed`` is absent (legacy blob), infer billing. */
  sessionFormat?: string | null;
  /** Video diagnosis win/flop — omitted on non-video turns. */
  videoMode?: "win" | "flop" | null;
}

/** True when TD-4 replay can reconnect (sessionStorage or in-memory hook handles). */
export function hasAnswerStreamReplayHandles(
  sessionId: string,
  hookStreamId: string | null | undefined,
  hookLastSeq: number,
  now: number = Date.now(),
): boolean {
  if (loadPendingAnswerStream(sessionId, now)) return true;
  return Boolean(hookStreamId && hookLastSeq > 0);
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
  let parsed: PendingAnswerStream | (Omit<PendingAnswerStream, "creditsUsed"> & { creditsUsed?: number });
  try {
    parsed = JSON.parse(raw) as typeof parsed;
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
  const fmt =
    "sessionFormat" in parsed && parsed.sessionFormat !== undefined
      ? parsed.sessionFormat
      : null;
  const videoMode =
    "videoMode" in parsed && parsed.videoMode !== undefined ? parsed.videoMode : null;
  const creditsUsed =
    typeof parsed.creditsUsed === "number"
      ? parsed.creditsUsed
      : optimisticAnswerCreditsUsed(parsed.turnKind, fmt);
  return { ...parsed, creditsUsed, sessionFormat: fmt, videoMode };
}

export const PENDING_ANSWER_STREAM_KEY = KEY;
export const PENDING_ANSWER_STREAM_MAX_AGE_MS = RESUME_MAX_AGE_MS;
