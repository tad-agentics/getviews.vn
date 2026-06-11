/**
 * Phase C.1.0 — answer-session SSE hook.
 *
 * Streams ``POST /answer/sessions/:id/turns`` (Cloud Run, §J ``ReportV1``).
 * Paid analysis uses ``answer_turn`` SSE only (Phase C — ``/stream`` removed).
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from "react";
import { useQueryClient, type QueryClient, type QueryKey } from "@tanstack/react-query";

import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { logUsage } from "@/lib/logUsage";
import {
  clearPendingAnswerStream,
  optimisticAnswerCreditsUsed,
  savePendingAnswerStream,
  type PendingAnswerTurnKind,
} from "@/lib/sseResume";
import { STEP_EVENT_TYPES, type StepEvent } from "@/lib/types/sse-events";
import type {
  BrightSpotSignal,
  ChannelContext,
  FormatCard,
  NarrativeVi,
  ReferenceVideoCard,
  VideoAnswerNarrativeReadyPayload,
  VideoAnswerPreSynthesisPayload,
  VideoFlopIssue,
  ViewScenario,
} from "@/lib/api-types";

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

/**
 * TD-4 — a single auto-retry covers the common network-blip case where the
 * client received the `seq=1` payload token but lost the connection before
 * the `seq=2` done marker arrived. On retry we pass `resume_stream_id` +
 * `resume_from_seq` so the server replays from its 60s chunk buffer and
 * does **not** re-run Gemini / re-bill credits (see `cloud-run/main.py`).
 * Higher retry counts would risk unbounded cost if the cache missed and
 * the server fell through to a fresh run.
 */
const MAX_ANSWER_RETRIES = 1;

/**
 * Idle-timeout for the SSE reader loop. If no bytes arrive for this long
 * the stream is considered hung and we surface ``stream_timeout``. The
 * retry loop will then re-attempt with resume params, letting Cloud Run's
 * 60s replay buffer recover in-flight work without re-billing. Rolling
 * timer — every chunk resets it, so long but healthy streams don't trip.
 */
const SSE_IDLE_TIMEOUT_MS = 45_000;

/** Stable key so TD-4 replay does not duplicate legacy step lines in the UI. */
export function stepEventDedupeKey(event: StepEvent): string {
  switch (event.type) {
    case "step_start":
    case "step_process":
      return `${event.type}:${event.label}`;
    case "step_search":
      return `${event.type}:${event.source}:${event.query}`;
    case "step_creator":
      return `${event.type}:${event.handle}`;
    case "step_count":
      return `${event.type}:${event.count}`;
    case "step_done":
      return `${event.type}:${event.summary}`;
    case "step_error":
      return `${event.type}:${event.code}:${event.message_vi}`;
    case "step_status":
      return `${event.type}:${event.iteration}:${event.text}`;
    case "step_tool_start":
      return `${event.type}:${event.iteration}:${event.index}:${event.tool}:${event.label}`;
    case "step_tool_complete":
      return `${event.type}:${event.iteration}:${event.index}:${event.tool}`;
    default:
      return JSON.stringify(event);
  }
}

function appendStepDeduped(steps: StepEvent[], event: StepEvent): StepEvent[] {
  const key = stepEventDedupeKey(event);
  if (steps.some((s) => stepEventDedupeKey(s) === key)) return steps;
  return [...steps, event];
}

export type StreamStatus = "idle" | "streaming" | "done" | "error";

export interface StreamState<TPayload = unknown> {
  status: StreamStatus;
  text: string;
  streamId: string | null;
  lastSeq: number;
  error: string | null;
  finalPayload: TPayload | null;
  steps: StepEvent[];
  /** Number of backend heartbeat pings received. Multiply × 10 to get elapsed seconds. */
  heartbeatCount: number;
  /** Video answer SSE: shells + KPI hints before synthesis (merged across tokens). */
  preSynthesisData: VideoAnswerPreSynthesisPayload | null;
  channelContext: ChannelContext | null;
  narrativeReady: VideoAnswerNarrativeReadyPayload | null;
}

export interface StreamOptions<TPayload = unknown> {
  onFinal?: (payload: TPayload) => void;
  invalidateKeys?: QueryKey[];
}

export type AnswerTurnKind = "primary" | "timing" | "creators" | "script" | "generic";

export type StreamArgs = {
  mode: "answer_turn";
  answerSessionId: string;
  query: string;
  turnKind: AnswerTurnKind;
  /** Session row ``format`` — primary script turns bill 3 credits. */
  sessionFormat?: string | null;
  videoMode?: "win" | "flop" | null;
  analysisDepth?: "basic" | "deep" | null;
  sourceEntry?: string | null;
  /** Explicit intent from CTA pill — skip free-text classify (§4.10.2). */
  intentType?: string | null;
  ctaId?: string | null;
  resumeStreamId?: string;
  lastSeq?: number;
  /**
   * Unix ms timestamp of the original stream — preserved across
   * reloads so the sessionStorage entry keeps its age relative to
   * Cloud Run's 60s replay-buffer TTL
   * (``cloud-run/getviews_pipeline/session_store.py:_STREAM_REPLAY_TTL_SEC``).
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
  /** Fresh ``invalidateKeys`` / ``onFinal`` without forcing ``stream`` to change identity every render. */
  const streamOptsRef = useRef(options);
  streamOptsRef.current = options;
  const abortRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<StreamState<TPayload>>({
    status: "idle",
    text: "",
    streamId: null,
    lastSeq: 0,
    error: null,
    finalPayload: null,
    steps: [],
    heartbeatCount: 0,
    preSynthesisData: null,
    channelContext: null,
    narrativeReady: null,
  });

  // Abort the in-flight SSE on unmount so navigating away mid-stream
  // doesn't leak the fetch until SSE_IDLE_TIMEOUT_MS and doesn't set
  // state on an unmounted component. Credits (TD-1) are already
  // deducted at request time — this only frees client + connection.
  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  const stream = useCallback(
    async (args: StreamArgs): Promise<StreamResult<TPayload>> => {
      abortRef.current?.abort();
      const abort = new AbortController();
      abortRef.current = abort;

      const preservePipeline =
        Boolean(args.resumeStreamId) && (args.lastSeq ?? 0) > 0;
      setState((prev) => ({
        status: "streaming",
        text: preservePipeline ? prev.text : "",
        streamId: args.resumeStreamId ?? null,
        lastSeq: args.lastSeq ?? 0,
        error: null,
        finalPayload: null,
        steps: preservePipeline ? prev.steps : [],
        heartbeatCount: preservePipeline ? prev.heartbeatCount : 0,
        preSynthesisData: preservePipeline ? prev.preSynthesisData : null,
        channelContext: preservePipeline ? prev.channelContext : null,
        narrativeReady: preservePipeline ? prev.narrativeReady : null,
      }));

      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) throw new Error("No session");

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
              sessionFormat: args.sessionFormat ?? null,
              analysisDepth: args.analysisDepth ?? null,
              videoMode: args.videoMode ?? null,
              creditsUsed: optimisticAnswerCreditsUsed(
                args.turnKind as PendingAnswerTurnKind,
                args.sessionFormat,
                args.analysisDepth,
              ),
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
              body: JSON.stringify({
                query: args.query,
                kind: args.turnKind,
                ...(args.videoMode ? { video_mode: args.videoMode } : {}),
                ...(args.analysisDepth ? { analysis_depth: args.analysisDepth } : {}),
                ...(args.sourceEntry ? { source_entry: args.sourceEntry } : {}),
                ...(args.intentType ? { intent_type: args.intentType } : {}),
                ...(args.ctaId ? { cta_id: args.ctaId } : {}),
              }),
              signal: abort.signal,
            });

            if (res.status === 402) {
              // Semantic error — no retry will help; clear pending so
              // a reload doesn't loop. Refetch profile/credits: a 402
              // means our cached balance was stale-high — show the
              // user the real number immediately.
              clearPendingAnswerStream();
              void qc.invalidateQueries({ queryKey: ["profile"] });
              void qc.invalidateQueries({ queryKey: ["credits"] });
              setState((s) => ({ ...s, status: "error", error: "insufficient_credits" }));
              return { ok: false, error: "insufficient_credits" };
            }
            if (res.status === 409) {
              // TD-3 atomic lock held by another in-flight request from
              // this same user. Don't retry — the user must wait for
              // the previous request to finish or fail.
              clearPendingAnswerStream();
              setState((s) => ({ ...s, status: "error", error: "already_processing" }));
              return { ok: false, error: "already_processing" };
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
              streamOptsRef,
              args.answerSessionId,
              carriedPayload,
              persistProgress,
            );
            carriedPayload = outcome.payload;
            // Keep stream_id + seq tied together. A cross-pod reconnect
            // returns a fresh stream_id from seq=0; if we kept the old
            // seq, a 2nd retry would ask the new pod's buffer for an
            // offset it never produced — replay misses, Gemini re-runs.
            // When the id changes, reset to whatever the new stream is
            // at; when it stays the same, advance the high-water mark
            // monotonically.
            if (outcome.streamId && outcome.streamId !== resumeStreamId) {
              resumeStreamId = outcome.streamId;
              resumeSeq = outcome.lastSeq;
            } else {
              if (outcome.streamId) resumeStreamId = outcome.streamId;
              if (outcome.lastSeq > resumeSeq) resumeSeq = outcome.lastSeq;
            }

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
              // Keep pending when we had replay handles so AnswerScreen can
              // offer "Tiếp tục phân tích" / tab reload within the 60s buffer.
              const hadReplayProgress =
                Boolean(resumeStreamId) && resumeSeq > 0;
              if (!hadReplayProgress) {
                clearPendingAnswerStream();
              }
              return { ok: false, error: outcome.error ?? "stream_failed" };
            }
            // Loop to next attempt with resume params set.
          }

          if (!(resumeStreamId && resumeSeq > 0)) {
            clearPendingAnswerStream();
          }
          return { ok: false, error: "stream_failed" };
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") {
          return { ok: false, error: "aborted" };
        }
        setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
        return { ok: false, error: "stream_failed" };
      }
    },
    [qc],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({
      ...s,
      status: "idle",
      steps: [],
      heartbeatCount: 0,
      preSynthesisData: null,
      channelContext: null,
      narrativeReady: null,
    }));
  }, []);

  const reset = useCallback(() => {
    setState({
      status: "idle",
      text: "",
      streamId: null,
      lastSeq: 0,
      error: null,
      finalPayload: null,
      steps: [],
      heartbeatCount: 0,
      preSynthesisData: null,
      channelContext: null,
      narrativeReady: null,
    });
  }, []);

  const heartbeatElapsedSec = state.heartbeatCount * 10;

  return { ...state, heartbeatElapsedSec, stream, abort, reset };
}

type SetState<T> = Dispatch<SetStateAction<StreamState<T>>>;

function mergePreSynthesis(
  prev: VideoAnswerPreSynthesisPayload | null,
  token: Record<string, unknown>,
): VideoAnswerPreSynthesisPayload {
  const next: VideoAnswerPreSynthesisPayload = { ...(prev ?? {}) };
  // ``token.kpi`` was historically merged here but no FE surface ever read
  // ``preSynth.kpi`` — VideoBody reads ``report.kpis`` directly. Dropped to
  // avoid pretending the field is live.
  if (token.bright_spot_signal != null && typeof token.bright_spot_signal === "object") {
    next.bright_spot_signal = token.bright_spot_signal as BrightSpotSignal;
  }
  if (typeof token.performance_tier === "string") next.performance_tier = token.performance_tier;
  if (Array.isArray(token.reference_videos)) {
    next.reference_videos = token.reference_videos as ReferenceVideoCard[];
  }
  return next;
}

function channelContextFromToken(token: Record<string, unknown>): ChannelContext | null {
  const raw = token.channel_context;
  if (raw && typeof raw === "object" && raw !== null && "available" in raw) {
    return raw as ChannelContext;
  }
  const omit = new Set([
    "type",
    "stream_id",
    "seq",
    "delta",
    "done",
    "error",
    "payload",
    "heartbeat",
  ]);
  const entries = Object.entries(token).filter(([k]) => !omit.has(k));
  if (entries.length === 0) return null;
  return Object.fromEntries(entries) as unknown as ChannelContext;
}

function mergeNarrativeReady(
  prev: VideoAnswerNarrativeReadyPayload | null,
  token: Record<string, unknown>,
): VideoAnswerNarrativeReadyPayload {
  const narrative_vi =
    (token.narrative_vi as NarrativeVi | undefined) ?? prev?.narrative_vi;
  const format_cards =
    (token.format_cards as FormatCard[] | undefined) ?? prev?.format_cards;
  const tokErrs = token.errors;
  let errors = prev?.errors;
  if (Array.isArray(tokErrs) && tokErrs.length > 0) {
    errors = tokErrs as VideoFlopIssue[];
  }
  const tokBs = token.bright_spot_signal;
  let bright_spot_signal = prev?.bright_spot_signal;
  if (
    tokBs != null &&
    typeof tokBs === "object" &&
    !Array.isArray(tokBs) &&
    typeof (tokBs as BrightSpotSignal).message_vi === "string"
  ) {
    bright_spot_signal = tokBs as BrightSpotSignal;
  }
  const tokVs = token.view_scenarios;
  let view_scenarios = prev?.view_scenarios;
  if (Array.isArray(tokVs) && tokVs.length > 0) {
    view_scenarios = tokVs as ViewScenario[];
  }
  return {
    narrative_vi,
    format_cards,
    errors,
    bright_spot_signal,
    view_scenarios,
  };
}

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
  streamOptsRef: MutableRefObject<StreamOptions<TPayload>>,
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
    if (done) {
      // Flush any bytes held back by the streaming decoder (a multi-byte
      // UTF-8 Vietnamese char split across the final chunk boundary would
      // otherwise be dropped).
      buffer += decoder.decode();
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const row = line.replace(/\r$/, "");
      if (!row.startsWith("data: ")) continue;
      try {
        const token = JSON.parse(row.slice(6)) as {
          type?: string;
          stream_id?: string;
          seq?: number;
          delta?: string;
          done?: boolean;
          error?: string;
          payload?: TPayload;
          heartbeat?: boolean;
        };
        if (token.type !== undefined && STEP_EVENT_TYPES.has(token.type)) {
          setState((s) => ({
            ...s,
            steps: appendStepDeduped(s.steps, token as StepEvent),
          }));
          continue;
        }
        if (token.type === "pre_synthesis") {
          setState((s) => ({
            ...s,
            preSynthesisData: mergePreSynthesis(
              s.preSynthesisData,
              token as Record<string, unknown>,
            ),
          }));
        } else if (token.type === "channel_context") {
          const ctx = channelContextFromToken(token as Record<string, unknown>);
          if (ctx) {
            setState((s) => ({ ...s, channelContext: ctx }));
          }
        } else if (token.type === "narrative_ready") {
          setState((s) => ({
            ...s,
            narrativeReady: mergeNarrativeReady(
              s.narrativeReady,
              token as Record<string, unknown>,
            ),
          }));
        }
        // Backend heartbeat ping — emitted every 10s to keep SSE alive.
        // Increment counter so the UI can show "Vẫn đang xử lý · Ns…".
        if (token.heartbeat === true) {
          setState((s) => ({ ...s, heartbeatCount: s.heartbeatCount + 1 }));
        }
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
            setState((s) => ({
              ...s,
              status: "error",
              text,
              streamId: lastStreamId,
              lastSeq,
              error: token.error ?? null,
              finalPayload: null,
            }));
            void qc.invalidateQueries({ queryKey: ["profile"] });
            void qc.invalidateQueries({ queryKey: ["credits"] });
            return { ok: false, error: token.error, streamId: lastStreamId, lastSeq, payload };
          }
          setState((s) => ({
            ...s,
            status: "done",
            text,
            streamId: lastStreamId,
            lastSeq,
            error: null,
            finalPayload: payload,
          }));
          void qc.invalidateQueries({ queryKey: ["profile"] });
          void qc.invalidateQueries({ queryKey: ["credits"] });
          const streamOpts = streamOptsRef.current;
          for (const key of streamOpts.invalidateKeys ?? []) {
            void qc.invalidateQueries({ queryKey: key });
          }
          if (payload !== null && streamOpts.onFinal) {
            streamOpts.onFinal(payload);
          }
          return { ok: true, streamId: lastStreamId, lastSeq, payload };
        }
        if (token.error) {
          setState((s) => ({
            ...s,
            status: "error",
            error: token.error ?? "stream_failed",
          }));
          // Server refunds the charge on failed builds (2026-06-10) —
          // refetch BOTH so the restored balance shows immediately.
          void qc.invalidateQueries({ queryKey: ["profile"] });
          void qc.invalidateQueries({ queryKey: ["credits"] });
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
