/**
 * Phase C.1.0 — shared session-stream hook.
 *
 * Consolidates SSE + credit + resume semantics used by both the retired
 * chat surface and the new `/answer` report surface. One hook, two shapes
 * of data it can yield:
 *
 * - **Text stream** (chat bubbles + Vercel `/api/chat` follow-ups): tokens
 *   carry `delta: string`; accumulated into `state.text` for incremental
 *   rendering.
 * - **Report payload** (`/answer/sessions/:id/turns` — wired by C.2+): the
 *   final token before `done:true` carries `payload: unknown` with the full
 *   §J `ReportV1` shape. Surfaced via `state.finalPayload` and delivered to
 *   the optional `onFinal(payload)` callback.
 *
 * Both shapes share `stream_id` + `seq` for TD-4 replay, the 402/429
 * credit-gate contract, and the abort / reset affordances.
 *
 * Lifted (unchanged protocol) from the former `useChatStream` — callers
 * that only care about text keep working by reading `state.text`.
 */

import { useCallback, useRef, useState } from "react";
import { useQueryClient, type QueryKey } from "@tanstack/react-query";

import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { chatKeys } from "./useChatSession";
import { type StepEvent } from "@/lib/types/sse-events";

const CLOUD_RUN_URL = env.VITE_CLOUD_RUN_API_URL;
const VERCEL_CHAT_URL = "/api/chat";

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
  /** Step events received from Cloud Run pipeline (P0-6). Empty for Vercel-routed intents. */
  stepEvents: StepEvent[];
  /** Final structured payload (e.g. `ReportV1`) when the stream carries one. Null for text-only streams. */
  finalPayload: TPayload | null;
}

export interface StreamOptions<TPayload = unknown> {
  /** Called once with the parsed `payload` from the last token before `done: true`. */
  onFinal?: (payload: TPayload) => void;
  /** Extra query keys to invalidate on successful `done`. Added to the default chat-session + profile + credits set. */
  invalidateKeys?: QueryKey[];
}

export interface StreamArgs {
  sessionId: string;
  query: string;
  intentType: string;
  resumeStreamId?: string;
  lastSeq?: number;
  nicheLabel?: string;
}

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
    async ({
      sessionId,
      query,
      intentType,
      resumeStreamId,
      lastSeq: resumeSeq,
      nicheLabel,
    }: StreamArgs) => {
      abortRef.current?.abort();
      const abort = new AbortController();
      abortRef.current = abort;

      setState({
        status: "streaming",
        text: "",
        streamId: resumeStreamId ?? null,
        lastSeq: resumeSeq ?? 0,
        error: null,
        stepEvents: [],
        finalPayload: null,
      });

      try {
        // getSession() returns the current session; Cloud Run now validates via JWKS
        // (ES256) so expired token detection is handled server-side with 30s leeway.
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) throw new Error("No session");

        const useCloudRun = CLOUD_RUN_INTENTS.has(intentType);
        if (useCloudRun && !CLOUD_RUN_URL) {
          console.warn(`[useSessionStream] Cloud Run URL not set — routing ${intentType} to Vercel fallback`);
        }
        const endpoint = useCloudRun && CLOUD_RUN_URL ? `${CLOUD_RUN_URL}/stream` : VERCEL_CHAT_URL;

        const res = await fetch(endpoint, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionId,
            query,
            intent_type: intentType,
            stream_id: resumeStreamId,
            last_seq: resumeSeq,
            niche_label: nicheLabel,
          }),
          signal: abort.signal,
        });

        if (res.status === 402) {
          setState((s) => ({ ...s, status: "error", error: "insufficient_credits" }));
          return;
        }
        if (res.status === 429) {
          setState((s) => ({ ...s, status: "error", error: "daily_free_limit" }));
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (!res.body) throw new Error("Response body is null");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let text = "";
        let lastStreamId: string | null = resumeStreamId ?? null;
        let lastSeq = resumeSeq ?? 0;
        let payload: TPayload | null = null;
        // Buffer incomplete SSE lines across chunk boundaries.
        // reader.read() returns arbitrary byte chunks — a single "data: {...}\n"
        // event can be split across two reads. Without a buffer the partial tail
        // is silently dropped, causing the stream to appear cut off.
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last (potentially incomplete) fragment in the buffer.
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const token = JSON.parse(line.slice(6)) as {
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
              // Step event — append to stepEvents, no text change
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
                  // On error: only refresh profile/credits (is_processing cleared server-side).
                  // Do NOT invalidate the session query — no assistant row was written,
                  // and a DB refetch would update lastMessageIsAssistant, hiding the error block.
                  void qc.invalidateQueries({ queryKey: ["profile"] });
                  void qc.invalidateQueries({ queryKey: ["credits"] });
                } else {
                  setState({
                    status: "done",
                    text,
                    streamId: lastStreamId,
                    lastSeq,
                    error: null,
                    stepEvents: [],
                    finalPayload: payload,
                  });
                  // On success: refresh chat session (legacy) + profile/credits + any extras.
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
                }
                return;
              }
              // Mid-stream error without done flag (shouldn't happen, but handle gracefully)
              if (token.error) {
                setState((s) => ({ ...s, status: "error", error: token.error ?? "stream_failed", stepEvents: [] }));
                void qc.invalidateQueries({ queryKey: ["profile"] });
                return;
              }
              setState((s) => ({ ...s, text, streamId: lastStreamId, lastSeq }));
            } catch {
              /* skip malformed */
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === "AbortError") return;
        setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
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
