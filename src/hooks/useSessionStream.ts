/**
 * Phase C.1.0 — shared session-stream hook.
 *
 * - **Chat / pipeline** (`mode` omitted or `chat`): `POST` Cloud Run `/stream` or Vercel `/api/chat`.
 * - **Answer research** (`mode: 'answer_turn'`): `POST` `/answer/sessions/:id/turns` (SSE, §J `ReportV1`).
 */

import { useCallback, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { useQueryClient, type QueryClient, type QueryKey } from "@tanstack/react-query";

import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { logUsage } from "@/lib/logUsage";
import {
  clearPendingAnswerStream,
  savePendingAnswerStream,
  type PendingAnswerTurnKind,
} from "@/lib/sseResume";
import { chatKeys } from "./useChatSession";

/**
 * D.5.2 SSE observability — three usage_events fired from the answer_turn
 * retry loop to make the drop-rate dashboard possible:
 *
 *   sse_drop             unexpected EOF, non-2xx, or body-less response.
 *                         metadata: { endpoint, session_id, last_seq, reason }
 *   sse_resume_attempt   retry issued with resume_stream_id + resume_from_seq.
 *                         metadata: { endpoint, session_id, attempted_seq,
 *                                     cross_pod_likely }
 *   sse_resume_success   retry attempt produced a successful done token.
 *                         metadata: { endpoint, session_id }
 *
 * See supabase/migrations/20260502000000_usage_events_d52_sse.sql for the
 * dashboard allow-list + partial index.
 */
type SseDropReason = "network" | "server" | "abort" | "unknown";
const ANSWER_SSE_ENDPOINT = "/answer/sessions/:id/turns";

const CLOUD_RUN_URL = env.VITE_CLOUD_RUN_API_URL;
const VERCEL_CHAT_URL = "/api/chat";

/**
 * TD-4 — a single auto-retry covers the common network-blip case where the
 * client received the `seq=1` payload token but lost the connection before
 * the `seq=2` done marker arrived. On retry we pass `resume_stream_id` +
 * `resume_from_seq` so the server replays from its 120s chunk buffer and
 * does **not** re-run Gemini / re-bill credits (see `cloud-run/main.py`).
 * Higher retry counts would risk unbounded cost if the cache missed and
 * the server fell through to a fresh run.
 */
const MAX_ANSWER_RETRIES = 1;

/**
 * Idle-timeout for the SSE reader loop. If no bytes arrive for this long
 * the stream is considered hung and we surface ``stream_timeout``. The
 * retry loop will then re-attempt with resume params, letting Cloud Run's
 * 120s replay buffer recover in-flight work without re-billing. Rolling
 * timer — every chunk resets it, so long but healthy streams don't trip.
 */
const SSE_IDLE_TIMEOUT_MS = 45_000;

const CLOUD_RUN_INTENTS = new Set([
  "video_diagnosis",
  "competitor_profile",
  "own_channel",
  "content_directions",
  "trend_spike",
  "creator_search",
  "shot_list",
  // Wave 4 PR #3 — two URLs → /stream with the compare_videos intent.
  // Server orchestrates both diagnoses + delta in one envelope.
  "compare_videos",
]);

export type StreamStatus = "idle" | "streaming" | "done" | "error";

export interface StreamState<TPayload = unknown> {
  status: StreamStatus;
  text: string;
  streamId: string | null;
  lastSeq: number;
  error: string | null;
  finalPayload: TPayload | null;
}

export interface StreamOptions<TPayload = unknown> {
  onFinal?: (payload: TPayload) => void;
  invalidateKeys?: QueryKey[];
}

export type AnswerTurnKind = "primary" | "timing" | "creators" | "script" | "generic";

export type StreamArgs =
  | {
      mode?: "chat";
      sessionId: string;
      query: string;
      intentType: string;
      resumeStreamId?: string;
      lastSeq?: number;
      nicheLabel?: string;
    }
  | {
      mode: "answer_turn";
      answerSessionId: string;
      query: string;
      turnKind: AnswerTurnKind;
      resumeStreamId?: string;
      lastSeq?: number;
      /**
       * Unix ms timestamp of the original stream — preserved across
       * reloads so the sessionStorage entry keeps its age relative to
       * Cloud Run's 120s replay-buffer TTL (``src/lib/sseResume.ts``).
       * Omit on the first attempt; caller passes it back when resuming
       * from a stored pending entry.
       */
      startedAt?: number;
    };

export type StreamResult<TPayload = unknown> =
  | { ok: true; finalPayload: TPayload | null }
  | { ok: false; error: string };

type AnswerSseOutcome<T> = {
  ok: boolean;
  error?: string;
  streamId: string | null;
  lastSeq: number;
  payload: T | null;
};

export function useSessionStream<TPayload = unknown>(
  options: StreamOptions<TPayload> = {},
) {
  const qc = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<StreamState<TPayload>>({
    status: "idle",
    text: "",
    streamId: null,
    lastSeq: 0,
    error: null,
    finalPayload: null,
  });

  const stream = useCallback(
    async (args: StreamArgs): Promise<StreamResult<TPayload>> => {
      abortRef.current?.abort();
      const abort = new AbortController();
      abortRef.current = abort;

      setState({
        status: "streaming",
        text: "",
        streamId: args.resumeStreamId ?? null,
        lastSeq: args.lastSeq ?? 0,
        error: null,
        finalPayload: null,
      });

      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) throw new Error("No session");

        if (args.mode === "answer_turn") {
          if (!CLOUD_RUN_URL) {
            setState((s) => ({ ...s, status: "error", error: "no_cloud_run" }));
            return { ok: false, error: "no_cloud_run" };
          }

          // Retry loop — carries captured `streamId`/`lastSeq`/`payload`
          // across attempts so if the first attempt got the payload but lost
          // the done marker, the second attempt just asks the server to
          // replay seq=N+1 and we surface `finalPayload` from the first run.
          let resumeStreamId = args.resumeStreamId ?? null;
          let resumeSeq = args.lastSeq ?? 0;
          let carriedPayload: TPayload | null = null;
          // Preserved across page reloads so the replay TTL window is
          // measured from the stream's true origin, not each retry.
          const startedAt = args.startedAt ?? Date.now();
          const persistProgress = (streamId: string, seq: number) => {
            if (!streamId || seq <= 0) return;
            savePendingAnswerStream({
              sessionId: args.answerSessionId,
              streamId,
              seq,
              query: args.query,
              turnKind: args.turnKind as PendingAnswerTurnKind,
              startedAt,
            });
          };

          for (let attempt = 0; attempt <= MAX_ANSWER_RETRIES; attempt++) {
            const url = new URL(
              `${CLOUD_RUN_URL}/answer/sessions/${args.answerSessionId}/turns`,
            );
            const isResume = Boolean(resumeStreamId) && resumeSeq > 0;
            if (isResume) {
              url.searchParams.set("resume_stream_id", resumeStreamId!);
              url.searchParams.set("resume_from_seq", String(resumeSeq));
              // D.5.2 — record every retry attempt the client makes so the
              // dashboard can compute retry-success vs retry-abandon ratios.
              // `cross_pod_likely` is a hint for D.0.v — the server-side
              // replay buffer is per-instance, so a reconnect to a fresh
              // cold container produces a cache miss and re-runs Gemini.
              // Internal retries (attempt > 0) reconnect within ~seconds,
              // almost certainly to the same container. Caller-supplied
              // resumes (attempt === 0 + resume params pre-populated — page
              // refresh / tab reopen) have arbitrary delay and are the
              // class the dashboard actually wants to threshold on.
              logUsage("sse_resume_attempt", {
                endpoint: ANSWER_SSE_ENDPOINT,
                session_id: args.answerSessionId,
                attempted_seq: resumeSeq,
                cross_pod_likely: attempt === 0,
              });
            }
            const res = await fetch(url.toString(), {
              method: "POST",
              headers: {
                Authorization: `Bearer ${session.access_token}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({ query: args.query, kind: args.turnKind }),
              signal: abort.signal,
            });

            if (res.status === 402) {
              // Semantic error — no retry will help; clear pending so
              // a reload doesn't loop.
              clearPendingAnswerStream();
              setState((s) => ({ ...s, status: "error", error: "insufficient_credits" }));
              return { ok: false, error: "insufficient_credits" };
            }
            if (res.status === 429) {
              clearPendingAnswerStream();
              setState((s) => ({ ...s, status: "error", error: "daily_free_limit" }));
              return { ok: false, error: "daily_free_limit" };
            }
            if (!res.ok) {
              logUsage("sse_drop", {
                endpoint: ANSWER_SSE_ENDPOINT,
                session_id: args.answerSessionId,
                last_seq: resumeSeq,
                reason: "server" satisfies SseDropReason,
                http_status: res.status,
              });
              clearPendingAnswerStream();
              setState((s) => ({ ...s, status: "error", error: `http_${res.status}` }));
              return { ok: false, error: `http_${res.status}` };
            }
            if (!res.body) {
              logUsage("sse_drop", {
                endpoint: ANSWER_SSE_ENDPOINT,
                session_id: args.answerSessionId,
                last_seq: resumeSeq,
                reason: "server" satisfies SseDropReason,
              });
              clearPendingAnswerStream();
              setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
              return { ok: false, error: "stream_failed" };
            }

            const outcome: AnswerSseOutcome<TPayload> = await consumeAnswerSse(
              res,
              setState,
              qc,
              options,
              args.answerSessionId,
              carriedPayload,
              persistProgress,
            );
            carriedPayload = outcome.payload;
            if (outcome.streamId) resumeStreamId = outcome.streamId;
            if (outcome.lastSeq > resumeSeq) resumeSeq = outcome.lastSeq;

            if (outcome.ok) {
              // Server confirmed the turn landed — drop the pending entry
              // so a subsequent reload doesn't attempt a stale resume.
              clearPendingAnswerStream();
              if (isResume) {
                // The retry paid off — the dashboard ratio `resume_success /
                // resume_attempt` measures whether the server-side replay
                // buffer is actually doing its job.
                logUsage("sse_resume_success", {
                  endpoint: ANSWER_SSE_ENDPOINT,
                  session_id: args.answerSessionId,
                });
              }
              return { ok: true, finalPayload: outcome.payload };
            }
            // Consumer failures are sse_drop. `stream_failed` is unexpected
            // EOF / malformed frames; in-band `done: true` + `error` tokens
            // surface as their own error string.
            logUsage("sse_drop", {
              endpoint: ANSWER_SSE_ENDPOINT,
              session_id: args.answerSessionId,
              last_seq: outcome.lastSeq,
              reason: (outcome.error === "stream_failed" ||
              outcome.error === "stream_timeout"
                ? "network"
                : "unknown") satisfies SseDropReason,
              error: outcome.error ?? "stream_failed",
            });
            // Only transport-level errors are retryable — semantic errors
            // (e.g. `insufficient_credits` from the server's in-band error
            // token) must surface on the first attempt. `stream_timeout`
            // is treated like `stream_failed`: the server may still be
            // generating and a resume will land on the replay buffer.
            const retryable =
              (outcome.error === "stream_failed" ||
                outcome.error === "stream_timeout") &&
              Boolean(resumeStreamId) &&
              attempt < MAX_ANSWER_RETRIES;
            if (!retryable) {
              // Exhausted retries on a non-recoverable outcome — stale
              // pending entry would cause an auto-resume on reload to
              // hit the same error. Drop it.
              clearPendingAnswerStream();
              return { ok: false, error: outcome.error ?? "stream_failed" };
            }
            // Loop to next attempt with resume params set.
          }

          clearPendingAnswerStream();
          return { ok: false, error: "stream_failed" };
        }

        const intentType = args.intentType;
        const useCloudRun = CLOUD_RUN_INTENTS.has(intentType);
        if (useCloudRun && !CLOUD_RUN_URL) {
          console.warn(
            `[useSessionStream] Cloud Run URL not set — routing ${intentType} to Vercel fallback`,
          );
        }
        const endpoint =
          useCloudRun && CLOUD_RUN_URL ? `${CLOUD_RUN_URL}/stream` : VERCEL_CHAT_URL;

        const res = await fetch(endpoint, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: args.sessionId,
            query: args.query,
            intent_type: intentType,
            stream_id: args.resumeStreamId,
            last_seq: args.lastSeq,
            niche_label: args.nicheLabel,
          }),
          signal: abort.signal,
        });

        if (res.status === 402) {
          setState((s) => ({ ...s, status: "error", error: "insufficient_credits" }));
          return { ok: false, error: "insufficient_credits" };
        }
        if (res.status === 429) {
          setState((s) => ({ ...s, status: "error", error: "daily_free_limit" }));
          return { ok: false, error: "daily_free_limit" };
        }
        if (!res.ok) {
          setState((s) => ({ ...s, status: "error", error: `http_${res.status}` }));
          return { ok: false, error: `http_${res.status}` };
        }
        if (!res.body) {
          setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
          return { ok: false, error: "stream_failed" };
        }

        return await consumeChatSse(
          res,
          setState,
          qc,
          options,
          args.sessionId,
          args.resumeStreamId,
          args.lastSeq,
        );
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          return { ok: false, error: "aborted" };
        }
        setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
        return { ok: false, error: "stream_failed" };
      }
    },
    [qc, options],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, status: "idle" }));
  }, []);

  const reset = useCallback(() => {
    setState({
      status: "idle",
      text: "",
      streamId: null,
      lastSeq: 0,
      error: null,
      finalPayload: null,
    });
  }, []);

  return { ...state, stream, abort, reset };
}

type SetState<T> = Dispatch<SetStateAction<StreamState<T>>>;

/**
 * Wrap ``reader.read()`` in a rolling idle timeout. Resolves with
 * ``{timedOut: true}`` instead of throwing so the caller can run the
 * existing "log sse_drop + surface stream_timeout" flow.
 */
async function readWithIdleTimeout<T>(
  reader: ReadableStreamDefaultReader<T>,
  idleMs: number,
): Promise<ReadableStreamReadResult<T> | { timedOut: true }> {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const timeoutPromise = new Promise<{ timedOut: true }>((resolve) => {
    timer = setTimeout(() => resolve({ timedOut: true }), idleMs);
  });
  try {
    return await Promise.race([reader.read(), timeoutPromise]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function consumeAnswerSse<TPayload>(
  res: Response,
  setState: SetState<TPayload>,
  qc: QueryClient,
  options: StreamOptions<TPayload>,
  _answerSessionId: string,
  carriedPayload: TPayload | null = null,
  onProgress?: (streamId: string, seq: number) => void,
): Promise<AnswerSseOutcome<TPayload>> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let text = "";
  let lastStreamId: string | null = null;
  let lastSeq = 0;
  // Seed with any payload captured on a previous attempt so the done-marker
  // from a replay-only second fetch still resolves to a non-null finalPayload.
  let payload: TPayload | null = carriedPayload;
  let buffer = "";

  while (true) {
    const chunk = await readWithIdleTimeout(reader, SSE_IDLE_TIMEOUT_MS);
    if ("timedOut" in chunk) {
      // Cancel the underlying body stream so the fetch Promise rejects
      // and the AbortController's signal sees it. Then surface the
      // idle-timeout so the outer retry loop tries the replay path.
      try { await reader.cancel(); } catch { /* ignore */ }
      setState((s) => ({ ...s, status: "error", error: "stream_timeout" }));
      return { ok: false, error: "stream_timeout", streamId: lastStreamId, lastSeq, payload };
    }
    const { done, value } = chunk;
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const row = line.replace(/\r$/, "");
      if (!row.startsWith("data: ")) continue;
      try {
        const token = JSON.parse(row.slice(6)) as {
          stream_id?: string;
          seq?: number;
          delta?: string;
          done?: boolean;
          error?: string;
          payload?: TPayload;
        };
        if (token.stream_id) lastStreamId = token.stream_id;
        if (typeof token.seq === "number") lastSeq = token.seq;
        if (token.payload !== undefined) payload = token.payload;
        if (token.delta) text += token.delta;
        // Persist resume handles whenever they advance — the outer
        // ``persistProgress`` writes to sessionStorage so a tab reload
        // mid-stream can reconnect to Cloud Run's replay buffer.
        if (onProgress && lastStreamId) onProgress(lastStreamId, lastSeq);
        if (token.done) {
          if (token.error) {
            setState({
              status: "error",
              text,
              streamId: lastStreamId,
              lastSeq,
              error: token.error,
              finalPayload: null,
            });
            void qc.invalidateQueries({ queryKey: ["profile"] });
            void qc.invalidateQueries({ queryKey: ["credits"] });
            return { ok: false, error: token.error, streamId: lastStreamId, lastSeq, payload };
          }
          setState({
            status: "done",
            text,
            streamId: lastStreamId,
            lastSeq,
            error: null,
            finalPayload: payload,
          });
          void qc.invalidateQueries({ queryKey: ["profile"] });
          void qc.invalidateQueries({ queryKey: ["credits"] });
          for (const key of options.invalidateKeys ?? []) {
            void qc.invalidateQueries({ queryKey: key });
          }
          if (payload !== null && options.onFinal) {
            options.onFinal(payload);
          }
          return { ok: true, streamId: lastStreamId, lastSeq, payload };
        }
        if (token.error) {
          setState((s) => ({
            ...s,
            status: "error",
            error: token.error ?? "stream_failed",
          }));
          void qc.invalidateQueries({ queryKey: ["profile"] });
          return {
            ok: false,
            error: token.error ?? "stream_failed",
            streamId: lastStreamId,
            lastSeq,
            payload,
          };
        }
        setState((s) => ({ ...s, text, streamId: lastStreamId, lastSeq }));
      } catch {
        /* skip malformed */
      }
    }
  }
  setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
  return { ok: false, error: "stream_failed", streamId: lastStreamId, lastSeq, payload };
}

async function consumeChatSse<TPayload>(
  res: Response,
  setState: SetState<TPayload>,
  qc: QueryClient,
  options: StreamOptions<TPayload>,
  sessionId: string,
  resumeStreamId: string | undefined,
  resumeSeq: number | undefined,
): Promise<StreamResult<TPayload>> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let text = "";
  let lastStreamId: string | null = resumeStreamId ?? null;
  let lastSeq = resumeSeq ?? 0;
  let payload: TPayload | null = null;
  let buffer = "";

  while (true) {
    const chunk = await readWithIdleTimeout(reader, SSE_IDLE_TIMEOUT_MS);
    if ("timedOut" in chunk) {
      try { await reader.cancel(); } catch { /* ignore */ }
      setState((s) => ({ ...s, status: "error", error: "stream_timeout" }));
      return { ok: false, error: "stream_timeout" };
    }
    const { done, value } = chunk;
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const row = line.replace(/\r$/, "");
      if (!row.startsWith("data: ")) continue;
      try {
        const token = JSON.parse(row.slice(6)) as {
          stream_id?: string;
          seq?: number;
          delta?: string;
          done?: boolean;
          error?: string;
          payload?: TPayload;
        };
        if (token.stream_id) lastStreamId = token.stream_id;
        if (typeof token.seq === "number") lastSeq = token.seq;
        if (token.payload !== undefined) payload = token.payload;
        if (token.delta) text += token.delta;
        if (token.done) {
          if (token.error) {
            setState({
              status: "error",
              text,
              streamId: lastStreamId,
              lastSeq,
              error: token.error,
              finalPayload: null,
            });
            void qc.invalidateQueries({ queryKey: ["profile"] });
            void qc.invalidateQueries({ queryKey: ["credits"] });
            return { ok: false, error: token.error };
          }
          setState({
            status: "done",
            text,
            streamId: lastStreamId,
            lastSeq,
            error: null,
            finalPayload: payload,
          });
          void qc.invalidateQueries({ queryKey: chatKeys.session(sessionId) });
          void qc.invalidateQueries({ queryKey: chatKeys.sessions() });
          void qc.invalidateQueries({ queryKey: ["profile"] });
          void qc.invalidateQueries({ queryKey: ["credits"] });
          for (const key of options.invalidateKeys ?? []) {
            void qc.invalidateQueries({ queryKey: key });
          }
          if (payload !== null && options.onFinal) {
            options.onFinal(payload);
          }
          return { ok: true, finalPayload: payload };
        }
        if (token.error) {
          setState((s) => ({
            ...s,
            status: "error",
            error: token.error ?? "stream_failed",
          }));
          void qc.invalidateQueries({ queryKey: ["profile"] });
          return { ok: false, error: token.error ?? "stream_failed" };
        }
        setState((s) => ({ ...s, text, streamId: lastStreamId, lastSeq }));
      } catch {
        /* skip malformed */
      }
    }
  }
  setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
  return { ok: false, error: "stream_failed" };
}
