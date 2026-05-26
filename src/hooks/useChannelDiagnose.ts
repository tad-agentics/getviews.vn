/**
 * useChannelDiagnose — imperative SSE hook for POST /channel/diagnose.
 *
 * Opens a single SSE stream to Cloud Run `/channel/diagnose`, parses events into
 * structured state, and exposes `start(handle, nicheId, videoUrl?, options?)`.
 * SSE reconnect uses TD-4: stream_id + seq, one retry, 45s idle timeout.
 *
 * Event types from the server:
 *   trajectory         { trajectory: TrajectoryShape }
 *   score_card         { data: ChannelScoreCardData, captions?: Record<string, string> }
 *   channel_findings   { findings: ChannelDiagnosisFinding[] }
 *   step_start         { index, label }
 *   step_done          { index, count? }
 *   section_start      { section_id, title, embedded_tiles?, embedded_creators? }
 *   text_chunk         { content }
 *   section_done       { section_id }
 *   recommendation_item { index, title, body }
 *   cache_hit          (no extra fields)
 *   heartbeat          (every 10s keep-alive)
 *   payload            { payload: ChannelDiagnosisPayload }  // terminal before done
 *   done: true         terminal frame (with optional error)
 *
 * Query params on start: `force_refresh=1` bypasses 7-day cache (fresh run, 3 credits).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import type {
  ChannelDiagnosisFinding,
  ChannelDiagnosisPayload,
  ChannelHashtagInsight,
  ChannelNextVideoConcept,
  ChannelPerformerTile,
  ChannelPersona,
  ChannelRecommendation,
  ChannelScoreCard,
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
  /** Template + captions merged once `score_card` SSE arrives. */
  scoreCard: ChannelScoreCard | null;
  /** V5 §2 findings tile — from `channel_findings` SSE or terminal payload. */
  channelFindings: ChannelDiagnosisFinding[];
  channelPersona: ChannelPersona | null;
  peerSource: ChannelDiagnosisPayload["peer_source"];
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
  /** Section currently being filled by text_chunk events. ``null`` between
   * sections (after section_done, before the next section_start). Lets
   * the SectionRenderer scope the streaming cursor to the active row
   * instead of every row visible. */
  activeSectionId: string | null;
}

const INITIAL_STATE: ChannelDiagnoseState = {
  status: "idle",
  trajectoryShape: null,
  sections: [],
  recommendations: [],
  scoreCard: null,
  channelFindings: [],
  channelPersona: null,
  peerSource: null,
  finalPayload: null,
  error: null,
  heartbeatCount: 0,
  streamId: null,
  lastSeq: 0,
  activeStepIndex: -1,
  activeStepLabel: "",
  activeSectionId: null,
};

function mergeScoreCardFromPayload(p: ChannelDiagnosisPayload): ChannelScoreCard | null {
  const data = p.score_card;
  if (!data || typeof data !== "object") return null;
  const cap = p.score_card_captions;
  return {
    ...data,
    ...(cap && typeof cap === "object" ? { captions: cap } : {}),
  };
}

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
   * @param options.forceRefresh Bypass 7-day cache (charges 3 credits on fresh run).
   */
  const start = useCallback(
    async (
      handle: string,
      nicheId: number,
      videoUrl?: string,
      options?: { forceRefresh?: boolean },
    ) => {
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
        if (options?.forceRefresh) url.searchParams.set("force_refresh", "1");
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
      // Clearing activeSectionId tells SectionRenderer the cursor
      // should no longer render on this section. The next
      // section_start re-sets it before any text_chunk arrives.
      activeSectionId:
        s.activeSectionId === section.section_id ? null : s.activeSectionId,
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

      if (eventType === "score_card") {
        const data = token.data as ChannelScoreCard | undefined;
        const captions = token.captions as Record<string, string> | undefined;
        if (data && typeof data === "object") {
          setState((s) => ({
            ...s,
            scoreCard: { ...data, ...(captions ? { captions } : {}) },
          }));
        }
        continue;
      }

      if (eventType === "channel_findings") {
        const rows = token.findings;
        if (Array.isArray(rows)) {
          setState((s) => ({
            ...s,
            channelFindings: rows as ChannelDiagnosisFinding[],
          }));
        }
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
        if (Array.isArray(token.hashtag_insights)) {
          newSection.hashtag_insights = token.hashtag_insights as ChannelHashtagInsight[];
        }
        if (token.next_video && typeof token.next_video === "object") {
          newSection.next_video = token.next_video as ChannelNextVideoConcept;
        }
        activeSection = newSection;
        // Eagerly add stub to state so UI can show the header immediately.
        // Also mark this section as the active streaming target so the
        // SectionRenderer cursor scopes to it instead of every section.
        setState((s) => ({
          ...s,
          sections: [
            ...s.sections.filter((sec) => sec.section_id !== newSection.section_id),
            { ...newSection },
          ],
          activeSectionId: newSection.section_id,
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
        const kindRaw = token.kind as string | undefined;
        const kind: ChannelRecommendation["kind"] =
          kindRaw === "hero" || kindRaw === "regular" || kindRaw === "anti"
            ? kindRaw
            : undefined;
        const rec: ChannelRecommendation = {
          index: token.index as number,
          title: (token.title as string) ?? "",
          body: (token.body as string) ?? "",
          ...(kind ? { kind } : {}),
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
      if (token.payload !== undefined && token.payload !== null) {
        const pl = token.payload as ChannelDiagnosisPayload;
        payload = pl;
        setState((s) => ({
          ...s,
          finalPayload: pl,
          scoreCard: s.scoreCard ?? mergeScoreCardFromPayload(pl),
          channelFindings:
            pl.channel_findings && pl.channel_findings.length > 0
              ? pl.channel_findings
              : s.channelFindings,
          channelPersona: pl.channel_persona ?? s.channelPersona,
          peerSource: pl.peer_source ?? s.peerSource,
        }));
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
        setState((s) => {
          const fp = payload ?? s.finalPayload;
          return {
            ...s,
            status: "done",
            finalPayload: fp,
            scoreCard: s.scoreCard ?? (fp ? mergeScoreCardFromPayload(fp) : null),
            channelFindings:
              fp?.channel_findings && fp.channel_findings.length > 0
                ? fp.channel_findings
                : s.channelFindings,
            channelPersona: fp?.channel_persona ?? s.channelPersona,
            peerSource: fp?.peer_source ?? s.peerSource,
            error: null,
          };
        });
        return { ok: true, streamId: lastStreamId, lastSeq, payload };
      }
    }
  }

  // Unexpected EOF
  setState((s) => ({ ...s, status: "error", error: "stream_failed" }));
  return { ok: false, error: "stream_failed", streamId: lastStreamId, lastSeq, payload };
}
