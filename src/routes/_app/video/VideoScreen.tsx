import { useEffect, useMemo } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { SectionMini } from "@/components/SectionMini";
import { Btn } from "@/components/v2/Btn";
import { TopBar } from "@/components/v2/TopBar";
import { RetentionCurve } from "@/components/v2/RetentionCurve";
import { Timeline } from "@/components/v2/Timeline";
import { HookPhaseGrid } from "@/components/v2/HookPhaseCard";
import { KpiGrid } from "@/components/v2/KpiGrid";
import { IssueCard } from "@/components/v2/IssueCard";
import { env } from "@/lib/env";
import type { VideoAnalyzeMeta, VideoAnalyzeResponse, VideoNicheMeta } from "@/lib/api-types";
import { useVideoAnalysis, videoAnalysisKey } from "@/hooks/useVideoAnalysis";
import { VideoUrlCapture } from "./VideoUrlCapture";

function formatViewsVi(n: number): string {
  return n.toLocaleString("vi-VN");
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

/** Chat handoff — matches ``ChatScreen`` `location.state.initialPrompt` consumption. */
function buildFlopScriptHandoffPrompt(d: VideoAnalyzeResponse): string {
  const issues = d.flop_issues ?? [];
  const lines = [
    "Mình vừa soi video flop trên Getviews — giúp mình lên shot-list / kịch bản, ưu tiên sửa các điểm sau:",
    ...issues.slice(0, 8).map((i) => `• ${i.title}\n  Fix gợi ý: ${i.fix}`),
  ];
  if (d.analysis_headline) lines.push("", `Chẩn đoán tổng: ${d.analysis_headline}`);
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
  const nicheRet =
    nicheMeta?.avg_retention != null ? `${Math.round(nicheMeta.avg_retention * 100)}% ret ngách TB` : null;
  const sample = nicheMeta?.sample_size;

  return (
    <div className="border-t-2 border-[color:var(--gv-ink)] pt-5">
      <div className="gv-mono mb-2.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-accent)]">
        Chẩn đoán · cấu trúc
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 font-[family-name:var(--gv-font-mono)] text-xs text-[color:var(--gv-ink-3)]">
        <span>
          {formatViewsVi(meta.views)} view · {retLabel} · save {formatSaveRatePct(meta)}
        </span>
        <span className="text-[color:var(--gv-ink-4)]">/</span>
        <span>
          Ngách TB: {nicheViews}
          {nicheRet ? ` · ${nicheRet}` : ""}
        </span>
        {sample != null && sample > 0 ? (
          <>
            <span className="text-[color:var(--gv-ink-4)]">/</span>
            <span className="text-[color:var(--gv-ink-4)]">Mẫu MV ~{sample} video</span>
          </>
        ) : null}
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
    enabled: Boolean(cacheKey && cloudConfigured),
  });

  const emptyParams = !cacheKey;
  const showCompactUrlBar = Boolean(
    cloudConfigured && cacheKey && !isPending && !isFetching && (Boolean(data) || isError),
  );

  const submitNewUrl = (tiktokUrl: string) => {
    navigate(`/app/video?url=${encodeURIComponent(tiktokUrl)}`, { replace: true });
  };

  return (
    <AppLayout>
      <TopBar title="Soi video" />
      <main className="mx-auto max-w-[1280px] px-5 pb-20 pt-6 min-[900px]:px-7">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Link
            to="/app/trends"
            className="inline-flex items-center gap-1.5 text-sm text-[color:var(--gv-ink-3)] transition-colors hover:text-[color:var(--gv-ink)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" strokeWidth={1.75} />
            Quay lại Xu hướng
          </Link>
        </div>

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
              <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">{error?.message ?? "Lỗi không xác định"}</p>
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
            <VideoAnalysisBodyInner data={data} />
          </div>
        ) : null}
      </main>
    </AppLayout>
  );
}

function VideoAnalysisBodyInner({ data }: { data: VideoAnalyzeResponse }) {
  const navigate = useNavigate();
  const meta = data.meta;
  const duration = meta.duration_sec || 58;
  const userCurve = data.retention_curve ?? [];
  const bench = data.niche_benchmark_curve;
  const retEnd = retentionEndPct(userCurve);
  const isFlop = data.mode === "flop";

  const goScript = () => {
    navigate("/app/chat", {
      state: { initialPrompt: buildFlopScriptHandoffPrompt(data) },
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
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[color:color-mix(in_srgb,var(--gv-ink)_55%,transparent)]" />
          <div className="absolute bottom-4 left-3.5 right-3.5 text-[color:var(--gv-paper)]">
            <div className="gv-mono text-[11px] opacity-90">
              @{meta.creator} · {Math.round(duration)}s
            </div>
            {meta.title ? (
              <p className="gv-tight mt-1 text-lg leading-tight">{meta.title}</p>
            ) : null}
          </div>
        </div>
        <p className="gv-mono mt-3 text-center text-[11px] uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
          {meta.date_posted ? `${meta.date_posted} · ` : ""}
          {formatViewsVi(meta.views)} view
        </p>
      </aside>

      <div className="flex flex-col gap-7">
        <header>
          <div className="gv-mono mb-1 text-[9.5px] uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
            Báo cáo phân tích · {data.mode === "win" ? "Nổ" : "Flop"}
          </div>
          <h1
            className={`gv-tight m-0 max-w-[820px] text-[clamp(26px,3vw,36px)] tracking-tight text-[color:var(--gv-ink)] ${
              isFlop ? "text-pretty font-medium leading-[1.1]" : "font-semibold leading-[1.05]"
            }`}
          >
            {data.analysis_headline ?? "—"}
          </h1>
          {!isFlop && data.analysis_subtext ? (
            <p className="mt-2 max-w-[640px] text-[15px] text-[color:var(--gv-ink-3)]">{data.analysis_subtext}</p>
          ) : null}
        </header>

        {isFlop ? (
          <FlopDiagnosisStrip meta={meta} nicheMeta={data.niche_meta} retentionEnd={retEnd} />
        ) : null}

        <KpiGrid kpis={data.kpis} />

        <RetentionCurve durationSec={duration} userCurve={userCurve} benchmarkCurve={bench} />

        <section>
          <SectionMini kicker="Dòng thời gian" title={`Cấu trúc ${Math.round(duration)} giây`} />
          <Timeline segments={data.segments} durationSec={duration} />
        </section>

        {data.mode === "win" ? (
          <section>
            <SectionMini kicker="Giải mã hook" title="3 giây đầu — vì sao giữ chân?" />
            <HookPhaseGrid phases={data.hook_phases} />
          </section>
        ) : null}

        {data.mode === "win" && data.lessons.length ? (
          <section>
            <SectionMini kicker="Bài học áp dụng" title="Điểm rút ra từ video" />
            <ul className="flex list-none flex-col gap-2.5 p-0">
              {data.lessons.map((lesson, i) => (
                <li
                  key={`${lesson.title}-${i}`}
                  className="grid grid-cols-[40px_1fr] items-center gap-4 rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-3.5 min-[520px]:grid-cols-[40px_1fr_auto]"
                >
                  <span className="gv-tight text-2xl text-[color:var(--gv-accent)]">0{i + 1}</span>
                  <div>
                    <p className="gv-tight m-0 text-[17px] text-[color:var(--gv-ink)]">{lesson.title}</p>
                    <p className="mt-0.5 text-xs text-[color:var(--gv-ink-3)]">{lesson.body}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {data.mode === "flop" && data.flop_issues?.length ? (
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
