/**
 * VideoBody — video diagnosis report rendered as an answer-session body.
 *
 * This is the structured Win/Flop report (KPI strip + niche overlay +
 * hook phases + errors + narrative_vi)
 * lifted from ``src/routes/_app/video/VideoScreen.tsx``'s
 * ``VideoAnalysisBodyInner``. Visual design and behaviour match the
 * dedicated screen 1:1 — same components, same copy, same handlers.
 *
 * Receives ``report: VideoReportPayload`` from the answer-session
 * dispatcher (``ContinuationTurn`` / primary-turn renderer); does NOT
 * fetch its own data — that's the session payload's job, populated by
 * Cloud Run's /stream emit (PR-2 backend half).
 *
 * PR-2 ships dark — composer still redirects to /app/video, this body
 * doesn't render in production yet. PR-3 flips routing so the
 * ``video_diagnosis`` intent lands here and ``/app/video`` is removed.
 */
import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, Copy, Play } from "lucide-react";

import { SectionMini } from "@/components/SectionMini";
import { Btn } from "@/components/v2/Btn";
import { Timeline } from "@/components/v2/Timeline";
import { HookPhaseGrid } from "@/components/v2/HookPhaseCard";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { KpiGrid } from "@/components/v2/KpiGrid";
import { CommentRadarTile } from "@/routes/_app/components/CommentRadarTile";
import { ThumbnailTile } from "@/routes/_app/components/ThumbnailTile";
import { scriptPrefillFromVideo } from "@/lib/scriptPrefill";
import { logUsage } from "@/lib/logUsage";
import { r2FrameUrl } from "@/lib/services/corpus-service";
import { ContextStrip } from "@/components/v2/answer/video/blocks/ContextStrip";
import {
  CreatorComparisonCard,
  CreatorComparisonUnavailable,
} from "@/components/v2/answer/video/blocks/CreatorComparisonCard";
import { FlopIssueNarrativeRow } from "@/components/v2/answer/video/blocks/FlopIssueRow";
import { FlopDiagnosisStrip } from "@/components/v2/answer/video/blocks/FlopDiagnosisStrip";
import { CrossFormatPanel } from "@/components/v2/answer/video/blocks/CrossFormatPanel";
import { FormatCardsGrid } from "@/components/v2/answer/video/blocks/FormatCardsGrid";
import { PerformanceTierChip } from "@/components/v2/answer/video/blocks/PerformanceTierChip";
import {
  ChannelProofBlock,
  ChannelContextLegacy,
} from "@/components/v2/answer/video/blocks/ChannelProofBlock";
import { isV5Report } from "@/lib/v5-compat";
import type {
  BrightSpotSignal,
  ChannelContext,
  FormatCard,
  NarrativeVi,
  ReferenceVideoCard,
  VideoAnalyzeMeta,
  VideoAnalyzeMode,
  VideoReportPayload,
  VideoAnswerNarrativeReadyPayload,
  VideoAnswerPreSynthesisPayload,
  VideoFlopIssue,
  VideoLesson,
  ViewScenario,
} from "@/lib/api-types";

// Utility for building flop script handoff prompt — local to VideoBody
function formatViewsVi(n: number): string {
  return n.toLocaleString("vi-VN");
}

function retentionEndPct(curve: { t: number; pct: number }[] | null | undefined): number | null {
  if (!curve?.length) return null;
  return curve[curve.length - 1].pct;
}

/** Research handoff — ``AnswerScreen`` reads ``location.state.initialPrompt``. */
function buildFlopScriptHandoffPrompt(d: VideoReportPayload, watchUrl: string | null): string {
  const issues = d.errors ?? [];
  const lines = [
    `Corpus video_id: ${d.video_id}`,
    ...(watchUrl?.trim() ? [`Link TikTok đã soi: ${watchUrl.trim()}`] : []),
    "",
    "Mình vừa soi video flop trên Getviews — giúp mình lên shot-list / kịch bản, ưu tiên sửa các điểm sau:",
    ...issues.slice(0, 8).map((i) => `• ${i.title}\n  Fix gợi ý: ${i.fix}`),
  ];
  const headline = d.narrative_vi?.headline_vi?.trim();
  if (headline) lines.push("", `Chẩn đoán tổng: ${headline}`);
  return lines.join("\n");
}

export function VideoBody({
  report,
  preSynthesisData = null,
  channelContext = null,
  narrativeReady = null,
}: {
  report: VideoReportPayload;
  preSynthesisData?: VideoAnswerPreSynthesisPayload | null;
  channelContext?: ChannelContext | null;
  narrativeReady?: VideoAnswerNarrativeReadyPayload | null;
}) {
  const navigate = useNavigate();
  const meta = report.meta;
  const duration = meta.duration_sec || 58;
  const userCurve = report.retention_curve ?? [];
  const retEnd = retentionEndPct(userCurve);
  // ``mode`` lives on the report (BE single source of truth). VideoScreen
  // briefly distinguished a ``viewMode`` state during refetch; on the
  // answer surface the report is loaded once into the session payload,
  // so report.mode IS the view mode.
  const viewMode: VideoAnalyzeMode = report.mode ?? "win";
  const isFlop = viewMode === "flop";
  // Phase 4.4.6 — detect v5 BE response to opt into v5 layout paths.
  const isV5 = isV5Report(report as Record<string, unknown>);
  const preSynth = preSynthesisData ?? null;
  const narrativeVi: NarrativeVi | undefined =
    narrativeReady?.narrative_vi ?? report.narrative_vi;
  const formatCardsEffective: FormatCard[] | undefined =
    narrativeReady?.format_cards ?? report.format_cards;
  const refVideos: ReferenceVideoCard[] =
    preSynth?.reference_videos ?? report.reference_videos ?? [];
  const brightEffective: BrightSpotSignal | undefined =
    narrativeReady?.bright_spot_signal ??
    preSynth?.bright_spot_signal ??
    report.bright_spot_signal;
  const viewScenariosEffective: ViewScenario[] | undefined =
    narrativeReady?.view_scenarios ?? report.view_scenarios;
  const channelEffective: ChannelContext | undefined =
    channelContext ?? report.channel_context;
  // BE classifies each video into a refined tier (`hit | average | flop | unknown`)
  // by combining corpus benchmarks with channel context. Streamed during the
  // pre-synthesis SSE phase and persisted on the report; either source is
  // authoritative. Hidden when "unknown" (BE couldn't benchmark — don't make
  // up a verdict).
  const performanceTier: string | undefined =
    preSynth?.performance_tier ?? report.performance_tier;
  const streamedErrs = narrativeReady?.errors;
  const reportErrs = report.structural_errors ?? report.errors ?? [];
  // Phase 4.4.2 — cap to first 3 (highest severity) per v5 contract.
  const flopIssuesForNarrative: VideoFlopIssue[] = (
    streamedErrs && streamedErrs.length > 0 ? streamedErrs : reportErrs
  ).slice(0, 3);
  const winLessons: VideoLesson[] = (narrativeVi?.lessons ?? []).map((l) => ({
    title: l.title,
    body: l.body,
  }));
  const flopIssueCount = flopIssuesForNarrative.length;

  // Reconstruct the public TikTok URL from creator + video_id. On
  // ``/app/video`` the screen had access to the user's pasted ?url=
  // query; the answer surface doesn't, so we derive instead. Same shape
  // VideoScreen used for its play-button overlay.
  const tiktokWatchUrl = useMemo(() => {
    const raw = meta.creator?.trim() ?? "";
    if (!raw || !report.video_id) return null;
    const handle = raw.startsWith("@") ? raw.slice(1) : raw;
    if (!handle) return null;
    return `https://www.tiktok.com/@${handle}/video/${report.video_id}`;
  }, [meta.creator, report.video_id]);

  const thumbStats = useMemo(() => {
    const parts: string[] = [];
    if (meta.date_posted) parts.push(`Đăng ${meta.date_posted}`);
    parts.push(`${formatViewsVi(meta.views)} view`);
    if (meta.saves != null && meta.saves > 0) {
      parts.push(`${formatViewsVi(meta.saves)} save`);
    } else {
      parts.push(`save ${formatSaveRatePct(meta)}`);
    }
    if (meta.shares > 0) parts.push(`${formatViewsVi(meta.shares)} share`);
    return parts.join(" · ");
  }, [meta]);

  useEffect(() => {
    logUsage("video_body_load", {
      mode: viewMode,
      video_id: report.video_id,
      source: report.source ?? "corpus",
    });
  }, [viewMode, report.video_id, report.source]);

  const goScript = () => {
    if (isFlop) logUsage("flop_cta_click", { video_id: report.video_id });
    navigate("/app/answer", {
      state: { initialPrompt: buildFlopScriptHandoffPrompt(report, tiktokWatchUrl) },
    });
  };

  const goWinScript = () => {
    logUsage("video_to_script", { video_id: report.video_id, mode: "win" });
    const topic =
      meta.title?.trim() ||
      narrativeVi?.headline_vi?.trim() ||
      `Video từ @${meta.creator?.trim() || "creator"}`;
    const phases = report.hook_phases ?? [];
    const first = phases[0];
    const hookFromPhase = first ? first.label : null;
    const headlineHook = narrativeVi?.headline_vi?.trim() ?? "";
    navigate(
      scriptPrefillFromVideo({
        topic,
        hook: (hookFromPhase ?? headlineHook) || null,
        duration_sec: duration,
      }),
    );
  };

  const copyHook = async () => {
    const phases = report.hook_phases ?? [];
    const first = phases[0];
    const text = first
      ? `${first.t_range} · ${first.label}`
      : (narrativeVi?.headline_vi ?? "");
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard denied or unavailable */
    }
  };

  const showCommentRadarTile =
    report.comment_radar != null && report.comment_radar.sampled > 0;
  const showThumbnailTile = report.thumbnail_analysis != null;

  const applyLesson = (lesson: VideoLesson) => {
    navigate("/app/answer", {
      state: {
        initialPrompt: [
          `Corpus video_id: ${report.video_id}`,
          "",
          "Áp lesson từ video đang nổ trên Getviews:",
          `**${lesson.title}**`,
          lesson.body,
        ].join("\n"),
      },
    });
  };

  return (
    <div className="grid grid-cols-1 gap-8 min-[900px]:grid-cols-[320px_1fr]">
      {/* Stretch row height (grid default) so the sticky thumb has room; items-start + shrink-wrapped aside made sticky a no-op. */}
      <aside className="flex min-h-0 min-w-0 flex-col">
        {/*
          Sticky within the studio scrollport: follows the user down the report
          until the grid row ends (same height as the main column), then scrolls away.
          Only stick once the grid is two-column (>=900px). Below that the aside
          stacks above the body and a sticky 9/16 thumbnail pins a near-full-viewport
          poster over the scrolling report at mobile width (360–640px).
        */}
        <div className="space-y-3 self-start min-[900px]:sticky min-[900px]:top-20 lg:top-24">
          <div
            className="relative aspect-[9/16] overflow-hidden rounded-[18px] border-[8px] border-[color:var(--gv-ink)] shadow-[0_30px_60px_-30px_color-mix(in_srgb,var(--gv-ink)_34%,transparent)]"
            style={{
              backgroundImage: meta.thumbnail_url ? `url(${meta.thumbnail_url})` : undefined,
              backgroundColor: "var(--gv-canvas-2)",
              backgroundSize: "cover",
              backgroundPosition: "center",
            }}
          >
            {!isFlop && meta.is_breakout ? (
              <div className="pointer-events-none absolute left-3 top-3 z-[1]">
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-accent)] px-[7px] py-[3px] text-[10px] font-bold uppercase tracking-[0.05em] text-[color:var(--gv-paper)]">
                  BREAKOUT
                </span>
              </div>
            ) : null}
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[color:color-mix(in_srgb,var(--gv-ink)_55%,transparent)]" />
            {tiktokWatchUrl ? (
              <div className="pointer-events-none absolute inset-0 z-[2] flex items-center justify-center">
                <a
                  href={tiktokWatchUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="pointer-events-auto flex h-14 w-14 items-center justify-center rounded-full bg-[color:color-mix(in_srgb,var(--gv-paper)_24%,transparent)] text-[color:var(--gv-paper)] outline-none ring-offset-2 backdrop-blur-sm transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-[color:var(--gv-accent)]"
                  aria-label="Mở video trên TikTok"
                >
                  <Play className="ml-0.5 h-7 w-7" strokeWidth={1.35} aria-hidden />
                </a>
              </div>
            ) : null}
            <div className="pointer-events-none absolute bottom-4 left-3.5 right-3.5 text-[color:var(--gv-paper)]">
              <div className="gv-mono text-[11px] opacity-90">
                {atHandle(meta.creator)} · {Math.round(duration)}s
              </div>
              {meta.title ? (
                <p className="gv-tight mt-1 text-lg leading-tight">{meta.title}</p>
              ) : null}
            </div>
          </div>
          <p className="gv-mono text-center text-[11px] uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
            {thumbStats}
          </p>
        </div>
      </aside>

      <div className="flex flex-col gap-7">
        {!isFlop ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Btn variant="ghost" size="sm" type="button" onClick={() => void copyHook()}>
              <Copy className="h-3.5 w-3.5" strokeWidth={1.7} />
              Copy hook
            </Btn>
            <Btn variant="ink" size="sm" type="button" onClick={goWinScript}>
              Tạo kịch bản từ video này
            </Btn>
          </div>
        ) : null}
        <header>
          {isFlop ? (
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="gv-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-accent)]">
                {brightEffective?.signal_type === "hook_only_problem" ||
                (retEnd != null && retEnd >= 68)
                  ? `CHẨN ĐOÁN · ${flopIssueCount} ĐIỂM CẦN CHỈNH · GIỮ CHÂN ĐANG TỐT`
                  : `CHẨN ĐOÁN VIDEO CỦA BẠN · ${flopIssueCount} ĐIỂM LỖI CẤU TRÚC`}
              </span>
              <PerformanceTierChip tier={performanceTier} />
              {meta.content_format ? (
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-canvas-2)] px-[7px] py-[3px] text-[9px] capitalize tracking-[0.04em] text-[color:var(--gv-ink-3)]">
                  {meta.content_format.replace(/_/g, " ")}
                </span>
              ) : null}
            </div>
          ) : report.carousel_subformat_label ? (
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="gv-mono text-[9.5px] tracking-[0.18em] text-[color:var(--gv-ink-4)]">
                MỔ CAROUSEL VIRAL ·{" "}
                <span className="normal-case text-[color:var(--gv-ink-3)]">
                  {report.carousel_subformat_label}
                  {report.carousel_slide_count ? ` · ${report.carousel_slide_count} slides` : ""}
                </span>
                {" "}·{" "}
                <span className="normal-case text-[color:var(--gv-ink-3)]">
                  {meta.niche_label ?? "—"}
                </span>
              </span>
              <PerformanceTierChip tier={performanceTier} />
              {meta.content_format ? (
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-canvas-2)] px-[7px] py-[3px] text-[9px] capitalize tracking-[0.04em] text-[color:var(--gv-ink-3)]">
                  {meta.content_format.replace(/_/g, " ")}
                </span>
              ) : null}
            </div>
          ) : (
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="gv-mono text-[9.5px] tracking-[0.18em] text-[color:var(--gv-ink-4)]">
                MỔ VIDEO VIRAL ·{" "}
                <span className="normal-case text-[color:var(--gv-ink-3)]">
                  {meta.niche_label ?? "—"}
                </span>
              </span>
              <PerformanceTierChip tier={performanceTier} />
              {meta.content_format ? (
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-canvas-2)] px-[7px] py-[3px] text-[9px] capitalize tracking-[0.04em] text-[color:var(--gv-ink-3)]">
                  {meta.content_format.replace(/_/g, " ")}
                </span>
              ) : null}
            </div>
          )}
          <h1
            className={`m-0 max-w-[820px] text-[clamp(26px,3vw,36px)] text-[color:var(--gv-ink)] ${
              isFlop
                ? "gv-serif text-pretty font-medium leading-[1.25]"
                : "gv-tight font-semibold leading-[1.05] tracking-tight"
            }`}
          >
            {narrativeVi?.headline_vi?.trim() || "—"}
          </h1>
        </header>

        {isFlop ? (
          <FlopDiagnosisStrip
            meta={meta}
            nicheMeta={report.niche_meta}
            retentionEnd={retEnd}
          />
        ) : null}

        {narrativeVi?.ket_luan_nhanh ? (
          <section className="mb-4" aria-label="Kết luận nhanh">
            <p className="gv-mono mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
              Kết luận nhanh
            </p>
            <div className="rounded-[12px] bg-primary/10 px-4 py-3">
              <p className="max-w-[680px] leading-relaxed text-foreground">
                {narrativeVi.ket_luan_nhanh}
              </p>
            </div>
          </section>
        ) : null}

        {isFlop && viewScenariosEffective && viewScenariosEffective.length > 0 ? (
          <section className="mb-4" aria-label="Mức độ cải thiện có thể kỳ vọng">
            <p className="gv-mono mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
              Mức cải thiện lượt xem (ước lượng thận trọng)
            </p>
            <ol className="m-0 list-decimal space-y-2 pl-4 text-[13px] leading-snug text-[color:var(--gv-ink-2)]">
              {viewScenariosEffective.map((row, idx) => (
                <li key={`${idx}-${row.focus_vi.slice(0, 24)}`}>
                  <span className="font-medium text-foreground">{row.focus_vi}</span>
                  <span className="text-[color:var(--gv-ink-3)]"> — {row.outcome_vi}</span>
                </li>
              ))}
            </ol>
          </section>
        ) : null}

        <KpiGrid kpis={report.kpis} />

        {brightEffective ? (
          <div
            className="mb-4 rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-3 py-2.5"
            aria-label="Điểm sáng tín hiệu"
          >
            <p className="gv-mono mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
              Tín hiệu
            </p>
            <div className="flex items-start gap-2">
              <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-[color:var(--gv-accent)]" />
              <p className="text-[13px] leading-snug text-[color:var(--gv-ink-2)]">
                {brightEffective.message_vi}
              </p>
            </div>
          </div>
        ) : null}

        {narrativeVi?.van_de_chinh ? (
          <section className="mb-6">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Vấn đề chính
            </h3>
            <p className="max-w-[680px] leading-relaxed text-foreground">
              {narrativeVi.van_de_chinh}
            </p>
          </section>
        ) : null}

        {viewMode === "flop" && flopIssuesForNarrative.length > 0 ? (
          <section className="mb-6">
            <SectionMini kicker="" title="Lỗi cấu trúc · xếp theo ảnh hưởng" />
            <div className="flex flex-col gap-3">
              {flopIssuesForNarrative.map((issue, i) => {
                const narrativeItem = narrativeVi?.loi_chinh_narrative?.find(
                  (n) => n.error_id === issue.error_id,
                );
                return (
                  <FlopIssueNarrativeRow
                    key={issue.error_id ?? `${issue.title}-${i}`}
                    issue={issue}
                    narrativeItem={narrativeItem}
                    referenceVideos={refVideos}
                  />
                );
              })}
            </div>
            <div className="mt-4 flex justify-end">
              <Btn type="button" variant="accent" onClick={goScript}>
                Viết lại kịch bản
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
              </Btn>
            </div>
          </section>
        ) : null}

        {channelEffective?.available ? (
          isV5 ? (
            <ChannelProofBlock
              channelContext={channelEffective}
              analyzedFormat={meta.content_format ?? null}
            />
          ) : (
            <ChannelContextLegacy
              channelContext={channelEffective}
              metaTitle={meta.title}
              metaViews={meta.views}
            />
          )
        ) : null}

        {formatCardsEffective && formatCardsEffective.length > 0 ? (
          <FormatCardsGrid cards={formatCardsEffective} referenceVideos={refVideos} />
        ) : null}

        {report.cross_format_signal ? (
          <CrossFormatPanel signal={report.cross_format_signal} />
        ) : null}

        {narrativeVi?.dinh_huong_chien_luoc ? (
          <section className="mb-6 rounded-[14px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Cần làm gì khác
            </h3>
            <p className="max-w-[680px] leading-relaxed text-foreground">
              {narrativeVi.dinh_huong_chien_luoc}
            </p>
          </section>
        ) : null}

        {report.creator_comparison ? (
          <CreatorComparisonCard data={report.creator_comparison} />
        ) : report.meta?.creator ? (
          <CreatorComparisonUnavailable creator={report.meta.creator} />
        ) : null}

        {report.segments && report.segments.length > 0 ? (
          <Collapsible defaultOpen={false}>
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="gv-mono flex w-full items-center justify-between gap-2 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)] hover:text-[color:var(--gv-ink-3)]"
              >
                <span>Dòng thời gian · Cấu trúc {Math.round(duration)} giây</span>
                <span className="shrink-0 text-[11px] normal-case tracking-normal">▼ mở rộng</span>
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <section className="mt-3">
                <p className="mb-3 max-w-[680px] text-[12px] leading-relaxed text-[color:var(--gv-ink-2)]">
                  Phân tích đọc video qua các khung hình được lấy mẫu theo thời gian (nhận diện hình + cấu trúc cảnh), rồi gom
                  thành 8 nhịp kịch bản. Số % trên mỗi ô là phần thời lượng dành cho nhịp đó trong toàn clip — không
                  phải tỉ lệ khán giả còn xem. Trục giây bên dưới khớp độ dài video.
                </p>
                <Timeline segments={report.segments} durationSec={duration} />
              </section>
            </CollapsibleContent>
          </Collapsible>
        ) : null}

        {showCommentRadarTile || showThumbnailTile ? (
          <section aria-label="Thumbnail và bình luận">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {showCommentRadarTile && report.comment_radar ? (
                <CommentRadarTile data={report.comment_radar} />
              ) : null}
              {showThumbnailTile && report.thumbnail_analysis ? (
                <ThumbnailTile
                  data={report.thumbnail_analysis}
                  frameUrl={r2FrameUrl(report.video_id)}
                />
              ) : null}
            </div>
          </section>
        ) : null}

        {report.hook_phases?.length ? (
          <Collapsible defaultOpen={false}>
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="gv-mono flex w-full items-center justify-between gap-2 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)] hover:text-[color:var(--gv-ink-3)]"
              >
                <span>Giải mã hook · {isFlop ? "3 giây đầu dễ mất người xem" : "3 giây đầu vì sao người xem dừng"}</span>
                <span className="shrink-0 text-[11px] normal-case tracking-normal">▼ mở rộng</span>
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <section className="mt-3">
                <p className="mb-3 max-w-[680px] text-[12px] leading-relaxed text-[color:var(--gv-ink-2)]">
                  Ba thẻ theo cửa sổ 0–3s: hình mở, kiểu hook, chỗ lời/kết nối sớm — tóm tắt từ cùng luồng phân tích
                  hình (không phải lời thoại đầy đủ từng câu).
                </p>
                <HookPhaseGrid phases={report.hook_phases} />
              </section>
            </CollapsibleContent>
          </Collapsible>
        ) : null}

        <Collapsible defaultOpen={false}>
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="gv-mono flex w-full items-center justify-between gap-2 text-left text-[10px] font-semibold uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)] hover:text-[color:var(--gv-ink-3)]"
            >
              <span>Bối cảnh phân tích</span>
              <span className="shrink-0 text-[11px] normal-case tracking-normal">▼ mở rộng</span>
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ContextStrip meta={meta} enrichment={report.enrichment} />
          </CollapsibleContent>
        </Collapsible>

        {viewMode === "win" && winLessons.length ? (
          <section>
            <SectionMini kicker="Bài học áp dụng" title="3 điều bạn có thể copy" />
            <ul className="flex list-none flex-col gap-2.5 p-0">
              {winLessons.map((lesson, i) => (
                <li
                  key={`${lesson.title}-${i}`}
                  className="grid grid-cols-1 items-center gap-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3.5 sm:grid-cols-[40px_1fr_auto] sm:gap-4"
                >
                  <span className="gv-tight text-2xl text-[color:var(--gv-accent)]">
                    0{i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="gv-tight m-0 text-[17px] text-[color:var(--gv-ink)]">
                      {lesson.title}
                    </p>
                    <p className="mt-0.5 text-xs text-[color:var(--gv-ink-3)]">{lesson.body}</p>
                  </div>
                  <Btn
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="w-full justify-center sm:w-auto"
                    onClick={() => applyLesson(lesson)}
                  >
                    Áp dụng
                  </Btn>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}

