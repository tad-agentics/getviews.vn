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
  lastPayloadFromTurns,
  useAnswerSessionDetail,
  useAnswerSessionsList,
} from "@/hooks/useAnswerSessionQueries";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import type { ReportV1, SourceRowData } from "@/lib/api-types";
import { logUsage } from "@/lib/logUsage";
import { PatternBody } from "@/components/v2/answer/pattern/PatternBody";
import { appendTurnKindForQuery, planAnswerEntry } from "@/routes/_app/intent-router";
import { AnswerShell } from "@/components/v2/answer/AnswerShell";
import { QueryHeader } from "@/components/v2/answer/QueryHeader";
import { SessionDrawer } from "@/components/v2/answer/SessionDrawer";
import { FollowUpComposer } from "@/components/v2/answer/FollowUpComposer";
import { AnswerSourcesCard } from "@/components/v2/answer/AnswerSourcesCard";
import { TemplatizeCard } from "@/components/v2/answer/TemplatizeCard";
import {
  MiniResearchStrip,
  ProgressPill,
  ResearchStepStrip,
  useResearchStage,
} from "@/components/v2/answer/ResearchStrip";
import { RelatedQs } from "@/components/v2/answer/RelatedQs";
import { TimelineRail } from "@/components/v2/answer/TimelineRail";

const CLOUD = env.VITE_CLOUD_RUN_API_URL;

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

  const lastPayload = useMemo(
    () => lastPayloadFromTurns(detailQuery.data?.turns),
    [detailQuery.data?.turns],
  );

  const loading =
    bootstrapLoading ||
    (Boolean(sessionId) && detailQuery.isLoading && !detailQuery.data);

  const researchStage = useResearchStage(loading);
  const turnCount = detailQuery.data?.turns?.length ?? 0;

  // Studio / video handoff: promote `location.state` into `?q=`
  useEffect(() => {
    const state = location.state as { initialPrompt?: string; prefillUrl?: string } | null | undefined;
    const incoming = state?.initialPrompt ?? state?.prefillUrl;
    if (!incoming || typeof incoming !== "string" || !incoming.trim()) return;
    navigate(`${location.pathname}?q=${encodeURIComponent(incoming)}`, { replace: true, state: {} });
  }, [location.state, location.pathname, navigate]);

  const startedRef = useRef(false);
  useEffect(() => {
    if (sessionId || !seedQ.trim() || !CLOUD || !user || startedRef.current) return;
    startedRef.current = true;
    void (async () => {
      setBootstrapLoading(true);
      setError(null);
      try {
        const entry = planAnswerEntry(seedQ, false);
        if (entry.kind === "redirect") {
          navigate(entry.to, { replace: true });
          return;
        }
        const { format: sessionFormat, intent_type: sessionIntent } = entry;

        const { data: { session } } = await supabase.auth.getSession();
        if (!session) throw new Error("auth");
        const res = await fetch(`${CLOUD}/answer/sessions`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
            "Idempotency-Key": crypto.randomUUID(),
          },
          body: JSON.stringify({
            initial_q: seedQ,
            intent_type: sessionIntent,
            niche_id: profile?.primary_niche ?? null,
            format: sessionFormat,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const row = (await res.json()) as { id: string };
        logUsage("answer_session_create", {
          session_id: row.id,
          format: sessionFormat,
          intent_type: sessionIntent,
        });
        const turnRes = await fetch(`${CLOUD}/answer/sessions/${row.id}/turns`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ query: seedQ, kind: "primary" }),
        });
        if (!turnRes.ok) {
          if (turnRes.status === 402) setError("insufficient_credits");
          else throw new Error(`HTTP ${turnRes.status}`);
        }
        await turnRes.json();
        logUsage("answer_turn_append", { session_id: row.id, kind: "primary" });
        setSearchParams({ session: row.id, q: seedQ }, { replace: true });
        if (uid) {
          await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
          await queryClient.invalidateQueries({ queryKey: answerSessionKeys.detail(row.id) });
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "start_failed");
      } finally {
        setBootstrapLoading(false);
      }
    })();
  }, [sessionId, seedQ, CLOUD, user, profile?.primary_niche, setSearchParams, navigate, queryClient, uid]);

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

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error("auth");
      const turnRes = await fetch(`${CLOUD}/answer/sessions/${sessionId}/turns`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: q, kind: turnKind }),
      });
      if (!turnRes.ok) {
        if (turnRes.status === 402) setError("insufficient_credits");
        else throw new Error(`HTTP ${turnRes.status}`);
      }
      await turnRes.json();
      setFollowUp("");
      logUsage("answer_turn_append", {
        session_id: sessionId,
        kind: turnKind,
        intent_type: entry.intent_type,
      });
      if (uid) {
        await queryClient.invalidateQueries({ queryKey: answerSessionKeys.detail(sessionId) });
        await queryClient.invalidateQueries({ queryKey: answerSessionKeys.listsForUser(uid) });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "follow_up_failed");
    } finally {
      setBootstrapLoading(false);
    }
  }, [sessionId, followUp, CLOUD, user, navigate, queryClient, uid]);

  const openDrawer = useCallback(() => {
    setDrawerOpen(true);
    logUsage("answer_drawer_open", { session_id: sessionId });
  }, [sessionId]);

  const reportBody = (() => {
    if (!lastPayload) return null;
    if (lastPayload.kind === "pattern") {
      return (
        <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
            Pattern
          </p>
          <div className="mt-4">
            <PatternBody report={lastPayload.report} />
          </div>
        </div>
      );
    }
    if (lastPayload.kind === "ideas") {
      return (
        <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
            Ideas
          </p>
          <p className="mt-4 text-sm text-[color:var(--gv-ink-2)]">{lastPayload.report.lead}</p>
        </div>
      );
    }
    if (lastPayload.kind === "timing") {
      const tw = lastPayload.report.top_window as Record<string, unknown>;
      const label = [tw.day, tw.hours].filter(Boolean).join(" · ");
      return (
        <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
            Timing
          </p>
          <p className="mt-4 text-sm text-[color:var(--gv-ink-2)]">{label || "Khung giờ gợi ý"}</p>
        </div>
      );
    }
    const paras = (lastPayload.report.narrative as { paragraphs?: string[] } | undefined)?.paragraphs;
    const text =
      Array.isArray(paras) && paras.length > 0
        ? paras.join("\n\n")
        : "Báo cáo tổng quát (generic).";
    return (
      <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
        <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
          Tổng quát
        </p>
        <p className="mt-4 whitespace-pre-wrap text-sm text-[color:var(--gv-ink-2)]">{text}</p>
      </div>
    );
  })();

  const related = relatedFromReport(lastPayload);
  const sessions = listQuery.data?.sessions ?? [];

  return (
    <AppLayout active="answer" enableMobileSidebar>
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
          <div className="mb-6 flex flex-wrap items-center gap-2 text-[12px] text-[var(--gv-ink-4)]">
            <button
              type="button"
              onClick={() => navigate("/app")}
              className="chip inline-flex items-center gap-1 rounded-md border border-[var(--gv-rule)] px-2 py-1 font-mono"
            >
              ← Studio
            </button>
            <button
              type="button"
              onClick={openDrawer}
              className="chip inline-flex items-center gap-1 rounded-md border border-[var(--gv-rule)] px-2 py-1 font-mono hover:bg-[var(--gv-canvas-2)]"
            >
              Phiên nghiên cứu · {sessions.length}
            </button>
            {nicheLabel ? (
              <span className="font-mono uppercase tracking-wide text-[var(--gv-ink-4)]">
                · {nicheLabel}
              </span>
            ) : null}
          </div>
        }
        header={
          <QueryHeader
            title={displayTitle}
            meta={
              sessionId ? (
                <span>
                  {detailQuery.data?.session?.format ?? ""}
                  {detailQuery.data?.session?.intent_type
                    ? ` · ${detailQuery.data.session.intent_type}`
                    : ""}
                </span>
              ) : null
            }
          >
            {sessionId ? (
              <>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <ProgressPill loading={loading} stepIndex={researchStage} />
                </div>
                <ResearchStepStrip
                  stage={researchStage}
                  done={Boolean(!loading && lastPayload)}
                />
                <MiniResearchStrip active={loading} />
              </>
            ) : null}
          </QueryHeader>
        }
        main={
          <TimelineRail turnCount={turnCount}>
            {error ? (
              <p className="mt-4 text-sm text-[var(--gv-danger)]">{error}</p>
            ) : null}
            {detailQuery.isError && sessionId ? (
              <p className="mt-4 text-sm text-[var(--gv-danger)]">
                Không tải được phiên — thử mở lại từ Lịch sử hoặc phiên mới.
              </p>
            ) : null}
            {loading ? (
              <p className="text-sm text-[var(--gv-ink-3)]">Đang tải báo cáo…</p>
            ) : reportBody ? (
              reportBody
            ) : (
              <p className="text-sm text-[var(--gv-ink-3)]">
                Dán câu hỏi từ Studio hoặc mở phiên có sẵn từ Lịch sử.
              </p>
            )}
            <RelatedQs items={related} onPick={setFollowUp} />
            <FollowUpComposer
              value={followUp}
              onChange={setFollowUp}
              onSubmit={() => void submitFollowUp()}
              nicheLabel={nicheLabel}
              disabled={!sessionId}
            />
          </TimelineRail>
        }
        aside={
          <>
            <AnswerSourcesCard sources={sourcesFromReport(lastPayload)} />
            <TemplatizeCard sessionId={sessionId} />
          </>
        }
      />
    </AppLayout>
  );
}
