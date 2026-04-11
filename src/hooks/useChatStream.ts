import { useState, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { env } from "@/lib/env";
import { chatKeys } from "./useChatSession";
import { type StepEvent } from "@/lib/types/sse-events";

const CLOUD_RUN_URL = env.VITE_CLOUD_RUN_API_URL;
const VERCEL_CHAT_URL = "/api/chat";

const CLOUD_RUN_INTENTS = new Set([
  "video_diagnosis",
  "competitor_profile",
  "own_channel",
  "content_directions",
  "brief_generation",
  "trend_spike",
  "find_creators",
  "shot_list",
]);

export type StreamStatus = "idle" | "streaming" | "done" | "error";

export interface StreamState {
  status: StreamStatus;
  text: string;
  streamId: string | null;
  lastSeq: number;
  error: string | null;
  /** Step events received from Cloud Run pipeline (P0-6). Empty for Vercel-routed intents. */
  stepEvents: StepEvent[];
}

export function useChatStream() {
  const qc = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<StreamState>({
    status: "idle",
    text: "",
    streamId: null,
    lastSeq: 0,
    error: null,
    stepEvents: [],
  });

  const stream = useCallback(
    async ({
      sessionId,
      query,
      intentType,
      resumeStreamId,
      lastSeq: resumeSeq,
    }: {
      sessionId: string;
      query: string;
      intentType: string;
      resumeStreamId?: string;
      lastSeq?: number;
    }) => {
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
      });

      try {
        // getSession() returns cached token — refresh if within 60s of expiry to avoid
        // sending an expired JWT to Cloud Run (which returns 401).
        let { data: { session } } = await supabase.auth.getSession();
        if (!session) throw new Error("No session");
        const expiresAt = session.expires_at ?? 0; // unix seconds
        const nowSec = Math.floor(Date.now() / 1000);
        if (expiresAt - nowSec < 60) {
          const refreshed = await supabase.auth.refreshSession();
          session = refreshed.data.session;
          if (!session) {
            setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
            return;
          }
        }

        const useCloudRun = CLOUD_RUN_INTENTS.has(intentType);
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
          }),
          signal: abort.signal,
        });

        if (res.status === 402) {
          setState((s) => ({ ...s, status: "error", error: "insufficient_credits" }));
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (!res.body) throw new Error("Response body is null");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let text = "";
        let lastStreamId: string | null = resumeStreamId ?? null;
        let lastSeq = resumeSeq ?? 0;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const lines = decoder.decode(value).split("\n");
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
              };
              if (token.error) {
                setState((s) => ({ ...s, status: "error", error: token.error ?? "stream_failed" }));
                return;
              }
              if (token.stream_id) lastStreamId = token.stream_id;
              if (typeof token.seq === "number") lastSeq = token.seq;
              // Step event — append to stepEvents, no text change
              if (token.step) {
                setState((s) => ({ ...s, streamId: lastStreamId, lastSeq, stepEvents: [...s.stepEvents, token.step!] }));
                continue;
              }
              if (token.delta) text += token.delta;
              if (token.done) {
                setState({
                  status: "done",
                  text,
                  streamId: lastStreamId,
                  lastSeq,
                  error: null,
                  stepEvents: [],
                });
                void qc.invalidateQueries({ queryKey: chatKeys.messages(sessionId) });
                void qc.invalidateQueries({ queryKey: ["profile"] });
                void qc.invalidateQueries({ queryKey: ["credits"] });
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
    [qc],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, status: "idle" }));
  }, []);

  const reset = useCallback(() => {
    setState({ status: "idle", text: "", streamId: null, lastSeq: 0, error: null, stepEvents: [] });
  }, []);

  return { ...state, stream, abort, reset };
}
