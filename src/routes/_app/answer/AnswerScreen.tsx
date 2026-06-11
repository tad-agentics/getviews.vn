/**
 * Phase C.1 — /app/answer research shell (composed primitives + React Query).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { useAuth } from "@/hooks/useAuth";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import {
  answerSessionKeys,
  injectOptimisticTurn,
  lastPayloadFromTurns,
  useAnswerSessionDetail,
  type AnswerDetailCache,
} from "@/hooks/useAnswerSessionQueries";
import { useSessionStream } from "@/hooks/useSessionStream";
import { env } from "@/lib/env";
import { analysisErrorCopy, answerStreamErrorCopy } from "@/lib/errorMessages";
import { createAnswerSession } from "@/lib/answerApi";
import {
  clearPendingAnswerStream,
  hasAnswerStreamReplayHandles,
  loadPendingAnswerStream,
  optimisticAnswerCreditsUsed,
} from "@/lib/sseResume";
import {
  applyOptimisticAnswerTurn,
  buildResumeAnswerStreamArgs,
} from "@/routes/_app/answer/answerStreamTurn";
import { supabase } from "@/lib/supabase";
import type { AnswerSessionRow, AnswerTurnRow, ReportV1 } from "@/lib/api-types";
import { logUsage } from "@/lib/logUsage";
import {
  extractTikTokVideoIdFromText,
  nonTikTokUrlValidationMessage,
} from "@/lib/tiktokUrl";
import { Plus, Check, ArrowLeft } from "lucide-react";
import { ContinuationTurn } from "@/components/v2/answer/ContinuationTurn";
import { ScriptShootPanel } from "@/components/v2/answer/script/ScriptShootPanel";
import { buildChannelStudioPath } from "@/lib/channelStudioHandoff";
import {
  planStudioComposerSubmit,
  type StudioComposerPill,
} from "@/lib/studioComposer";
import { AnswerShell } from "@/components/v2/answer/AnswerShell";
import { FollowUpComposer } from "@/components/v2/answer/FollowUpComposer";
import { IntentCtaRail } from "@/components/v2/answer/IntentCtaRail";
import type { IntentCtaContext, IntentCtaSuggestion } from "@/lib/intentCtaSuggestions";
import { appendTurnKindForIntent, appendTurnKindForQuery } from "@/routes/_app/intent-router";
import {
  parseAnswerHandoffParams,
  planAnswerEntry,
} from "@/routes/_app/intent-router";
import {
  buildAnswerHandoffPath,
  resolveVideoHandoffQuery,
  type ParsedAnswerHandoff,
} from "@/lib/answerHandoff";
import {
  CacheHitBadge,
  LivePipelineStrip,
  isCacheHitPattern,
  useResearchStage,
} from "@/components/v2/answer/ResearchStrip";
import { TimelineRail } from "@/components/v2/answer/TimelineRail";
import { TopBar } from "@/components/v2/TopBar";
import { Btn } from "@/components/v2/Btn";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { surfaceStatsFromPayload } from "@/lib/reportSurfaceStats";
import { profileFirstNicheId } from "@/lib/profileNiches";

const CLOUD = env.VITE_CLOUD_RUN_API_URL;

// Answer-surface error codes recognised by ``analysisErrorCopy`` —
// anything else we get back from ``createAnswerSession`` / the SSE
// pipeline should fall through to a friendly ``fallback`` code so the
// UI never shows raw English like ``"answer/sessions 500"``.
const ANSWER_ERROR_CODES = new Set([
  "insufficient_credits",
  "daily_free_limit",
  "stream_failed",
  "stream_timeout",
  "session_not_found",
  "no_cloud_run",
  "network_failed",
  "start_failed",
  "follow_up_failed",
  "aborted",
  "auth",
  "session_expired",
  // Structured codes from cloud-run/main.py _classify_create_session_error.
  "invalid_niche",
  "invalid_payload",
  "idempotency_conflict",
  "non_tiktok_url",
  "ensemble_quota",
  "gemini_quota_exceeded",
]);

/** Stream errors where TD-4 resume or a fresh primary retry may recover. */
const RETRYABLE_STREAM_ERRORS = new Set([
  "stream_failed",
  "stream_timeout",
  "network_failed",
]);

/** Errors that may show the inline ``Gửi lại`` action (not billing/auth/validation). */
function errorAllowsInlineRetry(code: string): boolean {
  if (code === "follow_up_failed" || code === "start_failed") return true;
  return RETRYABLE_STREAM_ERRORS.has(code);
}

function showInlineRetryButton(opts: {
  error: string;
  canResumeInterruptedStream: boolean;
  sessionId: string | null;
  turnCount: number;
  followUp: string;
  primaryRetryQuery: string;
}): boolean {
  const { error, canResumeInterruptedStream, sessionId, turnCount, followUp, primaryRetryQuery } =
    opts;
  if (!errorAllowsInlineRetry(error) || canResumeInterruptedStream) return false;
  if (error === "follow_up_failed") {
    return Boolean(sessionId && followUp.trim());
  }
  if (error === "start_failed") {
    return Boolean(primaryRetryQuery);
  }
  // Fresh primary re-stream — only before the first persisted turn.
  return turnCount === 0 && Boolean(primaryRetryQuery);
}

function answerSessionUrlParams(
  sessionId: string,
  q: string,
  handoff: ParsedAnswerHandoff,
): URLSearchParams {
  const next = new URLSearchParams({ session: sessionId, q });
  if (handoff.mode) next.set("mode", handoff.mode);
  if (handoff.from) next.set("from", handoff.from);
  return next;
}

function primeEmptySessionDetailCache(
  queryClient: QueryClient,
  row: AnswerSessionRow,
  initialQ: string,
): void {
  queryClient.setQueryData<AnswerDetailCache>(
    answerSessionKeys.detail(row.id),
    (prev) =>
      prev ?? {
        session: {
          ...row,
          title: row.title ?? null,
          initial_q: initialQ,
        },
        turns: [],
      },
  );
}

function codeFromRawErrorMessage(message: string): string | null {
  const trimmed = message.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed) as { error?: unknown; detail?: unknown };
    if (typeof parsed.error === "string" && ANSWER_ERROR_CODES.has(parsed.error)) {
      return parsed.error;
    }
    if (typeof parsed.detail === "string" && ANSWER_ERROR_CODES.has(parsed.detail)) {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      return "invalid_payload";
    }
  } catch {
    // Not JSON — continue with heuristic matching below.
  }
  if (trimmed.includes("literal_error") && trimmed.includes('"loc":["body"')) {
    return "invalid_payload";
  }
  return null;
}

function pickAnswerErrorCode(e: unknown, fallback: string): string {
  if (e instanceof Error) {
    if (e.name === "SessionExpired") return "session_expired";
    if (e.name === "SessionNotFound") return "session_not_found";
    if (e.name === "FetchTimeout") return "stream_timeout";
    const lower = e.message?.toLowerCase() ?? "";
    if (
      lower.includes("failed to fetch") ||
      lower.includes("networkerror") ||
      lower.includes("load failed") ||
      (e.name === "TypeError" && lower.includes("fetch"))
    ) {
      return "network_failed";
    }
    const parsedCode = codeFromRawErrorMessage(e.message ?? "");
    if (parsedCode) return parsedCode;
    if (ANSWER_ERROR_CODES.has(e.message)) return e.message;
    if (e.message?.startsWith("http_")) return e.message;
  }
  if (typeof e === "string" && ANSWER_ERROR_CODES.has(e)) return e;
  return fallback;
}

/** Hero H1: long TikTok URLs wrap; font scales down on narrow viewports (vi). */
const ANSWER_HERO_H1_CLASS =
  "gv-tight mt-0 w-full min-w-0 max-w-[880px] [overflow-wrap:anywhere] text-[clamp(0.875rem,2.25vi+0.45rem,2.35rem)] leading-[1.2] tracking-[-0.03em] text-[color:var(--gv-ink)] sm:leading-[1.15]";

function evidenceVideoQueryFromPayload(p: ReportV1 | null): string | null {
  if (!p) return null;
  if (p.kind === "pattern" || p.kind === "generic") {
    const ev = p.report.evidence_videos?.[0];
    if (ev?.video_id) {
      const handle = ev.creator_handle?.trim();
      if (handle) {
        const h = handle.startsWith("@") ? handle.slice(1) : handle;
        return `https://www.tiktok.com/@${h}/video/${ev.video_id}`;
      }
      return ev.video_id;
    }
  }
  return null;
}

function scriptDraftIdFromTurns(turns: AnswerTurnRow[]): string | null {
  for (let i = turns.length - 1; i >= 0; i -= 1) {
    const row = turns[i]?.payload;
    if (row?.kind === "script") {
      const draftId = (row.report as { draft_id?: string }).draft_id;
      if (typeof draftId === "string" && draftId.trim()) return draftId.trim();
    }
  }
  return null;
}

export default function AnswerScreen() {
  const { user } = useAuth();
  const { data: profile } = useProfile();
  const { data: niches } = useNicheTaxonomy();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const sessionId = searchParams.get("session") ?? searchParams.get("session_id");
  const seedQ = searchParams.get("q") ?? "";
  const shootDraftId = searchParams.get("shoot");
  const handoff = useMemo(() => parseAnswerHandoffParams(searchParams), [searchParams]);

  const [followUp, setFollowUp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [bootstrapLoading, setBootstrapLoading] = useState(false);
  const [studioPill, setStudioPill] = useState<StudioComposerPill>("video_flop");

  const isAnswerLanding = !sessionId && !seedQ.trim();

  const openScriptShoot = useCallback(
    (draftId: string) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("shoot", draftId);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const closeScriptShoot = useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete("shoot");
        return next;
      },
      { replace: true },
    );
  }, [setSearchParams]);

  const uid = user?.id;
  const detailQuery = useAnswerSessionDetail(sessionId, uid);

  const {
    stream,
    status: streamStatus,
    steps,
    streamId,
    lastSeq,
    heartbeatElapsedSec,
    preSynthesisData,
    channelContext,
    narrativeReady,
    reset: resetStream,
  } = useSessionStream<ReportV1>({
    invalidateKeys: uid ? [answerSessionKeys.listsForUser(uid)] : [],
  });

  // Phase 5.7.1 — detect cache-hit pattern (single step_process "Đang đọc...").
  // When true: suppress LivePipelineStrip; show CacheHitBadge instead.
  const isCacheHit = isCacheHitPattern(steps);

  const defaultProfileNicheId = useMemo(() => profileFirstNicheId(profile), [profile]);

  const nicheLabel = useMemo(() => {
    const id = defaultProfileNicheId;
    if (id == null || !niches?.length) return undefined;
    const n = niches.find((row: { id: number; name: string }) => row.id === id);
    return n?.name;
  }, [defaultProfileNicheId, niches]);

  const displayTitle = useMemo(() => {
    const t = detailQuery.data?.session?.title?.trim();
    if (t) return t;
    const iq = detailQuery.data?.session?.initial_q?.trim();
    if (iq) return iq.length > 120 ? `${iq.slice(0, 120)}…` : iq;
    if (sessionId && detailQuery.isLoading) return "Đang tải…";
    return "Phiên nghiên cứu";
  }, [detailQuery.data?.session, detailQuery.isLoading, sessionId]);

  const turns: AnswerTurnRow[] = detailQuery.data?.turns ?? [];
  const sessionIntentType = detailQuery.data?.session?.intent_type;
  const sessionNicheId = detailQuery.data?.session?.niche_id ?? defaultProfileNicheId ?? null;

  const lastPayload = useMemo(() => lastPayloadFromTurns(turns), [turns]);

  /** `?session=` shows an old turn while `?q=` points at a different TikTok video. */
  const sessionQueryVideoMismatch = useMemo(() => {
    const q = seedQ.trim();
    if (!sessionId || !q || !lastPayload || lastPayload.kind !== "video") return false;
    const qVid = extractTikTokVideoIdFromText(q);
    const turnVid = String(lastPayload.report?.video_id ?? "").trim();
    return Boolean(qVid && turnVid && qVid !== turnVid);
  }, [sessionId, seedQ, lastPayload]);

  const surfaceStats = useMemo(() => surfaceStatsFromPayload(lastPayload), [lastPayload]);

  const heroQuestion = useMemo(() => {
    const initial = detailQuery.data?.session?.initial_q?.trim();
    if (initial) return initial;
    const sq = seedQ.trim();
    if (sq) return sq;
    return displayTitle;
  }, [detailQuery.data?.session?.initial_q, seedQ, displayTitle]);

  const dataFreshLabel = useMemo(() => {
    const raw = turns[turns.length - 1]?.created_at;
    if (!raw) return null;
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return null;
    return formatRelativeSinceVi(new Date(), d);
  }, [turns]);

  const streamInFlight = streamStatus === "streaming";

  const loading =
    bootstrapLoading ||
    streamInFlight ||
    (Boolean(sessionId) && detailQuery.isLoading && !detailQuery.data);

  const researchStage = useResearchStage(loading);
  const turnCount = turns.length;

  const hasReplayHandles = useMemo(() => {
    if (!sessionId) return false;
    return hasAnswerStreamReplayHandles(sessionId, streamId, lastSeq);
  }, [sessionId, streamId, lastSeq, streamStatus]);

  const primaryRetryQuery = useMemo(() => {
    const fromSession = detailQuery.data?.session?.initial_q?.trim();
    return followUp.trim() || seedQ.trim() || fromSession || "";
  }, [followUp, seedQ, detailQuery.data?.session?.initial_q]);

  const invalidStreamQuery = nonTikTokUrlValidationMessage(primaryRetryQuery);

  const canResumeInterruptedStream =
    Boolean(sessionId && CLOUD && user) &&
    turnCount === 0 &&
    !streamInFlight &&
    !bootstrapLoading &&
    !invalidStreamQuery &&
    hasReplayHandles &&
    Boolean(error && RETRYABLE_STREAM_ERRORS.has(error));

  /** Stream disconnect errors only apply while the session has no persisted turn. */
  const showAnswerErrorBanner = Boolean(
    error && (turnCount === 0 || !RETRYABLE_STREAM_ERRORS.has(error)),
  );

  const showErrorRetryButton = Boolean(
    error &&
    showAnswerErrorBanner &&
    !streamInFlight &&
    !bootstrapLoading &&
    CLOUD &&
    user &&
    showInlineRetryButton({
      error,
      canResumeInterruptedStream,
      sessionId: sessionId ?? null,
      turnCount,
      followUp,
      primaryRetryQuery,
    }),
  );

  // Legacy state handoff → canonical query params (§3.1).
  useEffect(() => {
    const state = location.state as { initialPrompt?: string; prefillUrl?: string } | null | undefined;
    const incoming = state?.initialPrompt ?? state?.prefillUrl;
    if (!incoming || typeof incoming !== "string" || !incoming.trim()) return;
    const params = new URLSearchParams(searchParams);
    params.set("q", incoming.trim());
    if (!params.has("mode")) params.set("mode", "win");
    navigate(`${location.pathname}?${params.toString()}`, { replace: true, state: {} });
  }, [location.state, location.pathname, navigate, searchParams]);

  /**
   * Blocks duplicate bootstrap for the same `?q=` (React Strict Mode).
   */
  const bootstrapInFlightRef = useRef<string | null>(null);

  function bootstrapDedupeKey(q: string): string {
    return q.trim();
  }

  /**
   * Resume-on-reload guard. ``loadPendingAnswerStream`` validates the
   * entry is for the current session and younger than the client resume
   * window (45s — 15s under the 60s server replay TTL; see sseResume.ts).
   * The ref below prevents double-firing under React Strict
   * Mode, and the detailQuery check prevents a resume when the server
   * already persisted the turn before we reloaded.
   */
  const resumeFiredRef = useRef<string | null>(null);
  /** Skip tab-reload auto-resume right after bootstrap stream fail (user picks "Tiếp tục"). */
  const skipAutoResumeSessionRef = useRef<string | null>(null);
  const prevSessionIdRef = useRef<string | null>(null);

  const startNewAnswer = useCallback(() => {
    setFollowUp("");
    setError(null);
    resetStream();
    bootstrapInFlightRef.current = null;
    skipAutoResumeSessionRef.current = null;
    resumeFiredRef.current = null;
    navigate({ pathname: "/app/answer", search: "" }, { replace: true });
  }, [navigate, resetStream]);

  /** Drop composer/stream stale state when switching between two open sessions. */
  useEffect(() => {
    const prev = prevSessionIdRef.current;
    const next = sessionId ?? null;
    prevSessionIdRef.current = next;
    if (prev === next) return;
    // First attach of ?session= after bootstrap must keep the stream-fail banner.
    if (prev === null) return;
    setError(null);
    resetStream();
    resumeFiredRef.current = null;
    skipAutoResumeSessionRef.current = null;
  }, [sessionId, resetStream]);

  /** Completed sessions must not show a prior stream-fail banner or pipeline snapshot. */
  useEffect(() => {
    if (turnCount === 0 || streamInFlight || bootstrapLoading) return;
    setError((prev) => (prev && RETRYABLE_STREAM_ERRORS.has(prev) ? null : prev));
    if (streamStatus !== "idle") {
      resetStream();
    }
    clearPendingAnswerStream();
  }, [turnCount, streamInFlight, bootstrapLoading, streamStatus, resetStream]);

  useEffect(() => {
    if (!sessionId || !CLOUD || !user) return;
    if (skipAutoResumeSessionRef.current === sessionId) return;
    // If turns already exist the stream completed before reload — the
    // persisted entry is stale and would trigger a no-op fresh run if
    // we followed it. Clear.
    if (detailQuery.isLoading) return;
    if ((detailQuery.data?.turns?.length ?? 0) > 0) {
      clearPendingAnswerStream();
      return;
    }
    if (resumeFiredRef.current === sessionId) return;
    const pending = loadPendingAnswerStream(sessionId);
    if (!pending) return;
    resumeFiredRef.current = sessionId;

    void (async () => {
      setBootstrapLoading(true);
      setError(null);
      try {
        const streamArgs = buildResumeAnswerStreamArgs({
          sessionId: pending.sessionId,
          query: pending.query,
          pending,
          sessionFormat: pending.sessionFormat ?? null,
          handoff,
          hookStreamId: null,
          hookLastSeq: 0,
        });
        if (!streamArgs) return;
        const result = await stream(streamArgs);
        if (!result.ok) {
          setError(pickAnswerErrorCode(result.error, "stream_failed"));
          return;
        }
        if (result.finalPayload) {
          const nextIndex = detailQuery.data?.turns.length ?? 0;
          const fallbackSession: AnswerDetailCache["session"] =
            detailQuery.data?.session ?? {
              id: pending.sessionId,
              user_id: user.id,
              title: null,
              initial_q: pending.query,
              intent_type: "generic",
              format: (pending.sessionFormat ?? "generic") as AnswerSessionRow["format"],
              niche_id: null,
            };
          applyOptimisticAnswerTurn(queryClient, pending.sessionId, fallbackSession, {
            id: `optimistic-${pending.sessionId}-${nextIndex}`,
            session_id: pending.sessionId,
            turn_index: nextIndex,
            kind: pending.turnKind,
            query: pending.query,
            payload: result.finalPayload,
            credits_used: pending.creditsUsed,
            created_at: new Date().toISOString(),
          });
        }
        if (uid) {
          await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
        }
      } catch (e) {
        if (typeof console !== "undefined") {
          console.error("[answer/resume] failed", e);
        }
        setError(pickAnswerErrorCode(e, "stream_failed"));
      } finally {
        setBootstrapLoading(false);
      }
    })();
  }, [
    sessionId,
    CLOUD,
    user,
    detailQuery.isLoading,
    detailQuery.data?.turns,
    detailQuery.data?.session,
    stream,
    queryClient,
    uid,
    handoff,
  ]);

  const resumeInterruptedStream = useCallback(async () => {
    if (!sessionId || !CLOUD || !user) return;
    skipAutoResumeSessionRef.current = null;
    const pending = loadPendingAnswerStream(sessionId);
    const sessionRow = detailQuery.data?.session;
    const query =
      pending?.query?.trim() ||
      sessionRow?.initial_q?.trim() ||
      seedQ.trim();
    if (!query) return;
    const streamArgs = buildResumeAnswerStreamArgs({
      sessionId,
      query,
      pending,
      sessionFormat: sessionRow?.format ?? null,
      handoff,
      hookStreamId: streamId,
      hookLastSeq: lastSeq,
    });
    if (!streamArgs) return;
    setBootstrapLoading(true);
    setError(null);
    try {
      const result = await stream(streamArgs);
      if (!result.ok) {
        setError(pickAnswerErrorCode(result.error, "stream_failed"));
        return;
      }
      logUsage("answer_turn_append", {
        session_id: sessionId,
        kind: pending?.turnKind ?? "primary",
        source_entry: "stream_resume_ui",
      });
      if (result.finalPayload) {
        const nextIndex = detailQuery.data?.turns.length ?? 0;
        const turnKind = pending?.turnKind ?? "primary";
        const fallbackSession: AnswerDetailCache["session"] = sessionRow ?? {
          id: sessionId,
          user_id: user.id,
          title: null,
          initial_q: query,
          intent_type: "generic",
          format: (streamArgs.sessionFormat ?? "generic") as AnswerSessionRow["format"],
          niche_id: null,
        };
        applyOptimisticAnswerTurn(queryClient, sessionId, fallbackSession, {
          id: `optimistic-${sessionId}-${nextIndex}`,
          session_id: sessionId,
          turn_index: nextIndex,
          kind: turnKind,
          query,
          payload: result.finalPayload,
          credits_used:
            pending?.creditsUsed ??
            optimisticAnswerCreditsUsed(
              turnKind,
              pending?.sessionFormat ?? sessionRow?.format,
            ),
          created_at: new Date().toISOString(),
        });
      }
      if (uid) {
        await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
      }
    } catch (e) {
      if (typeof console !== "undefined") {
        console.error("[answer/resume-ui] failed", e);
      }
      setError(pickAnswerErrorCode(e, "stream_failed"));
    } finally {
      setBootstrapLoading(false);
    }
  }, [
    sessionId,
    CLOUD,
    user,
    detailQuery.data?.session,
    detailQuery.data?.turns.length,
    seedQ,
    handoff,
    stream,
    streamId,
    lastSeq,
    queryClient,
    uid,
  ]);

  const retryFailedPrimaryTurn = useCallback(async () => {
    if (!sessionId || !CLOUD || !user || bootstrapLoading || streamInFlight) return;
    const query = primaryRetryQuery;
    if (!query) return;
    const sessionRow = detailQuery.data?.session;
    const pending = loadPendingAnswerStream(sessionId);
    const sessionFormat = sessionRow?.format ?? pending?.sessionFormat ?? "generic";
    const turnKind = pending?.turnKind ?? "primary";
    setBootstrapLoading(true);
    setError(null);
    try {
      const result = await stream({
        mode: "answer_turn",
        answerSessionId: sessionId,
        query,
        turnKind,
        sessionFormat,
        videoMode: sessionFormat === "video" ? handoff.mode ?? undefined : undefined,
        sourceEntry: "error_retry_ui",
      });
      if (!result.ok) {
        setError(pickAnswerErrorCode(result.error, "stream_failed"));
        return;
      }
      logUsage("answer_turn_append", {
        session_id: sessionId,
        kind: turnKind,
        source_entry: "error_retry_ui",
      });
      if (result.finalPayload) {
        const nextIndex = detailQuery.data?.turns.length ?? 0;
        const fallbackSession: AnswerDetailCache["session"] = sessionRow ?? {
          id: sessionId,
          user_id: user.id,
          title: null,
          initial_q: query,
          intent_type: "generic",
          format: sessionFormat as AnswerSessionRow["format"],
          niche_id: null,
        };
        applyOptimisticAnswerTurn(queryClient, sessionId, fallbackSession, {
          id: `optimistic-${sessionId}-${nextIndex}`,
          session_id: sessionId,
          turn_index: nextIndex,
          kind: turnKind,
          query,
          payload: result.finalPayload,
          credits_used:
            pending?.creditsUsed ??
            optimisticAnswerCreditsUsed(turnKind, sessionFormat),
          created_at: new Date().toISOString(),
        });
      }
      if (uid) {
        await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
      }
    } catch (e) {
      if (typeof console !== "undefined") {
        console.error("[answer/retry-primary] failed", e);
      }
      setError(pickAnswerErrorCode(e, "stream_failed"));
    } finally {
      setBootstrapLoading(false);
    }
  }, [
    sessionId,
    CLOUD,
    user,
    bootstrapLoading,
    streamInFlight,
    primaryRetryQuery,
    detailQuery.data?.session,
    detailQuery.data?.turns.length,
    handoff.mode,
    stream,
    queryClient,
    uid,
  ]);

  const appendFollowUpTurn = useCallback(
    async (opts: { sourceEntry: "composer" | "error_retry_ui"; clearComposerOnSuccess: boolean }) => {
      if (!sessionId || !CLOUD || !user || bootstrapLoading || streamInFlight) return;
      const q = followUp.trim();
      if (!q) return;
      const urlBlock = nonTikTokUrlValidationMessage(q);
      if (urlBlock) {
        setError("non_tiktok_url");
        return;
      }
      setBootstrapLoading(true);
      setError(null);
      try {
        const entry = planAnswerEntry(q, true);
        if (entry.kind === "blocked") {
          setError(entry.reason === "non_tiktok_url" ? "non_tiktok_url" : "follow_up_failed");
          return;
        }
        if (entry.kind === "redirect") {
          navigate(entry.to);
          if (opts.clearComposerOnSuccess) setFollowUp("");
          return;
        }
        const turnKind = appendTurnKindForQuery(q, true);
        const result = await stream({
          mode: "answer_turn",
          answerSessionId: sessionId,
          query: q,
          turnKind,
          sessionFormat: detailQuery.data?.session?.format,
          sourceEntry: opts.sourceEntry,
          videoMode: handoff.mode ?? undefined,
        });
        if (!result.ok) {
          setError(pickAnswerErrorCode(result.error, "follow_up_failed"));
          return;
        }
        if (opts.clearComposerOnSuccess) setFollowUp("");
        logUsage("answer_turn_append", {
          session_id: sessionId,
          kind: turnKind,
          intent_type: entry.intent_type,
          source_entry: opts.sourceEntry,
        });
        if (result.finalPayload) {
          const cached = queryClient.getQueryData<AnswerDetailCache>(
            answerSessionKeys.detail(sessionId),
          );
          const nextIndex = cached?.turns.length ?? 0;
          const synthesized: AnswerTurnRow = {
            id: `optimistic-${sessionId}-${nextIndex}`,
            session_id: sessionId,
            turn_index: nextIndex,
            kind: turnKind,
            query: q,
            payload: result.finalPayload,
            credits_used: turnKind === "script" ? 3 : 0,
            created_at: new Date().toISOString(),
          };
          queryClient.setQueryData<AnswerDetailCache>(
            answerSessionKeys.detail(sessionId),
            (prev) => {
              const fallbackSession = prev?.session ?? {
                id: sessionId,
                user_id: user.id,
                title: null,
                initial_q: q,
                intent_type: entry.intent_type,
                format: detailQuery.data?.session?.format ?? "generic",
                niche_id: null,
              };
              return injectOptimisticTurn(prev, fallbackSession, synthesized);
            },
          );
        }
        if (uid) {
          await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
        }
      } catch (e) {
        if (typeof console !== "undefined") {
          console.error("[answer/follow-up] failed", e);
        }
        setError(pickAnswerErrorCode(e, "follow_up_failed"));
      } finally {
        setBootstrapLoading(false);
      }
    },
    [
      sessionId,
      CLOUD,
      user,
      bootstrapLoading,
      streamInFlight,
      followUp,
      navigate,
      stream,
      queryClient,
      uid,
      handoff.mode,
      detailQuery.data?.session?.format,
    ],
  );

  const submitFollowUpFromComposer = useCallback(
    () => void appendFollowUpTurn({ sourceEntry: "composer", clearComposerOnSuccess: true }),
    [appendFollowUpTurn],
  );

  const retryFollowUpTurn = useCallback(
    () => void appendFollowUpTurn({ sourceEntry: "error_retry_ui", clearComposerOnSuccess: false }),
    [appendFollowUpTurn],
  );

  useEffect(() => {
    if (!sessionId && !seedQ.trim()) {
      bootstrapInFlightRef.current = null;
      setFollowUp("");
    }
  }, [sessionId, seedQ]);

  useEffect(() => {
    if (sessionId || !seedQ.trim() || !CLOUD || !user) return;
    const submittedQ = seedQ.trim();
    const bootstrapKey = bootstrapDedupeKey(submittedQ);
    if (bootstrapInFlightRef.current === bootstrapKey) return;
    bootstrapInFlightRef.current = bootstrapKey;

    void (async () => {
      setBootstrapLoading(true);
      setError(null);
      try {
        const entry = planAnswerEntry(seedQ, false);
        if (entry.kind === "blocked") {
          bootstrapInFlightRef.current = null;
          setFollowUp(submittedQ);
          setError("non_tiktok_url");
          return;
        }
        if (entry.kind === "redirect") {
          bootstrapInFlightRef.current = null;
          navigate(entry.to, { replace: true });
          return;
        }
        const { format: sessionFormat, intent_type: sessionIntent } = entry;

        const { data: { session: authSession } } = await supabase.auth.getSession();
        if (!authSession) throw new Error("auth");
        const row = await createAnswerSession(
          authSession.access_token,
          {
            initial_q: seedQ,
            intent_type: sessionIntent,
            niche_id: defaultProfileNicheId,
            format: sessionFormat,
          },
          crypto.randomUUID(),
        );

        logUsage("answer_session_create", {
          session_id: row.id,
          format: sessionFormat,
          intent_type: sessionIntent,
        });

        const result = await stream({
          mode: "answer_turn",
          answerSessionId: row.id,
          query: seedQ,
          turnKind: "primary",
          sessionFormat: sessionFormat,
          videoMode:
            sessionFormat === "video" ? handoff.mode ?? undefined : undefined,
          sourceEntry: handoff.from ?? undefined,
        });

        if (!result.ok) {
          bootstrapInFlightRef.current = null;
          setFollowUp(submittedQ);
          skipAutoResumeSessionRef.current = row.id;
          resetStream();
          primeEmptySessionDetailCache(queryClient, row, submittedQ);
          setSearchParams(answerSessionUrlParams(row.id, seedQ, handoff), {
            replace: true,
          });
          // Session row already exists — failure is the primary SSE turn, not create.
          setError(
            nonTikTokUrlValidationMessage(submittedQ)
              ? "non_tiktok_url"
              : pickAnswerErrorCode(result.error, "stream_failed"),
          );
          return;
        }

        skipAutoResumeSessionRef.current = null;
        logUsage("answer_turn_append", { session_id: row.id, kind: "primary" });
        if (result.finalPayload) {
          const synthesized: AnswerTurnRow = {
            id: `optimistic-${row.id}-0`,
            session_id: row.id,
            turn_index: 0,
            kind: "primary",
            query: seedQ,
            payload: result.finalPayload,
            credits_used:
              sessionFormat === "script"
                ? 3
                : sessionFormat === "compare"
                  ? 2
                  : sessionFormat === "video"
                    ? 2
                    : 1,
            created_at: new Date().toISOString(),
          };
          queryClient.setQueryData<AnswerDetailCache>(
            answerSessionKeys.detail(row.id),
            (prev) =>
              injectOptimisticTurn(
                prev,
                { ...row, title: row.title ?? null, initial_q: seedQ },
                synthesized,
              ),
          );
        }
        setSearchParams(answerSessionUrlParams(row.id, seedQ, handoff), { replace: true });
        if (uid) {
          await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
        }
      } catch (e) {
        bootstrapInFlightRef.current = null;
        // Keep the raw error visible in devtools so ops can trace Cloud Run
        // failures (404 / 500 / CORS / timeout) — the user-facing copy is
        // the friendly Vietnamese string below.
        if (typeof console !== "undefined") {
          console.error("[answer/bootstrap] failed", e);
        }
        setFollowUp(submittedQ);
        setError(pickAnswerErrorCode(e, "start_failed"));
      } finally {
        setBootstrapLoading(false);
      }
    })();
  }, [sessionId, seedQ, CLOUD, user, defaultProfileNicheId, handoff, setSearchParams, navigate, queryClient, uid, stream, resetStream]);

  const appendCtaTurn = useCallback(
    async (suggestion: IntentCtaSuggestion, query: string) => {
      if (!sessionId || !query.trim() || !CLOUD || !user) return;
      setBootstrapLoading(true);
      setError(null);
      try {
        const turnKind = appendTurnKindForIntent(suggestion.intentType);
        const result = await stream({
          mode: "answer_turn",
          answerSessionId: sessionId,
          query: query.trim(),
          turnKind,
          sessionFormat: detailQuery.data?.session?.format,
          sourceEntry: "intent_cta",
          intentType: suggestion.intentType,
          ctaId: suggestion.id,
          videoMode: handoff.mode ?? undefined,
        });
        if (!result.ok) {
          setError(pickAnswerErrorCode(result.error, "follow_up_failed"));
          return;
        }
        logUsage("answer_turn_append", {
          session_id: sessionId,
          kind: turnKind,
          intent_type: suggestion.intentType,
          source_entry: "intent_cta",
          cta_id: suggestion.id,
        });
        if (result.finalPayload) {
          const cached = queryClient.getQueryData<AnswerDetailCache>(
            answerSessionKeys.detail(sessionId),
          );
          const nextIndex = cached?.turns.length ?? 0;
          const synthesized: AnswerTurnRow = {
            id: `optimistic-${sessionId}-${nextIndex}`,
            session_id: sessionId,
            turn_index: nextIndex,
            kind: turnKind,
            query: query.trim(),
            payload: result.finalPayload,
            credits_used: turnKind === "script" ? 3 : 0,
            created_at: new Date().toISOString(),
          };
          queryClient.setQueryData<AnswerDetailCache>(
            answerSessionKeys.detail(sessionId),
            (prev) => {
              const fallbackSession = prev?.session ?? {
                id: sessionId,
                user_id: user.id,
                title: null,
                initial_q: query.trim(),
                intent_type: suggestion.intentType,
                format: detailQuery.data?.session?.format ?? "generic",
                niche_id: null,
              };
              return injectOptimisticTurn(prev, fallbackSession, synthesized);
            },
          );
        }
        if (uid) {
          await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
        }
      } catch (e) {
        if (typeof console !== "undefined") {
          console.error("[answer/cta] failed", e);
        }
        setError(pickAnswerErrorCode(e, "follow_up_failed"));
      } finally {
        setBootstrapLoading(false);
      }
    },
    [
      sessionId,
      CLOUD,
      user,
      stream,
      queryClient,
      uid,
      handoff.mode,
      detailQuery.data?.session?.format,
    ],
  );

  const handleIntentCta = useCallback(
    (suggestion: IntentCtaSuggestion, query: string) => {
      if (suggestion.action === "handoff") {
        const report = lastPayload?.kind === "video" ? lastPayload.report : null;
        const meta = report?.meta;
        const url =
          resolveVideoHandoffQuery({
            seedQ,
            sessionInitialQ: detailQuery.data?.session?.initial_q,
            videoId: report?.video_id,
            creatorHandle: typeof meta?.creator === "string" ? meta.creator : null,
          }) ??
          evidenceVideoQueryFromPayload(lastPayload) ??
          query.trim();
        if (!url) return;
        navigate(
          buildAnswerHandoffPath({
            q: url,
            mode: handoff.mode ?? "win",
            ...(handoff.from ? { from: handoff.from } : {}),
          }),
        );
        return;
      }
      if (suggestion.action === "compare_navigate") {
        const urlA =
          resolveVideoHandoffQuery({
            seedQ,
            sessionInitialQ: detailQuery.data?.session?.initial_q,
            videoId:
              lastPayload?.kind === "video" ? lastPayload.report.video_id : undefined,
            creatorHandle:
              lastPayload?.kind === "video" &&
              typeof lastPayload.report.meta?.creator === "string"
                ? lastPayload.report.meta.creator
                : null,
          }) ?? "";
        const urlB = query.trim();
        if (!urlA || !urlB) return;
        // Compare is now an answer-session format: hand both URLs to
        // ``/app/answer`` as the query; ``planAnswerEntry`` detects the
        // ≥2-URL compare intent and opens a ``compare`` session.
        navigate(
          buildAnswerHandoffPath({
            q: `${urlA} ${urlB}`,
            ...(handoff.from ? { from: handoff.from } : {}),
          }),
        );
        return;
      }
      if (suggestion.action === "shoot_panel") {
        const draftId = scriptDraftIdFromTurns(turns);
        if (draftId) openScriptShoot(draftId);
        return;
      }
      if (suggestion.action === "channel_handoff") {
        const report = lastPayload?.kind === "video" ? lastPayload.report : null;
        const handle =
          typeof report?.meta?.creator === "string" ? report.meta.creator : null;
        if (!handle?.trim()) return;
        const videoUrl =
          resolveVideoHandoffQuery({
            seedQ,
            sessionInitialQ: detailQuery.data?.session?.initial_q,
            videoId: report?.video_id,
            creatorHandle: handle,
          }) ?? undefined;
        navigate(
          buildChannelStudioPath({
            handle,
            videoUrl,
          }),
        );
        return;
      }
      void appendCtaTurn(suggestion, query);
    },
    [
      appendCtaTurn,
      navigate,
      seedQ,
      handoff,
      lastPayload,
      turns,
      openScriptShoot,
      detailQuery.data?.session?.initial_q,
    ],
  );

  const submitComposer = useCallback(() => {
    const q = followUp.trim();
    if (!q || !CLOUD || !user || bootstrapLoading || streamInFlight) return;
    const urlBlock = nonTikTokUrlValidationMessage(q);
    if (urlBlock) {
      setError("non_tiktok_url");
      return;
    }
    if (!sessionId) {
      const plan = planStudioComposerSubmit(studioPill, q);
      if (plan.kind === "blocked") {
        setError(plan.reason === "non_tiktok_url" ? "non_tiktok_url" : "start_failed");
        return;
      }
      navigate(plan.to, { replace: true });
      setFollowUp("");
      setError(null);
      return;
    }
    if (turnCount === 0) {
      void retryFailedPrimaryTurn();
      return;
    }
    void submitFollowUpFromComposer();
  }, [
    followUp,
    CLOUD,
    user,
    bootstrapLoading,
    streamInFlight,
    sessionId,
    studioPill,
    navigate,
    turnCount,
    retryFailedPrimaryTurn,
    submitFollowUpFromComposer,
  ]);

  const retryFromErrorBanner = useCallback(() => {
    if (!error || !errorAllowsInlineRetry(error)) return;
    if (canResumeInterruptedStream) {
      void resumeInterruptedStream();
      return;
    }
    if (error === "follow_up_failed" && sessionId && followUp.trim()) {
      void retryFollowUpTurn();
      return;
    }
    if (error === "start_failed" || !sessionId) {
      submitComposer();
      return;
    }
    if (turnCount === 0 && RETRYABLE_STREAM_ERRORS.has(error)) {
      void retryFailedPrimaryTurn();
    }
  }, [
    canResumeInterruptedStream,
    resumeInterruptedStream,
    error,
    sessionId,
    followUp,
    retryFollowUpTurn,
    submitComposer,
    turnCount,
    retryFailedPrimaryTurn,
  ]);

  const videoStreamProgress =
    streamInFlight && detailQuery.data?.session?.format === "video"
      ? { preSynthesisData, channelContext, narrativeReady }
      : undefined;

  const intentCtaContext = useMemo((): IntentCtaContext => {
    const report = lastPayload?.kind === "video" ? lastPayload.report : null;
    const meta = report?.meta;
    return {
      format: detailQuery.data?.session?.format ?? "generic",
      mode: handoff.mode,
      videoQuery: resolveVideoHandoffQuery({
        seedQ,
        sessionInitialQ: detailQuery.data?.session?.initial_q,
        videoId: report?.video_id,
        creatorHandle: typeof meta?.creator === "string" ? meta.creator : null,
      }),
      scriptDraftId: scriptDraftIdFromTurns(turns),
      evidenceVideoQuery: evidenceVideoQueryFromPayload(lastPayload),
      sessionInitialQ: detailQuery.data?.session?.initial_q ?? null,
      creatorHandle:
        typeof meta?.creator === "string" && meta.creator.trim()
          ? meta.creator.trim()
          : null,
    };
  }, [
    detailQuery.data?.session?.format,
    detailQuery.data?.session?.initial_q,
    handoff.mode,
    seedQ,
    lastPayload,
    turns,
  ]);

  const showIntentCtaRail = Boolean(
    sessionId && lastPayload && !loading && !streamInFlight && turnCount > 0,
  );

  const appendVideoTurnQuery = useCallback(
    (query: string) => {
      if (!sessionId) return;
      void appendCtaTurn(
        {
          id: "video_script",
          label: "Tạo kịch bản",
          intentType: "shot_list",
          action: "append_turn",
        },
        query,
      );
    },
    [sessionId, appendCtaTurn],
  );

  return (
    <AppLayout active="answer" enableMobileSidebar>
      <div className="w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="Nghiên cứu"
          title="Báo Cáo Nghiên Cứu"
          right={
            <>
              <Btn variant="ink" size="sm" type="button" onClick={startNewAnswer}>
                <Plus className="h-3.5 w-3.5 shrink-0" strokeWidth={2} aria-hidden />
                Phân tích mới
              </Btn>
            </>
          }
        />
        <AnswerShell
          crumb={
            <div className="mb-6 flex flex-col gap-3 border-b border-[color:var(--gv-rule)] pb-5 min-[700px]:flex-row min-[700px]:items-center min-[700px]:justify-between">
              <nav
                className="flex flex-wrap items-center gap-1.5 text-[color:var(--gv-ink-4)]"
                aria-label="Breadcrumb"
              >
                <button
                  type="button"
                  onClick={() => navigate("/app")}
                  aria-label="Quay lại Studio"
                  className="inline-flex min-h-[44px] items-center gap-1 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-1 gv-kicker leading-none tracking-[0.06em] text-[color:var(--gv-ink-3)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
                >
                  <ArrowLeft className="h-3 w-3 shrink-0" strokeWidth={2} aria-hidden />
                  Studio
                </button>
                {nicheLabel ? (
                  <span className="gv-kicker text-[color:var(--gv-ink-3)]">
                    <span className="text-[color:var(--gv-rule)]" aria-hidden>
                      {" "}
                      /{" "}
                    </span>
                    Nghiên cứu · {nicheLabel}
                  </span>
                ) : null}
              </nav>
              {sessionId && surfaceStats && !loading ? (
                <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-0.5 gv-kicker text-[color:var(--gv-ink-3)]">
                  <Check className="h-3 w-3 text-[color:var(--gv-pos)]" strokeWidth={2.5} aria-hidden />
                  <span className="tabular-nums">{surfaceStats.sampleVideos.toLocaleString("vi-VN")} video</span>
                  <span className="text-[color:var(--gv-rule)]" aria-hidden>
                    ·
                  </span>
                  <span className="tabular-nums">{surfaceStats.sourceUnits.toLocaleString("vi-VN")} nguồn</span>
                </span>
              ) : null}
            </div>
          }
          header={
            sessionId ? (
              <header className="border-b border-[color:var(--gv-rule)] pb-8">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <p className="gv-kicker text-[color:var(--gv-ink-3)]">
                    Câu hỏi
                  </p>
                  {dataFreshLabel ? (
                    <p className="gv-kicker text-[color:var(--gv-ink-3)]">{dataFreshLabel}</p>
                  ) : null}
                </div>
                <h1
                  className={ANSWER_HERO_H1_CLASS}
                  style={{ fontFamily: "var(--gv-font-display)" }}
                  title={heroQuestion}
                >
                  {heroQuestion}
                </h1>
                {/* Phase 5.7.1 — suppress full strip on cache hit; 5.7.2 — show badge */}
                {isCacheHit ? (
                  <CacheHitBadge
                    computedAt={
                      typeof (lastPayload as Record<string, unknown> | null)?.computed_at === "string"
                        ? (lastPayload as Record<string, unknown>).computed_at as string
                        : null
                    }
                  />
                ) : (
                  <LivePipelineStrip
                    steps={steps}
                    done={Boolean(!loading && lastPayload)}
                    loading={loading}
                    stage={researchStage}
                    videoCount={surfaceStats?.sampleVideos}
                    channelCount={
                      surfaceStats && surfaceStats.channelRows > 0 ? surfaceStats.channelRows : null
                    }
                    heartbeatElapsedSec={heartbeatElapsedSec}
                  />
                )}
              </header>
            ) : seedQ.trim() ? (
              <header className="border-b border-[color:var(--gv-rule)] pb-8">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <p className="gv-kicker text-[color:var(--gv-ink-3)]">
                    Câu hỏi
                  </p>
                  <p className="gv-kicker text-[color:var(--gv-ink-3)]">—</p>
                </div>
                <h1
                  className={ANSWER_HERO_H1_CLASS}
                  style={{ fontFamily: "var(--gv-font-display)" }}
                  title={seedQ.trim()}
                >
                  {seedQ.trim()}
                </h1>
                {bootstrapLoading ? (
                  <LivePipelineStrip
                    steps={steps}
                    done={false}
                    loading={loading}
                    stage={researchStage}
                    videoCount={surfaceStats?.sampleVideos}
                    channelCount={
                      surfaceStats && surfaceStats.channelRows > 0
                        ? surfaceStats.channelRows
                        : null
                    }
                    heartbeatElapsedSec={heartbeatElapsedSec}
                  />
                ) : null}
              </header>
            ) : null
          }
          main={
            <TimelineRail turnCount={turnCount}>
              {sessionQueryVideoMismatch ? (
                <div
                  className="mb-6 rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3"
                  role="status"
                >
                  <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink-2)]">
                    Link trong thanh địa chỉ khác video đang hiển thị trong phiên này. Bạn có thể mở phân tích
                    mới cho URL vừa dán.
                  </p>
                  <Btn
                    variant="ink"
                    size="sm"
                    type="button"
                    className="mt-3"
                    onClick={() => setSearchParams({ q: seedQ.trim() }, { replace: true })}
                  >
                    Phân tích video này
                  </Btn>
                </div>
              ) : null}
              {showAnswerErrorBanner ? (
                <div
                  className="mt-4 rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3"
                  role="alert"
                >
                  <p className="m-0 text-sm leading-relaxed text-[var(--gv-danger)]">
                    {error && RETRYABLE_STREAM_ERRORS.has(error)
                      ? answerStreamErrorCopy(error, canResumeInterruptedStream)
                      : analysisErrorCopy(error)}
                  </p>
                  {canResumeInterruptedStream || showErrorRetryButton ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {canResumeInterruptedStream ? (
                        <Btn
                          variant="ink"
                          size="sm"
                          type="button"
                          data-testid="resume-stream-btn"
                          onClick={() => void resumeInterruptedStream()}
                        >
                          Tiếp tục phân tích
                        </Btn>
                      ) : null}
                      {showErrorRetryButton ? (
                        <Btn
                          variant="ink"
                          size="sm"
                          type="button"
                          data-testid="error-retry-btn"
                          disabled={bootstrapLoading || streamInFlight}
                          onClick={() => void retryFromErrorBanner()}
                        >
                          Gửi lại
                        </Btn>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
              {detailQuery.isError && sessionId ? (
                <div
                  className="mt-4 rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3"
                  role="alert"
                >
                  <p className="m-0 text-sm leading-relaxed text-[var(--gv-danger)]">
                    {analysisErrorCopy(
                      pickAnswerErrorCode(detailQuery.error, "start_failed"),
                    )}
                  </p>
                  <Btn
                    variant="ink"
                    size="sm"
                    type="button"
                    className="mt-3"
                    data-testid="reload-session-btn"
                    disabled={detailQuery.isFetching}
                    onClick={() => void detailQuery.refetch()}
                  >
                    Tải lại phiên
                  </Btn>
                </div>
              ) : null}
              {shootDraftId ? (
                <div className="mb-8">
                  <ScriptShootPanel draftId={shootDraftId} onClose={closeScriptShoot} />
                </div>
              ) : null}
              {turnCount > 0 ? (
                <div
                  className="space-y-10"
                  aria-live="polite"
                  aria-busy={loading}
                  aria-relevant="additions text"
                >
                  {turns.map((t, idx) => (
                    <ContinuationTurn
                      key={t.id}
                      turn={t}
                      sessionId={sessionId}
                      sessionNicheId={sessionNicheId}
                      onOpenScriptShoot={openScriptShoot}
                      sessionIntentType={sessionIntentType}
                      videoStreamProgress={
                        videoStreamProgress &&
                        t.payload.kind === "video" &&
                        idx === turns.length - 1
                          ? videoStreamProgress
                          : undefined
                      }
                      onRequestAppendTurn={
                        t.payload.kind === "video" &&
                        idx === turns.length - 1 &&
                        sessionId
                          ? appendVideoTurnQuery
                          : undefined
                      }
                    />
                  ))}
                </div>
              ) : loading ? (
                // Stream in flight, no turns persisted yet — show a content
                // skeleton so the body isn't blank while LivePipelineStrip
                // in the header tracks step-by-step progress.
                <div
                  className="mt-6 animate-pulse space-y-3"
                  aria-live="polite"
                  aria-busy={true}
                  aria-label="Đang tạo báo cáo"
                >
                  <div className="h-4 w-3/4 rounded-md bg-[color:var(--gv-rule)]" />
                  <div className="h-4 w-1/2 rounded-md bg-[color:var(--gv-rule)]" />
                  <div className="h-4 w-2/3 rounded-md bg-[color:var(--gv-rule)]" />
                  <div className="mt-6 h-24 w-full rounded-[var(--gv-radius-md)] bg-[color:var(--gv-rule)]" />
                </div>
              ) : sessionId && !loading && !canResumeInterruptedStream ? (
                <div className="mt-4 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
                  <p className="gv-serif text-[17px] leading-snug text-[color:var(--gv-ink)]">
                    Chưa có lượt trong phiên này.
                  </p>
                  <p className="mt-2 text-[12px] leading-relaxed text-[color:var(--gv-ink-3)]">
                    Nếu bạn vừa gửi câu hỏi, có thể báo cáo chưa kịp persist. Thử tải lại phiên
                    sau vài giây.
                  </p>
                  <button
                    type="button"
                    className="mt-3 gv-kicker text-[color:var(--gv-accent)] underline"
                    onClick={() => void detailQuery.refetch()}
                  >
                    Tải lại phiên
                  </button>
                </div>
              ) : null}
              {showIntentCtaRail ? (
                <div
                  className="mt-6 mb-5 border-t border-[color:var(--gv-rule)] pt-4"
                  aria-label="Gợi ý bước tiếp theo"
                >
                  <p className="mb-3 gv-kicker text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">
                    Tiếp tục nghiên cứu
                  </p>
                  <IntentCtaRail
                    context={intentCtaContext}
                    compact
                    disabled={!CLOUD || !user || bootstrapLoading || streamInFlight}
                    onCta={handleIntentCta}
                  />
                </div>
              ) : null}
              {!sessionId || turnCount === 0 ? (
                <FollowUpComposer
                  value={followUp}
                  onChange={setFollowUp}
                  onSubmit={submitComposer}
                  variant={sessionId ? "followUp" : "initial"}
                  disabled={!CLOUD || !user || bootstrapLoading || streamInFlight}
                  studioPill={isAnswerLanding ? studioPill : undefined}
                  onStudioPillChange={isAnswerLanding ? setStudioPill : undefined}
                  nicheLabel={nicheLabel ?? "ngách của bạn"}
                />
              ) : null}
            </TimelineRail>
          }
        />
      </div>
    </AppLayout>
  );
}
