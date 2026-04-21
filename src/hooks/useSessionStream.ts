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
import { chatKeys } from "./useChatSession";
import { type StepEvent } from "@/lib/types/sse-events";

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

const CLOUD_RUN_INTENTS = new Set([
  "video_diagnosis",
  "competitor_profile",
  "own_channel",
  "content_directions",
  "trend_spike",
  "creator_search",
  "shot_list",
]);

export type StreamStatus = "idle" | "streaming" | "done" | "error";

export interface StreamState<TPayload = unknown> {
  status: StreamStatus;
  text: string;
  streamId: string | null;
  lastSeq: number;
  error: string | null;
  stepEvents: StepEvent[];
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
    stepEvents: [],
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
        stepEvents: [],
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

          for (let attempt = 0; attempt <= MAX_ANSWER_RETRIES; attempt++) {
            const url = new URL(
              `${CLOUD_RUN_URL}/answer/sessions/${args.answerSessionId}/turns`,
            );
            if (resumeStreamId && resumeSeq > 0) {
              url.searchParams.set("resume_stream_id", resumeStreamId);
              url.searchParams.set("resume_from_seq", String(resumeSeq));
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

            const outcome: AnswerSseOutcome<TPayload> = await consumeAnswerSse(
              res,
              setState,
              qc,
              options,
              args.answerSessionId,
              carriedPayload,
            );
            carriedPayload = outcome.payload;
            if (outcome.streamId) resumeStreamId = outcome.streamId;
            if (outcome.lastSeq > resumeSeq) resumeSeq = outcome.lastSeq;

            if (outcome.ok) {
              return { ok: true, finalPayload: outcome.payload };
            }
            // Only `stream_failed` is retryable — semantic errors (e.g.
            // `insufficient_credits` from the server's in-band error token)
            // must surface on the first attempt.
            const retryable =
              outcome.error === "stream_failed" &&
              Boolean(resumeStreamId) &&
              attempt < MAX_ANSWER_RETRIES;
            if (!retryable) {
              return { ok: false, error: outcome.error ?? "stream_failed" };
            }
            // Loop to next attempt with resume params set.
          }

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
      stepEvents: [],
      finalPayload: null,
    });
  }, []);

  return { ...state, stream, abort, reset };
}

type SetState<T> = Dispatch<SetStateAction<StreamState<T>>>;

async function consumeAnswerSse<TPayload>(
  res: Response,
  setState: SetState<TPayload>,
  qc: QueryClient,
  options: StreamOptions<TPayload>,
  _answerSessionId: string,
  carriedPayload: TPayload | null = null,
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
    const { done, value } = await reader.read();
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
              stepEvents: [],
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
            stepEvents: [],
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
            stepEvents: [],
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
    const { done, value } = await reader.read();
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
          step?: StepEvent;
          payload?: TPayload;
        };
        if (token.stream_id) lastStreamId = token.stream_id;
        if (typeof token.seq === "number") lastSeq = token.seq;
        if (token.step) {
          setState((s) => ({
            ...s,
            streamId: lastStreamId,
            lastSeq,
            stepEvents: [...s.stepEvents, token.step!],
          }));
          continue;
        }
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
              stepEvents: [],
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
            stepEvents: [],
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
            stepEvents: [],
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
