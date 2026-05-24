/**
 * Phase C.1 — /app/answer research shell (composed primitives + React Query).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
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
import { analysisErrorCopy } from "@/lib/errorMessages";
import { createAnswerSession } from "@/lib/answerApi";
import {
  clearPendingAnswerStream,
  loadPendingAnswerStream,
} from "@/lib/sseResume";
import { supabase } from "@/lib/supabase";
import type { AnswerTurnRow, ReportV1 } from "@/lib/api-types";
import { logUsage } from "@/lib/logUsage";
import { extractTikTokVideoIdFromText } from "@/lib/tiktokUrl";
import { Plus, Check, ArrowLeft } from "lucide-react";
import { ContinuationTurn } from "@/components/v2/answer/ContinuationTurn";
import { ScriptShootPanel } from "@/components/v2/answer/script/ScriptShootPanel";
import {
  parseAnswerHandoffParams,
  planAnswerEntry,
} from "@/routes/_app/intent-router";
import {
  buildAnswerHandoffPath,
  resolveVideoHandoffQuery,
  type AnswerHandoffDepth,
} from "@/lib/answerHandoff";
import { AnswerShell } from "@/components/v2/answer/AnswerShell";
import { FollowUpComposer } from "@/components/v2/answer/FollowUpComposer";
import { IntentCtaRail } from "@/components/v2/answer/IntentCtaRail";
import type { IntentCtaContext, IntentCtaSuggestion } from "@/lib/intentCtaSuggestions";
import { appendTurnKindForIntent } from "@/routes/_app/intent-router";
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
]);

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

  const setAnalysisDepth = useCallback(
    (depth: AnswerHandoffDepth) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("depth", depth);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const [followUp, setFollowUp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [bootstrapLoading, setBootstrapLoading] = useState(false);

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

  const { stream, status: streamStatus, steps, heartbeatElapsedSec, preSynthesisData, channelContext, narrativeReady } = useSessionStream<ReportV1>({
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

  /** Tiêu đề hero khi chưa mở phiên — gần mock “CÂU HỎI” + câu hỏi mẫu. */
  const emptyStateHeroQuestion = useMemo(() => {
    const q = seedQ.trim();
    if (q) return q;
    const niche = nicheLabel ?? "ngách của bạn";
    return `Xu hướng đang hot trong ${niche} tuần này?`;
  }, [seedQ, nicheLabel]);

  const streamInFlight = streamStatus === "streaming";

  const loading =
    bootstrapLoading ||
    streamInFlight ||
    (Boolean(sessionId) && detailQuery.isLoading && !detailQuery.data);

  const researchStage = useResearchStage(loading);
  const turnCount = turns.length;

  // Legacy state handoff → canonical query params (§3.1).
  useEffect(() => {
    const state = location.state as { initialPrompt?: string; prefillUrl?: string } | null | undefined;
    const incoming = state?.initialPrompt ?? state?.prefillUrl;
    if (!incoming || typeof incoming !== "string" || !incoming.trim()) return;
    const params = new URLSearchParams(searchParams);
    params.set("q", incoming.trim());
    if (!params.has("depth")) params.set("depth", "basic");
    if (!params.has("mode")) params.set("mode", "win");
    navigate(`${location.pathname}?${params.toString()}`, { replace: true, state: {} });
  }, [location.state, location.pathname, navigate, searchParams]);

  /**
   * Blocks duplicate bootstrap for the same `?q=` (React Strict Mode) but must not
   * stay true forever — otherwise a later Studio submit to `/app/answer?q=…` never runs
   * while this route stays mounted.
   */
  const bootstrapInFlightRef = useRef<string | null>(null);

  /**
   * Resume-on-reload guard. ``loadPendingAnswerStream`` validates the
   * entry is for the current session and younger than the replay TTL
   * (90s). The ref below prevents double-firing under React Strict
   * Mode, and the detailQuery check prevents a resume when the server
   * already persisted the turn before we reloaded.
   */
  const resumeFiredRef = useRef<string | null>(null);

  useEffect(() => {
    if (!sessionId || !CLOUD || !user) return;
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
        const result = await stream({
          mode: "answer_turn",
          answerSessionId: pending.sessionId,
          query: pending.query,
          turnKind: pending.turnKind,
          sessionFormat: pending.sessionFormat ?? null,
          analysisDepth: pending.analysisDepth ?? null,
          resumeStreamId: pending.streamId,
          lastSeq: pending.seq,
          startedAt: pending.startedAt,
        });
        if (!result.ok) {
          setError(result.error);
          return;
        }
        if (result.finalPayload) {
          const nextIndex = detailQuery.data?.turns.length ?? 0;
          const synthesized: AnswerTurnRow = {
            id: `optimistic-${pending.sessionId}-${nextIndex}`,
            session_id: pending.sessionId,
            turn_index: nextIndex,
            kind: pending.turnKind,
            query: pending.query,
            payload: result.finalPayload,
            credits_used: pending.creditsUsed,
            created_at: new Date().toISOString(),
          };
          queryClient.setQueryData<AnswerDetailCache>(
            answerSessionKeys.detail(pending.sessionId),
            (prev) => {
              const fallbackSession = prev?.session ?? {
                id: pending.sessionId,
                user_id: user.id,
                title: null,
                initial_q: pending.query,
                intent_type: "generic",
                format: "generic",
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
    stream,
    queryClient,
    uid,
  ]);

  useEffect(() => {
    if (!sessionId && !seedQ.trim()) {
      bootstrapInFlightRef.current = null;
      setFollowUp("");
    }
  }, [sessionId, seedQ]);

  useEffect(() => {
    if (sessionId || !seedQ.trim() || !CLOUD || !user) return;
    const submittedQ = seedQ.trim();
    if (bootstrapInFlightRef.current === submittedQ) return;
    bootstrapInFlightRef.current = submittedQ;

    void (async () => {
      setBootstrapLoading(true);
      setError(null);
      try {
        const entry = planAnswerEntry(seedQ, false);
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
          analysisDepth: sessionFormat === "video" ? handoff.depth : undefined,
          sourceEntry: handoff.from ?? undefined,
        });

        if (!result.ok) {
          bootstrapInFlightRef.current = null;
          setFollowUp(submittedQ);
          // Session row already exists — failure is the primary SSE turn, not create.
          setError(pickAnswerErrorCode(result.error, "stream_failed"));
          return;
        }

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
                  : sessionFormat === "video" && handoff.depth === "deep"
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
        const nextParams = new URLSearchParams({ session: row.id, q: seedQ });
        nextParams.set("depth", handoff.depth);
        if (handoff.mode) nextParams.set("mode", handoff.mode);
        if (handoff.from) nextParams.set("from", handoff.from);
        setSearchParams(nextParams, { replace: true });
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
  }, [sessionId, seedQ, CLOUD, user, defaultProfileNicheId, handoff, setSearchParams, navigate, queryClient, uid, stream]);

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
          analysisDepth:
            suggestion.id === "video_deep" ? "deep" : handoff.depth,
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
      handoff.depth,
      handoff.mode,
      detailQuery.data?.session?.format,
    ],
  );

  const onRequestDeepAnalysis = useCallback(() => {
    const report = lastPayload?.kind === "video" ? lastPayload.report : null;
    const meta = report?.meta;
    const url = resolveVideoHandoffQuery({
      seedQ,
      sessionInitialQ: detailQuery.data?.session?.initial_q,
      videoId: report?.video_id,
      creatorHandle: typeof meta?.creator === "string" ? meta.creator : null,
    });
    if (!url) return;
    navigate(
      buildAnswerHandoffPath({
        q: url,
        depth: "deep",
        mode: handoff.mode ?? "win",
        ...(handoff.from ? { from: handoff.from } : {}),
      }),
      { replace: true },
    );
  }, [
    navigate,
    seedQ,
    handoff.mode,
    handoff.from,
    lastPayload,
    detailQuery.data?.session?.initial_q,
  ]);

  const handleIntentCta = useCallback(
    (suggestion: IntentCtaSuggestion, query: string) => {
      if (suggestion.action === "handoff") {
        if (suggestion.id === "video_deep") {
          onRequestDeepAnalysis();
          return;
        }
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
            depth: handoff.depth,
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
            depth: handoff.depth,
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
      onRequestDeepAnalysis,
    ],
  );

  const submitComposer = useCallback(() => {
    const q = followUp.trim();
    if (!q || !CLOUD || !user || bootstrapLoading || streamInFlight) return;
    if (!sessionId) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("q", q);
          next.set("depth", handoff.depth);
          return next;
        },
        { replace: true },
      );
      setFollowUp("");
      return;
    }
  }, [
    followUp,
    CLOUD,
    user,
    bootstrapLoading,
    streamInFlight,
    sessionId,
    handoff.depth,
    setSearchParams,
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
      depth: handoff.depth,
      videoQuery: resolveVideoHandoffQuery({
        seedQ,
        sessionInitialQ: detailQuery.data?.session?.initial_q,
        videoId: report?.video_id,
        creatorHandle: typeof meta?.creator === "string" ? meta.creator : null,
      }),
      scriptDraftId: scriptDraftIdFromTurns(turns),
      evidenceVideoQuery: evidenceVideoQueryFromPayload(lastPayload),
      sessionInitialQ: detailQuery.data?.session?.initial_q ?? null,
    };
  }, [
    detailQuery.data?.session?.format,
    detailQuery.data?.session?.initial_q,
    handoff.mode,
    handoff.depth,
    seedQ,
    lastPayload,
    turns,
  ]);

  const showIntentCtaRail = Boolean(
    sessionId && lastPayload && !loading && !streamInFlight && turnCount > 0,
  );

  return (
    <AppLayout active="answer" enableMobileSidebar>
      <div className="w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="Nghiên cứu"
          title="Báo Cáo Nghiên Cứu"
          right={
            <>
              <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/answer")}>
                <Plus className="h-3.5 w-3.5" strokeWidth={2} />
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
            ) : (
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
                  title={emptyStateHeroQuestion}
                >
                  {emptyStateHeroQuestion}
                </h1>
                {bootstrapLoading && seedQ.trim() ? (
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
                <p
                  className={
                    bootstrapLoading && seedQ.trim()
                      ? "sr-only"
                      : "mt-4 max-w-[640px] text-sm leading-relaxed text-[color:var(--gv-ink-3)]"
                  }
                >
                  Dán câu hỏi từ Studio hoặc mở phiên có sẵn từ Lịch sử — bạn cũng có thể sửa khung hỏi bên dưới để
                  bắt đầu phân tích mới.
                </p>
              </header>
            )
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
              {error ? (
                <p className="mt-4 text-sm text-[var(--gv-danger)]">
                  {analysisErrorCopy(error)}
                </p>
              ) : null}
              {detailQuery.isError && sessionId ? (
                <p className="mt-4 text-sm text-[var(--gv-danger)]">
                  {analysisErrorCopy(
                    pickAnswerErrorCode(detailQuery.error, "start_failed"),
                  )}
                </p>
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
                      onOpenScriptShoot={openScriptShoot}
                      sessionIntentType={sessionIntentType}
                      videoStreamProgress={
                        videoStreamProgress &&
                        t.payload.kind === "video" &&
                        idx === turns.length - 1
                          ? videoStreamProgress
                          : undefined
                      }
                      analysisDepth={handoff.depth}
                      showDeepUpsell={
                        t.payload.kind === "video" &&
                        idx === turns.length - 1 &&
                        !loading &&
                        handoff.depth === "basic"
                      }
                      lockedSections={
                        t.payload.kind === "video"
                          ? t.payload.report.locked_sections
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
              ) : sessionId && !loading ? (
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
                <IntentCtaRail
                  context={intentCtaContext}
                  disabled={!CLOUD || !user || bootstrapLoading || streamInFlight}
                  onCta={handleIntentCta}
                />
              ) : (
                <FollowUpComposer
                  value={followUp}
                  onChange={setFollowUp}
                  onSubmit={submitComposer}
                  variant="initial"
                  disabled={!CLOUD || !user || bootstrapLoading || streamInFlight}
                  analysisDepth={handoff.depth}
                  onAnalysisDepthChange={setAnalysisDepth}
                />
              )}
            </TimelineRail>
          }
        />
      </div>
    </AppLayout>
  );
}
