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
 * Cloud Run answer-turn payload (``build_video_report`` / ``finalize_video_narrative_layer``).
 *
 * PR-2 ships dark — composer still redirects to /app/video, this body
 * doesn't render in production yet. PR-3 flips routing so the
 * ``video_diagnosis`` intent lands here and ``/app/video`` is removed.
 */
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight } from "lucide-react";

import { SectionMini } from "@/components/SectionMini";
import { Btn } from "@/components/v2/Btn";
import { KpiGrid } from "@/components/v2/KpiGrid";
import { buildChannelStudioPath } from "@/lib/channelStudioHandoff";
import { contentFormatLabelVi } from "@/lib/contentFormatLabels";
import { logUsage } from "@/lib/logUsage";
import { r2VideoPlaybackUrl } from "@/lib/r2";
import { r2FrameUrl } from "@/lib/services/corpus-service";
import {
  DiagnosisSectionRenderer,
  type VideoDiagnosisSectionEmbeds,
} from "@/components/diagnosis/DiagnosisSectionRenderer";
import { CreatorComparisonCard } from "@/components/v2/answer/video/blocks/CreatorComparisonCard";
import { FlopDiagnosisStrip } from "@/components/v2/answer/video/blocks/FlopDiagnosisStrip";
import { BoostAttributionBlock } from "@/components/v2/answer/video/blocks/BoostAttributionBlock";
import { CarouselIntelStrip } from "@/components/v2/answer/video/blocks/CarouselIntelStrip";
import { shouldShowBoostAttributionBlock } from "@/lib/boostAttributionLabels";
import { mergeVideoStructureSections } from "@/lib/mergeVideoStructureSections";
import { resolveDiagnosisSections } from "@/lib/resolveDiagnosisSections";
import { FormatCardsGrid } from "@/components/v2/answer/video/blocks/FormatCardsGrid";
import { PerformanceTierChip } from "@/components/v2/answer/video/blocks/PerformanceTierChip";
import {
  ChannelProofBlock,
  ChannelContextLegacy,
  channelProofBlockHasData,
  channelContextLegacyHasData,
} from "@/components/v2/answer/video/blocks/ChannelProofBlock";
import { reconcileViewKpiWithTierRatio } from "@/lib/videoKpis";
import { isV5Report } from "@/lib/v5-compat";
import { resolveHookTimeline } from "@/lib/resolveHookTimeline";
import { buildCommentNextStepBullet } from "@/lib/commentNextSteps";
import { isReportPresentationV2 } from "@/lib/presentationV2";
import {
  maxFindingsForTier,
  tierIsGapHeavy,
  tierIsStrengthHeavy,
  tierImpliesWinFraming,
  videoReportWasModeCorrected,
} from "@/lib/videoReportCoherence";
import {
  adjunctSectionTitle,
  buildCreatorComparisonProse,
  buildHookAnalysisFallbackProse,
  buildMetadataFallbackProse,
  buildScriptStructureFallbackProse,
  diagnosisSectionText,
  shouldShowMetadataBlock,
  shouldShowScriptStructureBlock,
} from "@/lib/videoAdjunctSections";
import type {
  BrightSpotSignal,
  ChannelContext,
  FormatCard,
  NarrativeVi,
  ReferenceVideoCard,
  VideoAnalyzeMeta,
  VideoReportPayload,
  VideoAnswerNarrativeReadyPayload,
  VideoAnswerPreSynthesisPayload,
  VideoFlopIssue,
  VideoLesson,
  ViewScenario,
} from "@/lib/api-types";

// Utility for building flop script handoff prompt — local to VideoBody
function atHandle(raw: string | null | undefined): string {
  if (!raw) return "@—";
  const handle = raw.startsWith("@") ? raw : `@${raw}`;
  return handle;
}

function retentionEndPct(curve: { t: number; pct: number }[] | null | undefined): number | null {
  if (!curve?.length) return null;
  return curve[curve.length - 1].pct;
}

/**
 * "LÀM GÌ TIẾP THEO" — renders dinh_huong_chien_luoc as a bullet list.
 * The BE may return newline-delimited bullets (with or without leading "• ").
 * We split, strip leading bullet chars, and render as <ul>.
 */
function NextStepsSection({ text, extraBullets = [] }: { text: string; extraBullets?: string[] }) {
  const lines = text
    .split(/\n/)
    .map((l) => l.replace(/^[•\-\*]\s*/, "").trim())
    .filter(Boolean);
  const allLines = [...lines, ...extraBullets.filter(Boolean)];

  return (
    <section className="mb-6">
      <h3 className="gv-mono mb-3 text-[11px] font-semibold gv-kicker tracking-[0.18em] text-[color:var(--gv-ink-4)]">
        Làm gì tiếp theo
      </h3>
      {allLines.length === 0 ? null : allLines.length > 1 || extraBullets.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {allLines.map((line, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-[14px] leading-relaxed text-foreground"
            >
              <span
                className="mt-[5px] h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--gv-accent)]"
                aria-hidden
              />
              {line}
            </li>
          ))}
        </ul>
      ) : (
        <p className="max-w-[680px] text-[14px] leading-relaxed text-foreground">
          {allLines[0] ?? text}
        </p>
      )}
    </section>
  );
}

/** Research handoff — ``AnswerScreen`` reads ``location.state.initialPrompt``. */
function buildVideoScriptHandoffPrompt(
  d: VideoReportPayload,
  watchUrl: string | null,
  performanceTier: string | undefined,
): string {
  const issues = d.errors ?? [];
  const winFraming = tierImpliesWinFraming(performanceTier, d.meta);
  const lines = [
    `Mã video: ${d.video_id}`,
    ...(watchUrl?.trim() ? [`Link TikTok đã soi: ${watchUrl.trim()}`] : []),
    "",
    winFraming
      ? "Mình vừa soi video đang breakout trên GetViews — giúp mình lên shot-list / kịch bản video tiếp theo, ưu tiên tối ưu hook 3 giây đầu:"
      : "Mình vừa soi video yếu trên GetViews — giúp mình lên shot-list / kịch bản, ưu tiên sửa các điểm sau:",
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
  onRequestAppendTurn,
}: {
  report: VideoReportPayload;
  preSynthesisData?: VideoAnswerPreSynthesisPayload | null;
  channelContext?: ChannelContext | null;
  narrativeReady?: VideoAnswerNarrativeReadyPayload | null;
  /** Append a shot-list turn in the same answer session (format-card CTA). */
  onRequestAppendTurn?: (query: string) => void;
}) {
  const navigate = useNavigate();
  const meta = report.meta;
  const isForeignReup = meta.foreign_reup === true;
  const duration = meta.duration_sec || 58;
  const userCurve = report.retention_curve ?? [];
  const retEnd = retentionEndPct(userCurve);
  const preSynth = preSynthesisData ?? null;
  const performanceTier: string | undefined =
    preSynth?.performance_tier ?? report.performance_tier;
  const tierRatio: number | null | undefined = preSynth?.tier_ratio ?? report.tier_ratio;
  const tierBenchmarkN: number | null | undefined =
    preSynth?.tier_benchmark_n ?? report.tier_benchmark_n;
  const gapHeavy = tierIsGapHeavy(performanceTier);
  const strengthHeavy = tierIsStrengthHeavy(performanceTier);
  const modeCorrectedFromFlop = videoReportWasModeCorrected(
    report.mode,
    performanceTier,
    meta,
  );
  const isV5 = isV5Report(report as unknown as Record<string, unknown>);
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
  const leadFinding = narrativeVi?.diagnosis_vi?.lead_finding;
  const headerLeadCandidate =
    (isReportPresentationV2() &&
      (leadFinding?.body_vi?.trim() ||
        leadFinding?.title_vi?.trim() ||
        brightEffective?.message_vi?.trim())) ||
    null;
  // Drop the lead chip if it just echoes the headline (prompt forbids it, but
  // guard the UI so a model slip never renders the same line twice).
  const headerLeadText =
    headerLeadCandidate && headerLeadCandidate !== narrativeVi?.headline_vi?.trim()
      ? headerLeadCandidate
      : null;
  const viewScenariosEffective: ViewScenario[] | undefined =
    narrativeReady?.view_scenarios ?? report.view_scenarios;
  const channelEffective: ChannelContext | undefined =
    channelContext ?? report.channel_context;
  const streamedErrs = narrativeReady?.errors;
  const reportErrs = report.structural_errors ?? report.errors ?? [];
  // Phase 4.4.2 — cap to first 3 (highest severity) per v5 contract.
  const findingCap = maxFindingsForTier(performanceTier);
  const flopIssuesForNarrative: VideoFlopIssue[] = (
    streamedErrs && streamedErrs.length > 0 ? streamedErrs : reportErrs
  ).slice(0, findingCap);
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
    if (!report.video_id) return null;
    const raw = meta.creator?.trim() ?? "";
    if (raw) {
      const handle = raw.startsWith("@") ? raw.slice(1) : raw;
      if (handle) {
        return `https://www.tiktok.com/@${handle}/video/${report.video_id}`;
      }
    }
    // TikTok resolves /video/{id} without @handle — needed when corpus row is missing creator.
    return `https://www.tiktok.com/video/${report.video_id}`;
  }, [meta.creator, report.video_id]);

  const clipSrc = r2VideoPlaybackUrl(report.video_id) ?? "";
  const canHoverClip = Boolean(clipSrc);
  const previewVideoRef = useRef<HTMLVideoElement>(null);
  const [previewPlaying, setPreviewPlaying] = useState(false);

  const handlePreviewEnter = useCallback(() => {
    if (!canHoverClip) return;
    const el = previewVideoRef.current;
    if (!el) return;
    if (!el.getAttribute("src")) {
      el.src = clipSrc;
      el.load();
    }
    el.currentTime = 0;
    void el.play().then(() => setPreviewPlaying(true)).catch(() => {});
  }, [canHoverClip, clipSrc]);

  const handlePreviewLeave = useCallback(() => {
    const el = previewVideoRef.current;
    if (!el) return;
    el.pause();
    el.currentTime = 0;
    setPreviewPlaying(false);
  }, []);

  useEffect(() => {
    logUsage("video_body_load", {
      performance_tier: performanceTier ?? "unknown",
      video_id: report.video_id,
      source: report.source ?? "corpus",
    });
  }, [performanceTier, report.video_id, report.source]);

  const diagnosisSections = useMemo(() => {
    const merged = mergeVideoStructureSections(
      resolveDiagnosisSections(narrativeVi, flopIssuesForNarrative, performanceTier),
    );
    return merged.filter((s) => String(s.section_id) !== "next_video");
  }, [narrativeVi, flopIssuesForNarrative, performanceTier]);
  const sectionIds = new Set(diagnosisSections.map((s) => String(s.section_id)));
  const thumbnailEmbedSectionId = useMemo((): string | null => {
    if (!report.thumbnail_analysis) return null;
    if (sectionIds.has("hook_analysis")) return "hook_analysis";
    if (sectionIds.has("diagnosis")) return "diagnosis";
    return null;
  }, [report.thumbnail_analysis, diagnosisSections]);
  const hasChannelPattern = sectionIds.has("channel_pattern");
  const hasBoostAttribution = sectionIds.has("boost_attribution");
  const adjunctTier = (
    ["hit", "average", "flop", "unknown"] as const
  ).includes(performanceTier as "hit" | "average" | "flop" | "unknown")
    ? (performanceTier as "hit" | "average" | "flop" | "unknown")
    : gapHeavy
      ? "flop"
      : "hit";
  const creatorComparisonIntro = useMemo(() => {
    if (!report.creator_comparison || hasChannelPattern) return undefined;
    return buildCreatorComparisonProse(report.creator_comparison, meta.views ?? 0, gapHeavy);
  }, [report.creator_comparison, hasChannelPattern, meta.views, gapHeavy]);
  const commentRadar =
    report.comment_radar != null && report.comment_radar.sampled > 0
      ? report.comment_radar
      : null;
  const commentNextStepBullet =
    isReportPresentationV2() ? buildCommentNextStepBullet(commentRadar) : null;
  const hookTimelineEvents = resolveHookTimeline(report);
  const videoSectionEmbeds = useMemo((): VideoDiagnosisSectionEmbeds => {
    const embeds: VideoDiagnosisSectionEmbeds = {};
    if (shouldShowMetadataBlock(meta, report.enrichment, commentRadar)) {
      embeds.metadata = {
        meta,
        enrichment: report.enrichment,
        commentRadar,
        crossFormatSignal: report.cross_format_signal ?? null,
      };
    }
    embeds.crossFormatSignal = report.cross_format_signal ?? null;
    if (report.video_id) {
      embeds.analyzedClip = {
        videoId: report.video_id,
        clipUrl: r2VideoPlaybackUrl(report.video_id),
        durationSec: duration,
      };
    }
    if ((report.segments?.length ?? 0) > 0 && duration > 0) {
      embeds.structureTimeline = {
        segments: report.segments,
        durationSec: duration,
        retentionCurve:
          isReportPresentationV2() && userCurve.length > 0
            ? {
                userCurve,
                nicheCurve: report.niche_benchmark_curve,
                riskEvents: report.retention_risk_events ?? null,
              }
            : null,
      };
    }
    if (hookTimelineEvents.length > 0) {
      embeds.hookTimeline = hookTimelineEvents;
    }
    if (report.thumbnail_analysis) {
      embeds.thumbnailAnalysis = {
        data: report.thumbnail_analysis,
        frameUrl: report.video_id ? r2FrameUrl(report.video_id) : null,
      };
    }
    return embeds;
  }, [report, meta, duration, commentRadar, userCurve, hookTimelineEvents]);
  const showCarouselIntel = (report.carousel_intel?.slides?.length ?? 0) > 0;
  const showBoostFallback =
    !hasBoostAttribution &&
    shouldShowBoostAttributionBlock(meta.boost_attribution, meta.reference_eligible);

  const goScript = () => {
    if (gapHeavy) logUsage("flop_cta_click", { video_id: report.video_id });
    navigate("/app/answer", {
      state: {
        initialPrompt: buildVideoScriptHandoffPrompt(
          report,
          tiktokWatchUrl,
          performanceTier,
        ),
      },
    });
  };

  const goChannelStudio = () => {
    const raw = meta.creator?.trim();
    if (!raw) return;
    logUsage("video_to_channel", {
      video_id: report.video_id,
      performance_tier: performanceTier ?? "unknown",
    });
    navigate(
      buildChannelStudioPath({
        handle: raw,
        videoUrl: tiktokWatchUrl ?? undefined,
      }),
    );
  };

  const handleFormatScript = (card: FormatCard) => {
    if (!onRequestAppendTurn) return;
    const name = card.format_name_vi.trim();
    let q = `Tạo kịch bản theo định dạng "${name}" từ báo cáo video này.`;
    if (card.example_hook_vi?.trim()) {
      q += ` Hook gợi ý: ${card.example_hook_vi.trim()}`;
    }
    onRequestAppendTurn(q);
  };

  const overlayCaption =
    meta.caption?.trim() || meta.title?.trim() || "";

  const applyLesson = (lesson: VideoLesson) => {
    navigate("/app/answer", {
      state: {
        initialPrompt: [
          `Mã video: ${report.video_id}`,
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
        <div className="w-full min-w-0 shrink-0 space-y-3 self-start min-[900px]:sticky min-[900px]:top-20 lg:top-24">
          <div
            className="relative aspect-[9/16] w-full max-[899px]:max-h-[56vh] shrink-0 overflow-hidden rounded-[18px] border-[8px] border-[color:var(--gv-ink)] shadow-[0_30px_60px_-30px_color-mix(in_srgb,var(--gv-ink)_34%,transparent)] bg-[color:var(--gv-canvas-2)]"
            onMouseEnter={handlePreviewEnter}
            onMouseLeave={handlePreviewLeave}
          >
            {canHoverClip ? (
              <video
                ref={previewVideoRef}
                muted
                loop
                playsInline
                preload="none"
                className={`pointer-events-none absolute inset-0 z-[1] h-full w-full object-cover transition-opacity duration-300 ${previewPlaying ? "opacity-100" : "opacity-0"}`}
                aria-hidden
              />
            ) : null}
            <div
              className={`pointer-events-none absolute inset-0 z-[2] transition-opacity duration-300 ${previewPlaying && canHoverClip ? "opacity-0" : "opacity-100"}`}
              style={{
                backgroundImage: meta.thumbnail_url ? `url(${meta.thumbnail_url})` : undefined,
                backgroundColor: "var(--gv-canvas-2)",
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            />
            {!meta.thumbnail_url ? (
              <div className="pointer-events-none absolute inset-0 z-[3] flex items-center justify-center px-3">
                <span className="gv-mono text-center text-[11px] font-medium gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
                  Chưa có ảnh bìa
                </span>
              </div>
            ) : null}
            {!gapHeavy && meta.is_breakout ? (
              <div className="pointer-events-none absolute left-3 top-3 z-[4]">
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-accent)] px-[7px] py-[3px] text-[11px] font-bold uppercase tracking-[0.05em] text-white">
                  BREAKOUT
                </span>
              </div>
            ) : null}
            <div className="pointer-events-none absolute inset-0 z-[4] bg-gradient-to-b from-transparent via-transparent to-[color:color-mix(in_srgb,var(--gv-ink)_55%,transparent)]" />
            <div className="pointer-events-none absolute bottom-4 left-3.5 right-3.5 z-[4] text-[color:var(--gv-paper)]">
              <div className="gv-kicker opacity-90">
                {meta.creator?.trim() ? atHandle(meta.creator) : "Kênh chưa xác định"} ·{" "}
                {Math.round(duration)}s
              </div>
              {overlayCaption ? (
                <p className="gv-tight mt-1 line-clamp-2 text-lg leading-tight">
                  {overlayCaption}
                </p>
              ) : null}
            </div>
          </div>
          <p className="min-[900px]:hidden text-center gv-kicker text-[color:var(--gv-ink-3)]">
            Cuộn xuống để xem báo cáo
          </p>
        </div>
      </aside>

      <div className="flex flex-col gap-7">
        {modeCorrectedFromFlop ? (
          <p
            className="m-0 rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3 text-sm leading-relaxed text-[color:var(--gv-ink-2)]"
            role="status"
          >
            Video này đang breakout — GetViews hiển thị góc tối ưu tiếp theo, không phải chẩn
            đoán flop.
          </p>
        ) : null}
        {gapHeavy && (flopIssueCount > 0 || meta.creator?.trim()) ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            {meta.creator?.trim() ? (
              <Btn variant="ghost" size="sm" type="button" onClick={goChannelStudio}>
                Soi kênh {atHandle(meta.creator)}
              </Btn>
            ) : null}
            {flopIssueCount > 0 ? (
              <Btn type="button" variant="accent" size="sm" onClick={goScript}>
                Viết lại kịch bản
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
              </Btn>
            ) : null}
          </div>
        ) : null}
        <header>
          {report.carousel_subformat_label ? (
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="gv-kicker text-[color:var(--gv-ink-4)]">
                PHÂN TÍCH CAROUSEL ·{" "}
                <span className="normal-case text-[color:var(--gv-ink-3)]">
                  {report.carousel_subformat_label}
                  {report.carousel_slide_count ? ` · ${report.carousel_slide_count} slides` : ""}
                </span>
                {" "}·{" "}
                <span className="normal-case text-[color:var(--gv-ink-3)]">
                  {meta.niche_label ?? "—"}
                </span>
              </span>
              <PerformanceTierChip tier={performanceTier} ratio={tierRatio} benchmarkN={tierBenchmarkN} />
              {isForeignReup ? (
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-accent)]/12 px-[7px] py-[3px] text-[11px] tracking-[0.04em] text-[color:var(--gv-accent)]">
                  Reup nước ngoài
                </span>
              ) : null}
              {meta.content_format ? (
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-canvas-2)] px-[7px] py-[3px] text-[11px] tracking-[0.04em] text-[color:var(--gv-ink-3)]">
                  {contentFormatLabelVi(meta.content_format)}
                </span>
              ) : null}
            </div>
          ) : (
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="gv-kicker text-[color:var(--gv-ink-4)]">
                PHÂN TÍCH VIDEO ·{" "}
                <span className="normal-case text-[color:var(--gv-ink-3)]">
                  {meta.niche_label ?? "—"}
                </span>
              </span>
              <PerformanceTierChip tier={performanceTier} ratio={tierRatio} benchmarkN={tierBenchmarkN} />
              {isForeignReup ? (
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-accent)]/12 px-[7px] py-[3px] text-[11px] tracking-[0.04em] text-[color:var(--gv-accent)]">
                  Reup nước ngoài
                </span>
              ) : null}
              {meta.content_format ? (
                <span className="gv-mono rounded-[3px] bg-[color:var(--gv-canvas-2)] px-[7px] py-[3px] text-[11px] tracking-[0.04em] text-[color:var(--gv-ink-3)]">
                  {contentFormatLabelVi(meta.content_format)}
                </span>
              ) : null}
            </div>
          )}
          <h1 className="gv-tight m-0 max-w-[820px] text-[clamp(26px,3vw,36px)] font-semibold leading-[1.05] tracking-tight text-[color:var(--gv-ink)]">
            {narrativeVi?.headline_vi?.trim() || "—"}
          </h1>
          {headerLeadText ? (
            <p
              className="mt-3 max-w-[680px] rounded-md border border-[color:var(--gv-accent)]/25 bg-[color:var(--gv-accent)]/8 px-3 py-2.5 text-sm font-medium leading-snug text-[color:var(--gv-ink)]"
              role="status"
            >
              {headerLeadText}
            </p>
          ) : null}
        </header>

        {gapHeavy && viewScenariosEffective && viewScenariosEffective.length > 0 ? (
          <section className="mb-4" aria-label="Mức độ cải thiện có thể kỳ vọng">
            <p className="gv-mono mb-2 text-[11px] font-semibold gv-kicker tracking-[0.18em] text-[color:var(--gv-ink-3)]">
              Mức cải thiện lượt xem (ước lượng thận trọng)
            </p>
            <ol className="m-0 list-decimal space-y-2 pl-4 text-sm leading-snug text-[color:var(--gv-ink-2)]">
              {viewScenariosEffective.map((row, idx) => (
                <li key={`${idx}-${row.focus_vi.slice(0, 24)}`}>
                  <span className="font-medium text-foreground">{row.focus_vi}</span>
                  <span className="text-[color:var(--gv-ink-3)]"> — {row.outcome_vi}</span>
                </li>
              ))}
            </ol>
          </section>
        ) : null}

        {/* One source of truth for the view ratio: tier_ratio (the chip's
            number) overrides the KPI's own niche computation when present
            — chip "0.7× TB FORMAT" vs KPI "0.6× ngách" was a live bug. */}
        <KpiGrid kpis={reconcileViewKpiWithTierRatio(report.kpis, tierRatio)} />

        {gapHeavy ? (
          <FlopDiagnosisStrip
            meta={meta}
            nicheMeta={report.niche_meta ?? null}
            retentionEnd={retEnd}
            isCarousel={Boolean(report.carousel_subformat_label)}
          />
        ) : null}

        {diagnosisSections.length > 0 ? (
          <div className="mb-6" aria-label="Chẩn đoán theo mục">
            {diagnosisSections.map((sec, idx) => {
              const sid = String(sec.section_id);
              const sectionProse = diagnosisSectionText(sec);
              return (
                <Fragment key={`${sid}-${idx}`}>
                  <DiagnosisSectionRenderer
                    section={sec}
                    referenceVideos={refVideos}
                    analyzedContentFormat={meta.content_format ?? null}
                    evidenceAnchors={narrativeVi?.diagnosis_vi?.evidence_anchors}
                    embedThumbnailSupport={sid === thumbnailEmbedSectionId}
                    creatorComparison={
                      sid === "channel_pattern" ? report.creator_comparison ?? null : undefined
                    }
                    channelPatternEmbed={
                      sid === "channel_pattern" && channelEffective?.available
                        ? {
                            channelContext: channelEffective,
                            analyzedFormat: meta.content_format ?? null,
                            creatorHandle: meta.creator ?? null,
                            metaTitle: meta.title,
                            metaViews: meta.views,
                            isV5,
                          }
                        : undefined
                    }
                    videoEmbeds={videoSectionEmbeds}
                    fallbackProse={
                      sectionProse
                        ? undefined
                        : sid === "script_structure"
                          ? buildScriptStructureFallbackProse(duration)
                          : sid === "hook_analysis"
                            ? buildHookAnalysisFallbackProse(
                                report.hook_phases,
                                gapHeavy,
                                narrativeVi,
                                flopIssuesForNarrative,
                              )
                            : sid === "metadata"
                              ? buildMetadataFallbackProse(meta)
                              : undefined
                    }
                  />
                  {sid === "boost_attribution" ? (
                    <BoostAttributionBlock
                      attribution={meta.boost_attribution}
                      referenceEligible={meta.reference_eligible}
                      findings={sec.findings}
                    />
                  ) : null}
                </Fragment>
              );
            })}
          </div>
        ) : null}

        {showBoostFallback ? (
          <BoostAttributionBlock
            attribution={meta.boost_attribution}
            referenceEligible={meta.reference_eligible}
          />
        ) : null}

        {showCarouselIntel ? (
          <CarouselIntelStrip intel={report.carousel_intel} />
        ) : null}

        {diagnosisSections.length > 0 && !hasChannelPattern && report.creator_comparison ? (
          <CreatorComparisonCard
            data={report.creator_comparison}
            introProse={creatorComparisonIntro}
          />
        ) : null}

        {/* Standalone channel block: shown when channel data is available but
            channel_pattern didn't emit as a v6 section (sample_size < 2).
            Add a brief intro so the cards aren't orphaned without context.
            Hidden entirely when the proof block itself would render nothing —
            a heading + boilerplate explainer with no comparison data was a
            live bug (2026-06-12 audit). */}
        {channelEffective?.available &&
        !hasChannelPattern &&
        !report.creator_comparison &&
        (isV5
          ? channelProofBlockHasData(channelEffective)
          : channelContextLegacyHasData(channelEffective)) ? (
          <div className="mb-6">
            <h3 className="mb-2 text-base font-bold leading-snug text-[color:var(--foreground)]">
              Video này so với kênh bạn
            </h3>
            <p className="mb-3 max-w-[680px] text-[14px] leading-relaxed text-[color:var(--gv-ink-2)]">
              Video này so với các video khác trên cùng kênh — video có lượt xem cao nhất cho thấy
              format và hook đang hoạt động tốt; video thấp nhất chỉ ra điểm yếu lặp lại.
            </p>
            {isV5 ? (
              <ChannelProofBlock
                channelContext={channelEffective}
                analyzedFormat={meta.content_format ?? null}
                creatorHandle={meta.creator ?? null}
              />
            ) : (
              <ChannelContextLegacy
                channelContext={channelEffective}
                metaTitle={meta.title}
                metaViews={meta.views}
              />
            )}
          </div>
        ) : null}

        {formatCardsEffective && formatCardsEffective.length > 0 ? (
          <FormatCardsGrid
            cards={formatCardsEffective}
            referenceVideos={refVideos}
            onCreateScriptFromFormat={onRequestAppendTurn ? handleFormatScript : undefined}
          />
        ) : null}

        {narrativeVi?.dinh_huong_chien_luoc ? (
          <NextStepsSection
            text={narrativeVi.dinh_huong_chien_luoc}
            extraBullets={commentNextStepBullet ? [commentNextStepBullet] : []}
          />
        ) : commentNextStepBullet ? (
          <NextStepsSection text="" extraBullets={[commentNextStepBullet]} />
        ) : null}

        {!sectionIds.has("script_structure") && shouldShowScriptStructureBlock(report) ? (
          <DiagnosisSectionRenderer
            section={{
              section_id: "script_structure",
              title: adjunctSectionTitle("script_structure", undefined, adjunctTier),
              title_vi: adjunctSectionTitle("script_structure", undefined, adjunctTier),
              text: "",
              findings: [],
            }}
            referenceVideos={refVideos}
            videoEmbeds={videoSectionEmbeds}
            fallbackProse={buildScriptStructureFallbackProse(duration)}
          />
        ) : null}

        {!sectionIds.has("metadata") && shouldShowMetadataBlock(meta, report.enrichment, commentRadar) ? (
          <DiagnosisSectionRenderer
            section={{
              section_id: "metadata",
              title: adjunctSectionTitle("metadata", undefined, adjunctTier),
              title_vi: adjunctSectionTitle("metadata", undefined, adjunctTier),
              text: "",
              findings: [],
            }}
            referenceVideos={refVideos}
            videoEmbeds={videoSectionEmbeds}
            fallbackProse={buildMetadataFallbackProse(meta)}
          />
        ) : null}

        {strengthHeavy && winLessons.length ? (
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

