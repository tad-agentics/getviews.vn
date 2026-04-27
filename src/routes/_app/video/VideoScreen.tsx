import { useEffect, useMemo } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import {
  ArrowRight,
  Copy,
  Loader2,
  Play,
  Plus,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { SectionMini } from "@/components/SectionMini";
import { Btn } from "@/components/v2/Btn";
import { TopBar } from "@/components/v2/TopBar";
import { RetentionCurve } from "@/components/v2/RetentionCurve";
import { Timeline } from "@/components/v2/Timeline";
import { HookPhaseGrid } from "@/components/v2/HookPhaseCard";
import { KpiGrid } from "@/components/v2/KpiGrid";
import { IssueCard } from "@/components/v2/IssueCard";
import { analysisErrorCopy } from "@/lib/errorMessages";
import { env } from "@/lib/env";
import { scriptPrefillFromVideo } from "@/lib/scriptPrefill";
import { looksLikeTikTokUrl } from "@/lib/tiktokUrl";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { logUsage } from "@/lib/logUsage";
import type {
  FlopHeadline,
  VideoAnalyzeMeta,
  VideoAnalyzeMode,
  VideoAnalyzeResponse,
  VideoLesson,
  VideoNicheMeta,
} from "@/lib/api-types";
import { useHomePulse } from "@/hooks/useHomePulse";
import { useVideoAnalysis, videoAnalysisKey } from "@/hooks/useVideoAnalysis";
import { sanitizePredictionPos } from "@/lib/sanitizePredictionPos";
import { r2FrameUrl } from "@/lib/services/corpus-service";
import { CommentRadarTile } from "@/routes/_app/components/CommentRadarTile";
import { ThumbnailTile } from "@/routes/_app/components/ThumbnailTile";
import { VideoUrlCapture } from "./VideoUrlCapture";

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

/** Research handoff — ``AnswerScreen`` reads `location.state.initialPrompt` or `?q=`. */
function buildFlopScriptHandoffPrompt(d: VideoAnalyzeResponse, analyzeUrl: string | null): string {
  const issues = d.flop_issues ?? [];
  const lines = [
    `Corpus video_id: ${d.video_id}`,
    ...(analyzeUrl?.trim() ? [`Link TikTok đã soi: ${analyzeUrl.trim()}`] : []),
    "",
    "Mình vừa soi video flop trên Getviews — giúp mình lên shot-list / kịch bản, ưu tiên sửa các điểm sau:",
    ...issues.slice(0, 8).map((i) => `• ${i.title}\n  Fix gợi ý: ${i.fix}`),
  ];
  if (d.analysis_headline) lines.push("", `Chẩn đoán tổng: ${stringifyAnalysisHeadline(d.analysis_headline)}`);
  return lines.join("\n");
}

/** Matches CLAIM_TIERS.pattern_spread — UI only, do not import tiers into this strip. */
const WINNERS_CLAIM_MIN = 10;

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
  const nicheRet =
    nicheMeta?.avg_retention != null ? `${Math.round(nicheMeta.avg_retention * 100)}% ret ngách TB` : null;
  const winnersN = nicheMeta?.winners_sample_size ?? null;

  return (
    <div className="border-t-2 border-[color:var(--gv-ink)] pt-5">
      <div className="flex flex-wrap gap-x-4 gap-y-1 font-[family-name:var(--gv-font-mono)] text-xs text-[color:var(--gv-ink-3)]">
        <span>
          {formatViewsVi(meta.views)} view · {retLabel} · save {formatSaveRatePct(meta)}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        <span>
          Ngách TB: {nicheViews}
          {nicheRet ? ` · ${nicheRet}` : ""}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        {winnersN != null && winnersN >= WINNERS_CLAIM_MIN ? (
          <span>So sánh với {winnersN} video thắng</span>
        ) : (
          <span className="text-[color:var(--gv-ink-4)]">
            Đang xây dựng pool (≥10 video cần thu thập)
          </span>
        )}
      </div>
    </div>
  );
}

export default function VideoScreen() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const videoId = searchParams.get("video_id");
  const url = searchParams.get("url");

  const cacheKey = useMemo(() => videoAnalysisKey(videoId, url), [videoId, url]);
  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);

  // Reject obviously-invalid `?url=` payloads before they reach Cloud
  // Run. A non-TikTok URL burns a backend round-trip and hits 404
  // (today users see "Không tìm thấy video" with no hint that the URL
  // itself is wrong). We only gate the query-param path — VideoId
  // deep-links are opaque and validated server-side.
  const urlValidationError = useMemo(() => {
    const u = url?.trim();
    if (!u) return null;
    return looksLikeTikTokUrl(u) ? null : "URL không phải link TikTok — dùng link dạng tiktok.com/@… hoặc vm.tiktok.com/…";
  }, [url]);
  const { data: pulse } = useHomePulse(cloudConfigured);

  const asOf = useMemo(() => {
    if (!pulse?.as_of) return null;
    const d = new Date(pulse.as_of);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [pulse?.as_of]);
  const asOfRelative = useMemo(() => formatRelativeSinceVi(new Date(), asOf), [asOf]);

  /** B.1.5 — same handoff as chat: `location.state.prefillUrl` → stable `?url=` query. */
  useEffect(() => {
    const st = location.state as { prefillUrl?: string } | null | undefined;
    const p = st?.prefillUrl?.trim();
    if (!p) return;
    if (searchParams.get("video_id") || searchParams.get("url")) return;
    navigate(`/app/video?url=${encodeURIComponent(p)}`, { replace: true, state: {} });
  }, [location.state, navigate, searchParams]);

  const { data, isPending, isError, error, refetch, isFetching } = useVideoAnalysis({
    videoId,
    url,
    forceRefresh: false,
    // Skip the hook when the URL is malformed — prevents a 404-generating
    // POST that would burn a Cloud Run round-trip.
    enabled: Boolean(cacheKey && cloudConfigured && !urlValidationError),
  });

  // One video = one mode = one analysis. The BE picks the analyzer
  // (``is_flop_mode`` in ``video_analyze.py`` auto-detects from the
  // video's performance vs niche), and ``data.mode`` is the single
  // source of truth for which UI to render. The previous code parsed
  // a ``?mode=`` URL param and let it override the response mode —
  // that allowed a contradictory state (flop UI on a win response).
  // No FE call site sets ``?mode=`` today, so the override was dead;
  // dropped here so the contradiction can never reappear.
  const effectiveMode = useMemo((): VideoAnalyzeMode => data?.mode ?? "win", [data?.mode]);

  const emptyParams = !cacheKey;
  const showCompactUrlBar = Boolean(
    cloudConfigured && cacheKey && !isPending && !isFetching && (Boolean(data) || isError),
  );

  const submitNewUrl = (tiktokUrl: string) => {
    navigate(`/app/video?url=${encodeURIComponent(tiktokUrl)}`, { replace: true });
  };

  return (
    <AppLayout enableMobileSidebar>
      <TopBar
        kicker="BÁO CÁO"
        title="Phân Tích Video"
        right={
          <>
            {pulse?.as_of ? (
              <span className="hide-narrow hidden items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)] md:inline-flex">
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]"
                  style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
                />
                Dữ liệu cập nhật {asOfRelative}
              </span>
            ) : null}
            {/* Bookmark / "Đã Lưu" stub removed (D.6-era cleanup) — no
                 handler, no data model, just visual clutter. Re-add
                 when the "save video for later" feature lands. */}
            <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/answer")}>
              <Plus className="h-3.5 w-3.5" strokeWidth={2} />
              Phân tích mới
            </Btn>
          </>
        }
      />
      <main className="gv-route-main gv-route-main--1280">
        {emptyParams ? (
          <div className="flex flex-col gap-6">
            <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6 text-center text-[color:var(--gv-ink-3)]">
              <p className="gv-tight m-0 text-lg text-[color:var(--gv-ink)]">Soi video trong corpus</p>
              <p className="mt-2 text-sm">
                Dán link TikTok đã ingest, hoặc mở từ lưới{" "}
                <Link to="/app/trends" className="text-[color:var(--gv-accent-deep)] underline-offset-2 hover:underline">
                  Xu hướng
                </Link>
                .
              </p>
            </div>
            {cloudConfigured ? (
              <VideoUrlCapture variant="hero" onSubmitUrl={submitNewUrl} disabled={false} />
            ) : (
              <p className="text-sm text-[color:var(--gv-ink-3)]">
                Phân tích cần <span className="font-[family-name:var(--gv-font-mono)]">VITE_CLOUD_RUN_API_URL</span> trong
                môi trường build.
              </p>
            )}
          </div>
        ) : !cloudConfigured ? (
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Phân tích video cần <span className="font-[family-name:var(--gv-font-mono)]">VITE_CLOUD_RUN_API_URL</span>{" "}
            trong môi trường build.
          </p>
        ) : urlValidationError ? (
          // Deep-link came with a non-TikTok URL; fail closed + offer
          // the normal capture input as a recovery path.
          <div className="flex flex-col gap-4">
            <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
              <p className="gv-tight m-0 text-lg text-[color:var(--gv-neg-deep)]">URL không hợp lệ</p>
              <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">{urlValidationError}</p>
            </div>
            <VideoUrlCapture variant="hero" onSubmitUrl={submitNewUrl} />
          </div>
        ) : isPending || isFetching ? (
          <div
            className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-[color:var(--gv-ink-3)]"
            role="status"
            aria-label="Đang phân tích video"
          >
            <Loader2 className="h-8 w-8 animate-spin text-[color:var(--gv-accent)]" strokeWidth={1.5} />
            <span className="text-sm">Đang tải phân tích…</span>
          </div>
        ) : isError ? (
          <div className="flex flex-col gap-4">
            {showCompactUrlBar ? (
              <div>
                <p className="gv-mono mb-2 text-[10px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
                  Phân tích video khác
                </p>
                <VideoUrlCapture key={cacheKey} variant="compact" onSubmitUrl={submitNewUrl} />
              </div>
            ) : null}
            <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
              <p className="gv-tight m-0 text-lg text-[color:var(--gv-neg-deep)]">Không tải được phân tích</p>
              <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">{analysisErrorCopy(error)}</p>
              <Btn className="mt-4" type="button" variant="ghost" onClick={() => refetch()}>
                Thử lại
              </Btn>
            </div>
          </div>
        ) : data ? (
          <div className="flex flex-col gap-5">
            {showCompactUrlBar ? (
              <div>
                <p className="gv-mono mb-2 text-[10px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
                  Phân tích video khác
                </p>
                <VideoUrlCapture key={cacheKey} variant="compact" onSubmitUrl={submitNewUrl} />
              </div>
            ) : null}
            {/* Win/flop Segmented toggle removed — one video has one
                analysis (BE picks via ``is_flop_mode``). The toggle
                let creators flip the same video between modes, which
                contradicted the design model that win + flop are
                separate intents with separate diagnostic paths. */}
            <VideoAnalysisBodyInner data={data} analyzeUrl={url} viewMode={effectiveMode} />
          </div>
        ) : null}
      </main>
    </AppLayout>
  );
}

function VideoAnalysisBodyInner({
  data,
  analyzeUrl,
  viewMode,
}: {
  data: VideoAnalyzeResponse;
  /** Query ``url`` when user analyzed by TikTok URL (for chat handoff). */
  analyzeUrl: string | null;
  /** Win vs flop layout; may differ from ``data.mode`` briefly while refetching. */
  viewMode: VideoAnalyzeMode;
}) {
  const navigate = useNavigate();
  const meta = data.meta;
  const duration = meta.duration_sec || 58;
  const userCurve = data.retention_curve ?? [];
  const bench = data.niche_benchmark_curve;
  const retEnd = retentionEndPct(userCurve);
  const isFlop = viewMode === "flop";
  const flopIssueCount = data.flop_issues?.length ?? 0;

  const tiktokWatchUrl = useMemo(() => {
    const raw = meta.creator?.trim() ?? "";
    if (!raw || !data.video_id) return null;
    const handle = raw.startsWith("@") ? raw.slice(1) : raw;
    if (!handle) return null;
    return `https://www.tiktok.com/@${handle}/video/${data.video_id}`;
  }, [meta.creator, data.video_id]);

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
    logUsage("video_screen_load", { mode: viewMode, video_id: data.video_id });
  }, [viewMode, data.video_id]);

  const goScript = () => {
    if (isFlop) logUsage("flop_cta_click", { video_id: data.video_id });
    navigate("/app/answer", {
      state: { initialPrompt: buildFlopScriptHandoffPrompt(data, analyzeUrl) },
    });
  };

  const goWinScript = () => {
    logUsage("video_to_script", { video_id: data.video_id, mode: "win" });
    const topic =
      meta.title?.trim() ||
      stringifyAnalysisHeadline(data.analysis_headline).trim() ||
      `Video từ @${meta.creator?.trim() || "creator"}`;
    const phases = data.hook_phases ?? [];
    const first = phases[0];
    const hookFromPhase = first ? `${first.label}: ${first.body}` : null;
    const headlineHook = stringifyAnalysisHeadline(data.analysis_headline).trim();
    navigate(
      scriptPrefillFromVideo({
        topic,
        hook: (hookFromPhase ?? headlineHook) || null,
        duration_sec: duration,
      }),
    );
  };

  const copyHook = async () => {
    const phases = data.hook_phases ?? [];
    const first = phases[0];
    const text = first
      ? `${first.t_range} · ${first.label}\n${first.body}`
      : stringifyAnalysisHeadline(data.analysis_headline);
    if (!text.trim()) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard denied or unavailable */
    }
  };

  const showCommentRadarTile =
    data.comment_radar != null && data.comment_radar.sampled > 0;
  const showThumbnailTile = data.thumbnail_analysis != null;

  const applyLesson = (lesson: VideoLesson) => {
    navigate("/app/answer", {
      state: {
        initialPrompt: [
          `Corpus video_id: ${data.video_id}`,
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
      <aside>
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
        <p className="gv-mono mt-3 text-center text-[11px] uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
          {thumbStats}
        </p>
      </aside>

      <div className="flex flex-col gap-7">
        {!isFlop ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            {/* Second bookmark stub removed alongside the top-bar one —
                 "Lưu" with no backing model. */}
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
          ) : (
            <div className="gv-mono mb-1 text-[9.5px] tracking-[0.18em] text-[color:var(--gv-ink-4)]">
              MỔ VIDEO VIRAL ·{" "}
              <span className="normal-case text-[color:var(--gv-ink-3)]">{meta.niche_label ?? "—"}</span>
            </div>
          )}
          <h1
            className={`m-0 max-w-[820px] text-[clamp(26px,3vw,36px)] text-[color:var(--gv-ink)] ${
              isFlop
                ? "gv-serif text-pretty font-medium leading-[1.1]"
                : "gv-tight font-semibold leading-[1.05] tracking-tight"
            }`}
          >
            {isFlop ? (
              data.analysis_headline == null ? (
                "—"
              ) : isFlopHeadline(data.analysis_headline) ? (
                <>
                  {data.analysis_headline.prefix}
                  {data.analysis_headline.view_accent ? (
                    <em className="gv-serif-italic text-[color:var(--gv-accent)]">
                      {data.analysis_headline.view_accent}
                    </em>
                  ) : null}
                  {data.analysis_headline.middle}
                  {data.analysis_headline.prediction_pos ? (
                    <span className="text-[color:var(--gv-pos)]">{data.analysis_headline.prediction_pos}</span>
                  ) : null}
                  {data.analysis_headline.suffix}
                </>
              ) : (
                (data.analysis_headline as string)
              )
            ) : (
              (data.analysis_headline as string | null) ?? "—"
            )}
          </h1>
          {!isFlop && data.analysis_subtext ? (
            <p className="mt-2 max-w-[640px] text-[15px] text-[color:var(--gv-ink-3)]">{data.analysis_subtext}</p>
          ) : null}
        </header>

        {isFlop ? (
          <FlopDiagnosisStrip meta={meta} nicheMeta={data.niche_meta} retentionEnd={retEnd} />
        ) : null}

        <KpiGrid kpis={data.kpis} />

        <RetentionCurve
          durationSec={duration}
          userCurve={userCurve}
          benchmarkCurve={bench}
          retentionSource={meta.retention_source ?? "modeled"}
        />

        <section>
          <SectionMini kicker="Dòng thời gian" title={`Cấu trúc ${Math.round(duration)} giây`} />
          <Timeline segments={data.segments} durationSec={duration} />
        </section>

        {showCommentRadarTile || showThumbnailTile ? (
          <section aria-label="Thumbnail và bình luận">
            <div className="grid grid-cols-1 gap-4 min-[640px]:grid-cols-2">
              {showCommentRadarTile && data.comment_radar ? (
                <CommentRadarTile data={data.comment_radar} />
              ) : null}
              {showThumbnailTile && data.thumbnail_analysis ? (
                <ThumbnailTile
                  data={data.thumbnail_analysis}
                  frameUrl={r2FrameUrl(data.video_id)}
                />
              ) : null}
            </div>
          </section>
        ) : null}

        {viewMode === "win" ? (
          <section>
            <SectionMini kicker="Giải mã hook" title="3 giây đầu — vì sao bạn không lướt qua?" />
            <HookPhaseGrid phases={data.hook_phases} />
          </section>
        ) : null}

        {viewMode === "win" && data.lessons.length ? (
          <section>
            <SectionMini kicker="Bài học áp dụng" title="3 điều bạn có thể copy" />
            <ul className="flex list-none flex-col gap-2.5 p-0">
              {data.lessons.map((lesson, i) => (
                <li
                  key={`${lesson.title}-${i}`}
                  className="grid grid-cols-1 items-center gap-3 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3.5 min-[520px]:grid-cols-[40px_1fr_auto] min-[520px]:gap-4"
                >
                  <span className="gv-tight text-2xl text-[color:var(--gv-accent)]">0{i + 1}</span>
                  <div className="min-w-0">
                    <p className="gv-tight m-0 text-[17px] text-[color:var(--gv-ink)]">{lesson.title}</p>
                    <p className="mt-0.5 text-xs text-[color:var(--gv-ink-3)]">{lesson.body}</p>
                  </div>
                  <Btn
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="w-full justify-center min-[520px]:w-auto"
                    onClick={() => applyLesson(lesson)}
                  >
                    Áp dụng
                  </Btn>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {viewMode === "flop" && data.flop_issues?.length ? (
          <section>
            <SectionMini kicker="Lỗi cấu trúc" title="Xếp theo ảnh hưởng" />
            <div className="flex flex-col gap-3">
              {data.flop_issues.map((issue, i) => (
                <IssueCard key={`${issue.title}-${i}`} issue={issue} onApplyToScript={goScript} />
              ))}
            </div>
            {data.projected_views != null ? (
              <div className="mt-6 flex flex-col gap-4 bg-[color:var(--gv-ink)] px-5 py-4 text-[color:var(--gv-paper)] min-[640px]:flex-row min-[640px]:flex-wrap min-[640px]:items-center min-[640px]:justify-between">
                <div>
                  <div className="gv-mono text-[9.5px] uppercase tracking-[0.16em] opacity-60">
                    Dự đoán nếu áp fix chính
                  </div>
                  <p className="gv-tight m-0 mt-1 text-xl font-medium">
                    ~<span className="text-[color:var(--gv-pos)]">{formatViewsVi(data.projected_views)}</span> view
                  </p>
                </div>
                <Btn type="button" variant="accent" className="w-full min-[640px]:w-auto" onClick={goScript}>
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
      </div>
    </div>
  );
}
