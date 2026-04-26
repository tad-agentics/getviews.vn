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
  useAnswerSessionsList,
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
import type { AnswerTurnRow, ReportV1, SourceRowData } from "@/lib/api-types";
import { logUsage } from "@/lib/logUsage";
import { Plus, Check, ArrowLeft, List, Bookmark } from "lucide-react";
import { ContinuationTurn } from "@/components/v2/answer/ContinuationTurn";
import { appendTurnKindForQuery, planAnswerEntry } from "@/routes/_app/intent-router";
import { AnswerShell } from "@/components/v2/answer/AnswerShell";
import { SessionDrawer } from "@/components/v2/answer/SessionDrawer";
import { FollowUpComposer } from "@/components/v2/answer/FollowUpComposer";
import { AnswerSourcesCard } from "@/components/v2/answer/AnswerSourcesCard";
import { TemplatizeCard } from "@/components/v2/answer/TemplatizeCard";
import {
  MiniResearchStrip,
  ResearchProcessBar,
  useResearchStage,
} from "@/components/v2/answer/ResearchStrip";
import { RelatedQsCard } from "@/components/v2/answer/RelatedQs";
import { TimelineRail } from "@/components/v2/answer/TimelineRail";
import { TopBar } from "@/components/v2/TopBar";
import { Btn } from "@/components/v2/Btn";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { surfaceStatsFromPayload } from "@/lib/reportSurfaceStats";

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

function pickAnswerErrorCode(e: unknown, fallback: string): string {
  if (e instanceof Error) {
    if (e.name === "SessionExpired") return "session_expired";
    if (e.name === "SessionNotFound") return "session_not_found";
    if (e.name === "FetchTimeout") return "stream_timeout";
    if (ANSWER_ERROR_CODES.has(e.message)) return e.message;
    if (e.message?.startsWith("http_")) return e.message;
  }
  if (typeof e === "string" && ANSWER_ERROR_CODES.has(e)) return e;
  return fallback;
}

function sourcesFromReport(p: ReportV1 | null): SourceRowData[] | undefined {
  if (!p) return undefined;
  return p.report.sources;
}

function relatedFromReport(p: ReportV1 | null): string[] {
  if (!p) return [];
  return p.report.related_questions ?? [];
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

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [followUp, setFollowUp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [bootstrapLoading, setBootstrapLoading] = useState(false);

  const uid = user?.id;
  const listQuery = useAnswerSessionsList(uid, Boolean(CLOUD && uid));
  const detailQuery = useAnswerSessionDetail(sessionId, uid);

  const { stream } = useSessionStream<ReportV1>({
    invalidateKeys: uid ? [answerSessionKeys.listsForUser(uid)] : [],
  });

  const nicheLabel = useMemo(() => {
    const id = profile?.primary_niche;
    if (id == null || !niches?.length) return undefined;
    const n = niches.find((row: { id: number; name: string }) => row.id === id);
    return n?.name;
  }, [profile?.primary_niche, niches]);

  const displayTitle = useMemo(() => {
    const t = detailQuery.data?.session?.title?.trim();
    if (t) return t;
    const iq = detailQuery.data?.session?.initial_q?.trim();
    if (iq) return iq.length > 120 ? `${iq.slice(0, 120)}…` : iq;
    if (sessionId && detailQuery.isLoading) return "Đang tải…";
    return "Phiên nghiên cứu";
  }, [detailQuery.data?.session, detailQuery.isLoading, sessionId]);

  const turns: AnswerTurnRow[] = detailQuery.data?.turns ?? [];

  const lastPayload = useMemo(() => lastPayloadFromTurns(turns), [turns]);

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

  const loading =
    bootstrapLoading ||
    (Boolean(sessionId) && detailQuery.isLoading && !detailQuery.data);

  const researchStage = useResearchStage(loading);
  const turnCount = turns.length;

  // Studio / video handoff: promote `location.state` into `?q=`
  useEffect(() => {
    const state = location.state as { initialPrompt?: string; prefillUrl?: string } | null | undefined;
    const incoming = state?.initialPrompt ?? state?.prefillUrl;
    if (!incoming || typeof incoming !== "string" || !incoming.trim()) return;
    navigate(`${location.pathname}?q=${encodeURIComponent(incoming)}`, { replace: true, state: {} });
  }, [location.state, location.pathname, navigate]);

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
            credits_used: pending.turnKind === "primary" ? 1 : 0,
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
    }
  }, [sessionId, seedQ]);

  useEffect(() => {
    if (sessionId || !seedQ.trim() || !CLOUD || !user) return;
    const q = seedQ.trim();
    if (bootstrapInFlightRef.current === q) return;
    bootstrapInFlightRef.current = q;

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
            niche_id: profile?.primary_niche ?? null,
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
        });

        if (!result.ok) {
          bootstrapInFlightRef.current = null;
          setError(pickAnswerErrorCode(result.error, "start_failed"));
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
            credits_used: 1,
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
        setSearchParams({ session: row.id, q: seedQ }, { replace: true });
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
        setError(pickAnswerErrorCode(e, "start_failed"));
      } finally {
        setBootstrapLoading(false);
      }
    })();
  }, [sessionId, seedQ, CLOUD, user, profile?.primary_niche, setSearchParams, navigate, queryClient, uid, stream]);

  const submitFollowUp = useCallback(async () => {
    const q = followUp.trim();
    if (!sessionId || !q || !CLOUD || !user) return;
    setBootstrapLoading(true);
    setError(null);
    try {
      const entry = planAnswerEntry(q, true);
      if (entry.kind === "redirect") {
        navigate(entry.to);
        setFollowUp("");
        return;
      }
      const turnKind = appendTurnKindForQuery(q, true);

      const result = await stream({
        mode: "answer_turn",
        answerSessionId: sessionId,
        query: q,
        turnKind,
      });
      if (!result.ok) {
        setError(pickAnswerErrorCode(result.error, "follow_up_failed"));
        return;
      }
      setFollowUp("");
      logUsage("answer_turn_append", {
        session_id: sessionId,
        kind: turnKind,
        intent_type: entry.intent_type,
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
          credits_used: 0,
          created_at: new Date().toISOString(),
        };
        queryClient.setQueryData<AnswerDetailCache>(
          answerSessionKeys.detail(sessionId),
          (prev) => {
            // Fallback session shape only used when cache is unexpectedly empty.
            const fallbackSession = prev?.session ?? {
              id: sessionId,
              user_id: user.id,
              title: null,
              initial_q: q,
              intent_type: entry.intent_type,
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
        console.error("[answer/follow_up] failed", e);
      }
      setError(pickAnswerErrorCode(e, "follow_up_failed"));
    } finally {
      setBootstrapLoading(false);
    }
  }, [sessionId, followUp, CLOUD, user, navigate, queryClient, uid, stream]);

  const openDrawer = useCallback(() => {
    setDrawerOpen(true);
    logUsage("answer_drawer_open", { session_id: sessionId });
  }, [sessionId]);

  const related = relatedFromReport(lastPayload);
  const sessions = listQuery.data?.sessions ?? [];

  return (
    <AppLayout active="answer" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="Nghiên cứu"
          title="Báo Cáo Nghiên Cứu"
          right={
            <>
              <span className="hide-narrow hidden items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.08em] text-[color:var(--gv-ink-3)] md:inline-flex">
                <span
                  className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--gv-accent)]"
                  style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
                />
                Dữ liệu cập nhật {dataFreshLabel ?? "—"}
              </span>
              <Btn variant="ghost" size="sm" type="button" disabled title="Sắp ra mắt">
                <Bookmark className="h-3.5 w-3.5" strokeWidth={2} />
                Đã lưu
              </Btn>
              <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/answer")}>
                <Plus className="h-3.5 w-3.5" strokeWidth={2} />
                Phân tích mới
              </Btn>
            </>
          }
        />
        <SessionDrawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sessions={sessions}
          activeSessionId={sessionId}
          onSelect={(id) => navigate(`/app/answer?session=${encodeURIComponent(id)}`)}
          onNewSession={() => navigate("/app/answer")}
          onViewAll={() => navigate("/app/history?filter=answer")}
          isLoading={listQuery.isLoading}
        />
        <AnswerShell
          crumb={
            <div className="mb-6 flex flex-col gap-3 border-b border-[color:var(--gv-rule)] pb-5 min-[720px]:flex-row min-[720px]:items-center min-[720px]:justify-between">
              <nav
                className="flex flex-wrap items-center gap-1.5 text-[color:var(--gv-ink-4)]"
                aria-label="Breadcrumb"
              >
                <button
                  type="button"
                  onClick={() => navigate("/app")}
                  className="inline-flex min-h-[30px] items-center gap-1 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-1 gv-mono text-[11px] font-medium leading-none tracking-[0.06em] text-[color:var(--gv-ink-3)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
                >
                  <ArrowLeft className="h-3 w-3 shrink-0" strokeWidth={2} aria-hidden />
                  Studio
                </button>
                <button
                  type="button"
                  onClick={openDrawer}
                  className="inline-flex min-h-[30px] items-center gap-1 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-1 gv-mono text-[11px] font-medium leading-none tracking-[0.06em] text-[color:var(--gv-ink-3)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
                >
                  <List className="h-3 w-3 shrink-0" strokeWidth={2} aria-hidden />
                  Phiên nghiên cứu · {sessions.length}
                </button>
                {nicheLabel ? (
                  <span className="gv-mono text-[11px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-3)]">
                    <span className="text-[color:var(--gv-rule)]" aria-hidden>
                      {" "}
                      /{" "}
                    </span>
                    Nghiên cứu · {nicheLabel}
                  </span>
                ) : null}
              </nav>
              {sessionId && surfaceStats && !loading ? (
                <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2 py-0.5 gv-mono text-[11px] tracking-[0.06em] text-[color:var(--gv-ink-3)]">
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
                  <p className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
                    Câu hỏi
                  </p>
                  {dataFreshLabel ? (
                    <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">{dataFreshLabel}</p>
                  ) : null}
                </div>
                <h1
                  className="gv-tight mt-0 max-w-[880px] text-[clamp(1.35rem,3.2vw,2.35rem)] leading-[1.15] tracking-[-0.03em] text-[color:var(--gv-ink)]"
                  style={{ fontFamily: "var(--gv-font-display)" }}
                >
                  {heroQuestion}
                </h1>
                {detailQuery.data?.session?.intent_type ? (
                  <p className="mt-2 gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
                    {detailQuery.data.session.format} · {detailQuery.data.session.intent_type}
                  </p>
                ) : null}
                <ResearchProcessBar
                  loading={loading}
                  stage={researchStage}
                  done={Boolean(!loading && lastPayload)}
                  videoCount={surfaceStats?.sampleVideos}
                  channelCount={
                    surfaceStats && surfaceStats.channelRows > 0 ? surfaceStats.channelRows : null
                  }
                />
                <MiniResearchStrip active={loading} />
              </header>
            ) : (
              <header className="border-b border-[color:var(--gv-rule)] pb-8">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <p className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
                    Câu hỏi
                  </p>
                  <p className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">—</p>
                </div>
                <h1
                  className="gv-tight mt-0 max-w-[880px] text-[clamp(1.35rem,3.2vw,2.35rem)] leading-[1.15] tracking-[-0.03em] text-[color:var(--gv-ink)]"
                  style={{ fontFamily: "var(--gv-font-display)" }}
                >
                  {emptyStateHeroQuestion}
                </h1>
                <p className="mt-4 max-w-[640px] text-sm leading-relaxed text-[color:var(--gv-ink-3)]">
                  Dán câu hỏi từ Studio hoặc mở phiên có sẵn từ Lịch sử — bạn cũng có thể sửa khung hỏi bên dưới để
                  bắt đầu phân tích mới.
                </p>
              </header>
            )
          }
          main={
            <TimelineRail turnCount={turnCount}>
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
              {loading ? (
                <p className="text-sm text-[var(--gv-ink-3)]">Đang tải báo cáo…</p>
              ) : turnCount > 0 ? (
                <div
                  className="space-y-10"
                  aria-live="polite"
                  aria-busy={loading}
                  aria-relevant="additions text"
                >
                  {turns.map((t) => (
                    <ContinuationTurn key={t.id} turn={t} />
                  ))}
                </div>
              ) : sessionId ? (
                <div className="mt-4 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
                  <p className="gv-serif text-[16px] leading-snug text-[color:var(--gv-ink)]">
                    Chưa có lượt trong phiên này.
                  </p>
                  <p className="mt-2 text-[12px] leading-relaxed text-[color:var(--gv-ink-3)]">
                    Nếu bạn vừa gửi câu hỏi, có thể báo cáo chưa kịp persist. Thử tải lại phiên
                    sau vài giây.
                  </p>
                  <button
                    type="button"
                    className="mt-3 gv-mono text-[11px] text-[color:var(--gv-accent)] underline"
                    onClick={() => void detailQuery.refetch()}
                  >
                    Tải lại phiên
                  </button>
                </div>
              ) : null}
              <FollowUpComposer
                value={followUp}
                onChange={setFollowUp}
                onSubmit={() => void submitFollowUp()}
                suggestedPrompts={related}
                disabled={!sessionId}
              />
            </TimelineRail>
          }
          aside={
            sessionId ? (
              <>
                <AnswerSourcesCard sources={sourcesFromReport(lastPayload)} />
                <RelatedQsCard items={related} onPick={setFollowUp} />
                <TemplatizeCard sessionId={sessionId} />
              </>
            ) : undefined
          }
        />
      </div>
    </AppLayout>
  );
}
