/**
 * useChannelDiagnose — imperative SSE hook for POST /channel/diagnose.
 *
 * This is a custom hook (NOT useQuery). It opens a single SSE stream to the
 * Cloud Run `/channel/diagnose` endpoint, parses section-tagged events into
 * structured state, and exposes an imperative `start(handle, nicheId, videoUrl?)`
 * API. SSE reconnect uses TD-4: stream_id + seq, one retry, 45s idle timeout.
 *
 * Event types from the server:
 *   trajectory      { trajectory: TrajectoryShape }
 *   step_start      { index, label }
 *   step_done       { index, count? }
 *   section_start   { section_id, title, embedded_tiles?, embedded_creators? }
 *   text_chunk      { content }
 *   section_done    { section_id }
 *   recommendation_item { index, title, body }
 *   cache_hit       (no extra fields)
 *   heartbeat       (every 10s keep-alive)
 *   payload         { payload: ChannelDiagnosisPayload }  // terminal before done
 *   done: true      terminal frame (with optional error)
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import type {
  ChannelDiagnosisPayload,
  ChannelPerformerTile,
  ChannelRecommendation,
  ChannelSection,
  ChannelUGCCreator,
  TrajectoryShape,
} from "@/lib/api-types";

const CLOUD_RUN_URL = env.VITE_CLOUD_RUN_API_URL;

/** TD-4 — one auto-retry on network drop; uses server-side 60s replay buffer. */
const MAX_DIAGNOSE_RETRIES = 1;

/** Rolling idle timeout — reset every chunk. */
const SSE_IDLE_TIMEOUT_MS = 45_000;

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

export type ChannelDiagnoseStatus = "idle" | "streaming" | "done" | "error";

export interface ChannelDiagnoseState {
  status: ChannelDiagnoseStatus;
  /** Resolved once the trajectory event arrives. */
  trajectoryShape: TrajectoryShape | null;
  /** Sections accumulated during streaming. Text grows as text_chunk events arrive. */
  sections: ChannelSection[];
  recommendations: ChannelRecommendation[];
  /** Final payload once `done: true` arrives (contains all sections + tiles). */
  finalPayload: ChannelDiagnosisPayload | null;
  error: string | null;
  /** Number of heartbeat pings (× 10 = approximate elapsed seconds). */
  heartbeatCount: number;
  streamId: string | null;
  lastSeq: number;
  /** Index of the currently active step (0-based), -1 when idle. */
  activeStepIndex: number;
  /** Label of the current step. */
  activeStepLabel: string;
}

const INITIAL_STATE: ChannelDiagnoseState = {
  status: "idle",
  trajectoryShape: null,
  sections: [],
  recommendations: [],
  finalPayload: null,
  error: null,
  heartbeatCount: 0,
  streamId: null,
  lastSeq: 0,
  activeStepIndex: -1,
  activeStepLabel: "",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function readWithIdleTimeout<T>(
  reader: ReadableStreamDefaultReader<T>,
  idleMs: number,
): Promise<ReadableStreamReadResult<T> | { timedOut: true }> {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const timeout = new Promise<{ timedOut: true }>((resolve) => {
    timer = setTimeout(() => resolve({ timedOut: true }), idleMs);
  });
  try {
    return await Promise.race([reader.read(), timeout]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useChannelDiagnose() {
  const qc = useQueryClient();
  const abortRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<ChannelDiagnoseState>(INITIAL_STATE);

  // Abort on unmount so navigating away doesn't leak the fetch.
  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  /**
   * Start a new channel diagnosis stream.
   * @param handle  TikTok handle (with or without @).
   * @param nicheId Creator niche ID for corpus benchmarks.
   * @param videoUrl Optional target video URL (§4 video_vs_channel).
   */
  const start = useCallback(
    async (handle: string, nicheId: number, videoUrl?: string) => {
      // Abort any previous stream
      abortRef.current?.abort();
      const abort = new AbortController();
      abortRef.current = abort;

      setState({
        ...INITIAL_STATE,
        status: "streaming",
      });

      if (!CLOUD_RUN_URL) {
        setState((s) => ({ ...s, status: "error", error: "no_cloud_run" }));
        return;
      }

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        setState((s) => ({ ...s, status: "error", error: "no_session" }));
        return;
      }

      let resumeStreamId: string | null = null;
      let resumeSeq = 0;
      let carriedPayload: ChannelDiagnosisPayload | null = null;

      for (let attempt = 0; attempt <= MAX_DIAGNOSE_RETRIES; attempt++) {
        const url = new URL(`${CLOUD_RUN_URL}/channel/diagnose`);
        url.searchParams.set("handle", handle);
        url.searchParams.set("niche_id", String(nicheId));
        if (videoUrl) url.searchParams.set("video_url", videoUrl);
        if (resumeStreamId && resumeSeq > 0) {
          url.searchParams.set("resume_stream_id", resumeStreamId);
          url.searchParams.set("resume_from_seq", String(resumeSeq));
        }

        let res: Response;
        try {
          res = await fetch(url.toString(), {
            method: "POST",
            headers: { Authorization: `Bearer ${session.access_token}` },
            signal: abort.signal,
          });
        } catch (err: unknown) {
          if (err instanceof Error && err.name === "AbortError") return;
          if (attempt < MAX_DIAGNOSE_RETRIES) continue;
          setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
          return;
        }

        if (!res.ok || !res.body) {
          if (attempt < MAX_DIAGNOSE_RETRIES) continue;
          setState((s) => ({
            ...s,
            status: "error",
            error: `http_${res.status}`,
          }));
          return;
        }

        const outcome = await consumeDiagnoseSse(
          res,
          setState,
          abort.signal,
          carriedPayload,
        );

        // Update resume pointers
        if (outcome.streamId && outcome.streamId !== resumeStreamId) {
          resumeStreamId = outcome.streamId;
          resumeSeq = outcome.lastSeq;
        } else {
          if (outcome.streamId) resumeStreamId = outcome.streamId;
          if (outcome.lastSeq > resumeSeq) resumeSeq = outcome.lastSeq;
        }
        if (outcome.payload) carriedPayload = outcome.payload;

        if (outcome.ok) {
          // Invalidate credits + profile so the credit chip refreshes.
          // TanStack invalidate uses prefix-match by default, so
          // ``["profile"]`` matches the keyed ``["profile", userId]``
          // query that useProfile.ts registers. Same for credits.
          void qc.invalidateQueries({ queryKey: ["profile"] });
          void qc.invalidateQueries({ queryKey: ["credits"] });
          // (No useQuery registers ``["channel-diagnose", handle]`` —
          // diagnose state is imperative SSE plumbing held in this hook.
          // The previous invalidation here was a no-op.)
          return;
        }

        if (outcome.error === "insufficient_credits"
          || outcome.error === "channel_not_found"
          || outcome.error === "already_in_flight") {
          // Non-retryable semantic errors.
          return;
        }

        // Transport error — loop to retry.
      }

      setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
    },
    [qc],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, status: "idle" }));
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  return { ...state, start, abort, reset };
}

// ---------------------------------------------------------------------------
// SSE consumer
// ---------------------------------------------------------------------------

type DiagnoseOutcome = {
  ok: boolean;
  error?: string;
  streamId: string | null;
  lastSeq: number;
  payload: ChannelDiagnosisPayload | null;
};

async function consumeDiagnoseSse(
  res: Response,
  setState: React.Dispatch<React.SetStateAction<ChannelDiagnoseState>>,
  signal: AbortSignal,
  carriedPayload: ChannelDiagnosisPayload | null,
): Promise<DiagnoseOutcome> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastStreamId: string | null = null;
  let lastSeq = 0;
  let payload = carriedPayload;

  /** Active section accumulator — null when between sections. */
  let activeSection: ChannelSection | null = null;

  const flushActiveSection = () => {
    if (!activeSection) return;
    const section = { ...activeSection };
    setState((s) => ({
      ...s,
      sections: [
        ...s.sections.filter((sec) => sec.section_id !== section.section_id),
        section,
      ],
    }));
    activeSection = null;
  };

  while (true) {
    if (signal.aborted) {
      try { await reader.cancel(); } catch { /* ignore */ }
      return { ok: false, error: "aborted", streamId: lastStreamId, lastSeq, payload };
    }

    const chunk = await readWithIdleTimeout(reader, SSE_IDLE_TIMEOUT_MS);
    if ("timedOut" in chunk) {
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
      let token: Record<string, unknown>;
      try {
        token = JSON.parse(row.slice(6)) as Record<string, unknown>;
      } catch {
        continue;
      }

      if (token.stream_id) lastStreamId = token.stream_id as string;
      if (typeof token.seq === "number") lastSeq = token.seq;

      const eventType = token.type as string | undefined;

      // --- Trajectory ---
      if (eventType === "trajectory") {
        setState((s) => ({
          ...s,
          trajectoryShape: token.trajectory as TrajectoryShape,
        }));
        continue;
      }

      // --- Steps ---
      if (eventType === "step_start") {
        setState((s) => ({
          ...s,
          activeStepIndex: (token.index as number) ?? s.activeStepIndex,
          activeStepLabel: (token.label as string) ?? s.activeStepLabel,
        }));
        continue;
      }
      if (eventType === "step_done") {
        // Step label stays visible until next step_start.
        continue;
      }

      // --- Section start ---
      if (eventType === "section_start") {
        flushActiveSection();
        const newSection: ChannelSection = {
          section_id: token.section_id as string,
          title: (token.title as string) ?? "",
          text: "",
        };
        if (Array.isArray(token.embedded_tiles) && token.embedded_tiles.length > 0) {
          newSection.embedded_tiles = token.embedded_tiles as ChannelPerformerTile[];
        }
        if (Array.isArray(token.embedded_creators) && token.embedded_creators.length > 0) {
          newSection.embedded_creators = token.embedded_creators as ChannelUGCCreator[];
        }
        activeSection = newSection;
        // Eagerly add stub to state so UI can show the header immediately.
        setState((s) => ({
          ...s,
          sections: [
            ...s.sections.filter((sec) => sec.section_id !== newSection.section_id),
            { ...newSection },
          ],
        }));
        continue;
      }

      // --- Text chunk ---
      if (eventType === "text_chunk") {
        const chunk_text = (token.content as string) ?? "";
        if (activeSection) {
          activeSection = { ...activeSection, text: activeSection.text + chunk_text };
          const snapshot = { ...activeSection };
          setState((s) => ({
            ...s,
            sections: s.sections.map((sec) =>
              sec.section_id === snapshot.section_id ? snapshot : sec,
            ),
          }));
        }
        continue;
      }

      // --- Recommendation item ---
      if (eventType === "recommendation_item") {
        const rec: ChannelRecommendation = {
          index: token.index as number,
          title: (token.title as string) ?? "",
          body: (token.body as string) ?? "",
        };
        setState((s) => ({
          ...s,
          recommendations: [
            ...s.recommendations.filter((r) => r.index !== rec.index),
            rec,
          ].sort((a, b) => a.index - b.index),
        }));
        continue;
      }

      // --- Section done ---
      if (eventType === "section_done") {
        flushActiveSection();
        continue;
      }

      // --- Heartbeat ---
      if (token.heartbeat === true) {
        setState((s) => ({ ...s, heartbeatCount: s.heartbeatCount + 1 }));
        continue;
      }

      // --- Final payload (before done) ---
      if (token.payload !== undefined) {
        payload = token.payload as ChannelDiagnosisPayload;
        setState((s) => ({ ...s, finalPayload: payload }));
        continue;
      }

      // --- Terminal done ---
      if (token.done === true) {
        flushActiveSection();
        if (token.error) {
          const err = token.error as string;
          setState((s) => ({ ...s, status: "error", error: err }));
          return { ok: false, error: err, streamId: lastStreamId, lastSeq, payload };
        }
        setState((s) => ({
          ...s,
          status: "done",
          finalPayload: payload ?? s.finalPayload,
          error: null,
        }));
        return { ok: true, streamId: lastStreamId, lastSeq, payload };
      }
    }
  }

  // Unexpected EOF
  setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
  return { ok: false, error: "stream_failed", streamId: lastStreamId, lastSeq, payload };
}
