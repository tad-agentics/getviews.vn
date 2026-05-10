/**
 * VideoBody — video diagnosis report rendered as an answer-session body.
 *
 * This is the structured Win/Flop report (KPI strip + retention curve +
 * niche overlay + hook phases + lessons + flop_issues + projected views)
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
import { RetentionCurve } from "@/components/v2/RetentionCurve";
import { Timeline } from "@/components/v2/Timeline";
import { HookPhaseGrid } from "@/components/v2/HookPhaseCard";
import { KpiGrid } from "@/components/v2/KpiGrid";
import { IssueCard } from "@/components/v2/IssueCard";
import { CommentRadarTile } from "@/routes/_app/components/CommentRadarTile";
import { ThumbnailTile } from "@/routes/_app/components/ThumbnailTile";
import { sanitizePredictionPos } from "@/lib/sanitizePredictionPos";
import { scriptPrefillFromVideo } from "@/lib/scriptPrefill";
import { logUsage } from "@/lib/logUsage";
import { r2FrameUrl } from "@/lib/services/corpus-service";
import type {
  CreatorComparison,
  FlopHeadline,
  VideoAnalyzeMeta,
  VideoAnalyzeMode,
  VideoAnalyzeResponse,
  VideoEnrichment,
  VideoLesson,
  VideoNicheMeta,
  VideoReportPayload,
} from "@/lib/api-types";

// Matches CLAIM_TIERS.pattern_spread — UI only, do not import tiers.
const WINNERS_CLAIM_MIN = 10;

function formatViewsVi(n: number): string {
  return n.toLocaleString("vi-VN");
}

function isFlopHeadline(v: string | FlopHeadline | null | undefined): v is FlopHeadline {
  return v != null && typeof v === "object" && "prefix" in v && "view_accent" in v;
}

function stringifyAnalysisHeadline(h: string | FlopHeadline | null | undefined): string {
  if (h == null) return "";
  if (typeof h === "string") return h;
  return `${h.prefix}${h.view_accent}${h.middle}${sanitizePredictionPos(h.prediction_pos)}${h.suffix}`;
}

/**
 * Soft fallback rendered when the BE knows the creator handle but
 * couldn't build a hit/flop comparison (creator has insufficient
 * post history, EnsembleData returned only zero-view fresh posts,
 * etc.). Replaces the previous silent omission so the user sees
 * "we tried but couldn't" rather than the card vanishing.
 */
const PROMOTION_LABEL_VI: Record<NonNullable<VideoEnrichment["promotion_type"]>, string> = {
  organic: "Tự sản xuất",
  brand_deal: "Đặt hàng nhãn",
  affiliate: "Affiliate",
  self_promotion: "Tự quảng bá",
};

function ContextStrip({
  meta,
  enrichment,
}: {
  meta: VideoAnalyzeMeta;
  enrichment?: VideoEnrichment | null;
}) {
  const ratio = meta.target_vs_creator_median ?? null;
  const median = meta.creator_median_views ?? null;
  const hasRatio = ratio != null && median != null && median > 0;
  const audience = enrichment?.target_audience?.trim() ?? "";
  const painPoints = (enrichment?.pain_points ?? []).filter((p) => p.trim().length > 0);
  const styleTags = (enrichment?.style_tags ?? []).filter((s) => s.trim().length > 0);
  const promotion = enrichment?.promotion_type ?? "organic";
  const showPromotion = promotion !== "organic";

  if (!hasRatio && !audience && painPoints.length === 0 && styleTags.length === 0 && !showPromotion) {
    return null;
  }

  return (
    <section
      aria-label="Bối cảnh phân tích"
      className="mt-6 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4"
    >
      <p className="gv-mono mb-3 text-[10px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
        BỐI CẢNH PHÂN TÍCH
      </p>
      <div className="grid grid-cols-1 gap-3 min-[700px]:grid-cols-2">
        {hasRatio ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              SO VỚI KÊNH BẠN
            </p>
            <p className="gv-mono m-0 text-[18px] font-semibold text-[color:var(--gv-ink)]">
              {ratio!.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}× kênh trung bình
            </p>
            <p className="m-0 text-[11.5px] text-[color:var(--gv-ink-3)]">
              Trung vị {median!.toLocaleString("vi-VN")} view trên các bài gần đây
            </p>
          </div>
        ) : null}
        {audience ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              NHẮM TỚI
            </p>
            <p className="m-0 text-[13px] leading-relaxed text-[color:var(--gv-ink)]">
              {audience}
            </p>
          </div>
        ) : null}
        {painPoints.length > 0 ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              ĐIỂM NHẠY KHAI THÁC
            </p>
            <ul className="m-0 list-disc pl-4 text-[12.5px] leading-relaxed text-[color:var(--gv-ink-2)]">
              {painPoints.slice(0, 3).map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {styleTags.length > 0 || showPromotion ? (
          <div>
            <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[color:var(--gv-ink-4)]">
              KIỂU SẢN XUẤT
            </p>
            <div className="flex flex-wrap gap-1.5">
              {showPromotion ? (
                <span className="rounded-full border border-[color:var(--gv-accent)] bg-[color:var(--gv-canvas)] px-2 py-0.5 text-[11px] text-[color:var(--gv-accent)]">
                  {PROMOTION_LABEL_VI[promotion]}
                </span>
              ) : null}
              {styleTags.slice(0, 5).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-2 py-0.5 text-[11px] text-[color:var(--gv-ink-2)]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function CreatorComparisonUnavailable({ creator }: { creator: string }) {
  const at = creator.startsWith("@") ? creator : `@${creator}`;
  return (
    <div className="mt-6 rounded-xl border border-dashed border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] p-4 text-[12.5px] text-[var(--gv-ink-3)]">
      <p className="gv-mono mb-1 text-[10px] uppercase tracking-wider text-[var(--gv-ink-3)]">
        SO SÁNH TRONG KÊNH · {at}
      </p>
      <p className="m-0 leading-relaxed">
        Chưa đủ video gần nhất của creator để so sánh hit/flop.
        {" "}Cần tối thiểu 2 video có lượng view rõ ràng để dựng được
        cặp đối chiếu.
      </p>
    </div>
  );
}

function CreatorComparisonCard({ data }: { data: CreatorComparison }) {
  const fmtViews = (v: number) =>
    v >= 1_000_000
      ? `${(v / 1_000_000).toFixed(1)}M`
      : v >= 1_000
        ? `${Math.round(v / 1_000)}K`
        : v.toLocaleString("vi-VN");

  return (
    <div className="mt-6 rounded-xl border border-[var(--gv-rule)] bg-[var(--gv-canvas-2)] p-4">
      <p className="gv-mono mb-3 text-[10px] uppercase tracking-wider text-[var(--gv-ink-3)]">
        SO SÁNH TRONG KÊNH · {data.creator_handle}
      </p>

      <div className="grid grid-cols-2 gap-3">
        <a
          href={data.hit.tiktok_url ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col gap-1 rounded-lg border border-[var(--gv-pos)] bg-[var(--gv-canvas)] p-3 no-underline"
        >
          <span className="gv-mono text-[9px] uppercase tracking-wider text-[var(--gv-pos)]">
            Video đỉnh
          </span>
          <span className="gv-mono text-[22px] font-bold leading-none text-[var(--gv-ink)]">
            {fmtViews(data.hit.views)}
          </span>
          <span className="text-[10px] text-[var(--gv-ink-3)]">lượt xem</span>
        </a>

        <a
          href={data.flop.tiktok_url ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col gap-1 rounded-lg border border-[var(--gv-rule)] bg-[var(--gv-canvas)] p-3 no-underline"
        >
          <span className="gv-mono text-[9px] uppercase tracking-wider text-[var(--gv-ink-3)]">
            Video thấp nhất
          </span>
          <span className="gv-mono text-[22px] font-bold leading-none text-[var(--gv-ink)]">
            {fmtViews(data.flop.views)}
          </span>
          <span className="text-[10px] text-[var(--gv-ink-3)]">lượt xem</span>
        </a>
      </div>

      <div className="mt-3 flex items-center justify-between rounded-lg bg-[var(--gv-canvas)] px-3 py-2.5">
        <span className="text-[12px] text-[var(--gv-ink-2)]">Video đỉnh vượt video thấp nhất</span>
        <span className="gv-mono text-[13px] font-bold text-[var(--gv-ink)]">
          {data.delta.toLocaleString("vi-VN")}×
        </span>
      </div>

      <p className="mt-2 text-[11px] text-[var(--gv-ink-3)]">
        Video này đang ở{" "}
        <span className="font-medium text-[var(--gv-ink)]">{data.target_percentile}</span> so với{" "}
        <span className="font-medium text-[var(--gv-ink)]">{data.total_posts_analyzed} video</span> gần
        nhất của {data.creator_handle} (median: {fmtViews(data.median_views)} views).
      </p>
    </div>
  );
}

function formatSaveRatePct(meta: VideoAnalyzeMeta): string {
  const r = meta.save_rate;
  if (r == null || Number.isNaN(r)) return "—";
  const pct = r <= 1 ? r * 100 : r;
  return `${pct.toFixed(1)}%`;
}

function retentionEndPct(curve: { t: number; pct: number }[] | null | undefined): number | null {
  if (!curve?.length) return null;
  return curve[curve.length - 1].pct;
}

/** Research handoff — ``AnswerScreen`` reads ``location.state.initialPrompt``. */
function buildFlopScriptHandoffPrompt(d: VideoAnalyzeResponse, watchUrl: string | null): string {
  const issues = d.flop_issues ?? [];
  const lines = [
    `Corpus video_id: ${d.video_id}`,
    ...(watchUrl?.trim() ? [`Link TikTok đã soi: ${watchUrl.trim()}`] : []),
    "",
    "Mình vừa soi video flop trên Getviews — giúp mình lên shot-list / kịch bản, ưu tiên sửa các điểm sau:",
    ...issues.slice(0, 8).map((i) => `• ${i.title}\n  Fix gợi ý: ${i.fix}`),
  ];
  if (d.analysis_headline)
    lines.push("", `Chẩn đoán tổng: ${stringifyAnalysisHeadline(d.analysis_headline)}`);
  return lines.join("\n");
}

function FlopDiagnosisStrip({
  meta,
  nicheMeta,
  retentionEnd,
}: {
  meta: VideoAnalyzeMeta;
  nicheMeta: VideoNicheMeta | null;
  retentionEnd: number | null;
}) {
  const retLabel = retentionEnd != null ? `${Math.round(retentionEnd)}% giữ chân` : "— giữ chân";
  const nicheViews = nicheMeta?.avg_views != null ? formatViewsVi(nicheMeta.avg_views) : "—";
  // A.2.4 — when the BE pivoted the cohort to content_class
  // (benchmark_axis="content_class" from A.2.3), the comparison is sharper:
  // same (topic × format) bucket. Label reflects that so creators know the
  // benchmark is "videos cùng format" not just "videos cùng ngách". Default
  // ``"niche"`` for legacy responses without the axis tag.
  const isContentClass = nicheMeta?.benchmark_axis === "content_class";
  const cohortLabel = isContentClass ? "Cùng format TB" : "Ngách TB";
  const retSuffix = isContentClass ? "ret cùng format" : "ret ngách TB";
  const winnersLabel = isContentClass ? "video cùng format" : "video thắng trong ngách";
  const nicheRet =
    nicheMeta?.avg_retention != null
      ? `${Math.round(nicheMeta.avg_retention * 100)}% ${retSuffix}`
      : null;
  const winnersN = nicheMeta?.winners_sample_size ?? null;

  return (
    <div className="border-t-2 border-[color:var(--gv-ink)] pt-5">
      <div className="flex flex-wrap gap-x-4 gap-y-1 font-[family-name:var(--gv-font-mono)] text-xs text-[color:var(--gv-ink-3)]">
        <span>
          {formatViewsVi(meta.views)} view · {retLabel} · save {formatSaveRatePct(meta)}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        <span>
          {cohortLabel}: {nicheViews}
          {nicheRet ? ` · ${nicheRet}` : ""}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        {winnersN != null && winnersN >= WINNERS_CLAIM_MIN ? (
          <span>So sánh với {winnersN} {winnersLabel}</span>
        ) : (
          <span className="text-[color:var(--gv-ink-4)]">
            Đang xây dựng pool (≥10 video cần thu thập)
          </span>
        )}
      </div>
    </div>
  );
}

export function VideoBody({ report }: { report: VideoReportPayload }) {
  const navigate = useNavigate();
  const meta = report.meta;
  const duration = meta.duration_sec || 58;
  const userCurve = report.retention_curve ?? [];
  const bench = report.niche_benchmark_curve;
  const retEnd = retentionEndPct(userCurve);
  // ``mode`` lives on the report (BE single source of truth). VideoScreen
  // briefly distinguished a ``viewMode`` state during refetch; on the
  // answer surface the report is loaded once into the session payload,
  // so report.mode IS the view mode.
  const viewMode: VideoAnalyzeMode = report.mode ?? "win";
  const isFlop = viewMode === "flop";
  const flopIssueCount = report.flop_issues?.length ?? 0;

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
      stringifyAnalysisHeadline(report.analysis_headline).trim() ||
      `Video từ @${meta.creator?.trim() || "creator"}`;
    const phases = report.hook_phases ?? [];
    const first = phases[0];
    const hookFromPhase = first ? `${first.label}: ${first.body}` : null;
    const headlineHook = stringifyAnalysisHeadline(report.analysis_headline).trim();
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
      ? `${first.t_range} · ${first.label}\n${first.body}`
      : stringifyAnalysisHeadline(report.analysis_headline);
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
      <aside className="min-w-0">
        {/*
          Sticky within the studio scrollport: follows the user down the report
          until the grid row ends (same height as the main column), then scrolls away.
        */}
        <div className="sticky top-20 space-y-3 lg:top-24">
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
                @{meta.creator} · {Math.round(duration)}s
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
            <div className="gv-mono mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-accent)]">
              CHẨN ĐOÁN VIDEO CỦA BẠN · {flopIssueCount} ĐIỂM LỖI CẤU TRÚC
            </div>
          ) : report.carousel_subformat_label ? (
            <div className="gv-mono mb-1 text-[9.5px] tracking-[0.18em] text-[color:var(--gv-ink-4)]">
              MỔ CAROUSEL VIRAL ·{" "}
              <span className="normal-case text-[color:var(--gv-ink-3)]">
                {report.carousel_subformat_label}
                {report.carousel_slide_count ? ` · ${report.carousel_slide_count} slides` : ""}
              </span>
              {" "}·{" "}
              <span className="normal-case text-[color:var(--gv-ink-3)]">
                {meta.niche_label ?? "—"}
              </span>
            </div>
          ) : (
            <div className="gv-mono mb-1 text-[9.5px] tracking-[0.18em] text-[color:var(--gv-ink-4)]">
              MỔ VIDEO VIRAL ·{" "}
              <span className="normal-case text-[color:var(--gv-ink-3)]">
                {meta.niche_label ?? "—"}
              </span>
            </div>
          )}
          <h1
            className={`m-0 max-w-[820px] text-[clamp(26px,3vw,36px)] text-[color:var(--gv-ink)] ${
              isFlop
                ? "gv-serif text-pretty font-medium leading-[1.25]"
                : "gv-tight font-semibold leading-[1.05] tracking-tight"
            }`}
          >
            {isFlop ? (
              report.analysis_headline == null ? (
                "—"
              ) : isFlopHeadline(report.analysis_headline) ? (
                <>
                  {report.analysis_headline.prefix}
                  {report.analysis_headline.view_accent ? (
                    <em className="gv-serif-italic text-[color:var(--gv-accent)]">
                      {report.analysis_headline.view_accent}
                    </em>
                  ) : null}
                  {report.analysis_headline.middle}
                  {report.analysis_headline.prediction_pos ? (
                    <span className="text-[color:var(--gv-pos)]">
                      {report.analysis_headline.prediction_pos}
                    </span>
                  ) : null}
                  {report.analysis_headline.suffix}
                </>
              ) : (
                (report.analysis_headline as string)
              )
            ) : (
              (report.analysis_headline as string | null) ?? "—"
            )}
          </h1>
          {!isFlop && report.analysis_subtext ? (
            <p className="mt-2 max-w-[640px] text-[15px] text-[color:var(--gv-ink-3)]">
              {report.analysis_subtext}
            </p>
          ) : null}
        </header>

        {isFlop ? (
          <FlopDiagnosisStrip
            meta={meta}
            nicheMeta={report.niche_meta}
            retentionEnd={retEnd}
          />
        ) : null}

        <KpiGrid kpis={report.kpis} />

        <ContextStrip meta={meta} enrichment={report.enrichment} />

        {report.creator_comparison ? (
          <CreatorComparisonCard data={report.creator_comparison} />
        ) : report.meta?.creator ? (
          <CreatorComparisonUnavailable creator={report.meta.creator} />
        ) : null}

        <RetentionCurve
          durationSec={duration}
          userCurve={userCurve}
          benchmarkCurve={bench}
          retentionSource={meta.retention_source ?? "modeled"}
        />

        <section>
          <SectionMini kicker="Dòng thời gian" title={`Cấu trúc ${Math.round(duration)} giây`} />
          <Timeline segments={report.segments} durationSec={duration} />
        </section>

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

        {viewMode === "win" ? (
          <section>
            <SectionMini kicker="Giải mã hook" title="3 giây đầu — vì sao bạn không lướt qua?" />
            <HookPhaseGrid phases={report.hook_phases} />
          </section>
        ) : null}

        {viewMode === "win" && report.lessons.length ? (
          <section>
            <SectionMini kicker="Bài học áp dụng" title="3 điều bạn có thể copy" />
            <ul className="flex list-none flex-col gap-2.5 p-0">
              {report.lessons.map((lesson, i) => (
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

        {viewMode === "flop" && report.flop_issues?.length ? (
          <section>
            <SectionMini kicker="Lỗi cấu trúc" title="Xếp theo ảnh hưởng" />
            <div className="flex flex-col gap-3">
              {report.flop_issues.map((issue, i) => (
                <IssueCard key={`${issue.title}-${i}`} issue={issue} onApplyToScript={goScript} />
              ))}
            </div>
            {report.projected_views != null ? (
              <div className="mt-6 flex flex-col gap-4 bg-[color:var(--gv-ink)] px-5 py-4 text-[color:var(--gv-paper)] sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
                <div>
                  <div className="gv-mono text-[9.5px] uppercase tracking-[0.16em] opacity-60">
                    Dự đoán nếu áp fix chính
                  </div>
                  <p className="gv-tight m-0 mt-1 text-xl font-medium">
                    ~
                    <span className="text-[color:var(--gv-pos)]">
                      {formatViewsVi(report.projected_views)}
                    </span>{" "}
                    view
                  </p>
                </div>
                <Btn
                  type="button"
                  variant="accent"
                  className="w-full sm:w-auto"
                  onClick={goScript}
                >
                  Viết lại kịch bản
                  <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
                </Btn>
              </div>
            ) : (
              <div className="mt-4 flex justify-end">
                <Btn type="button" variant="accent" onClick={goScript}>
                  Viết lại kịch bản
                  <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
                </Btn>
              </div>
            )}
          </section>
        ) : null}

        {report.cross_format_signal ? (
          <CrossFormatPanel signal={report.cross_format_signal} />
        ) : null}
      </div>
    </div>
  );
}

function CrossFormatPanel({
  signal,
}: {
  signal: NonNullable<VideoReportPayload["cross_format_signal"]>;
}) {
  return (
    <section className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
      <SectionMini
        kicker="Tín hiệu liên ngách"
        title={`Format ${signal.format_label_vi} đang lan toả ${signal.niches_with_format} ngách`}
      />
      <p className="mt-1 text-[13px] text-[color:var(--gv-ink-3)]">
        Trong 30 ngày qua, {signal.total_sample_size} video cùng format này
        đang chạy ở {signal.niches_with_format} ngách khác nhau — tín hiệu
        format hot ngoài ngách của bạn.
      </p>
      {signal.top_hooks.length > 0 ? (
        <ul className="mt-3 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-2">
          {signal.top_hooks.map((h) => (
            <li
              key={h.hook_type}
              className="flex items-center justify-between gap-3 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2 text-[12px]"
            >
              <span className="font-medium text-[color:var(--gv-ink)]">
                {h.hook_type_vi || h.hook_type}
              </span>
              <span className="gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
                {Math.round(h.avg_views).toLocaleString("vi-VN")} view ·{" "}
                {h.niche_spread} ngách
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
