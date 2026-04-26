import { memo, useEffect, useMemo, useRef } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight, Pencil } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { channelAnalyzeHandleKey, useChannelAnalyze } from "@/hooks/useChannelAnalyze";
import type { ProfileRow } from "@/hooks/useProfile";
import { useRefreshMyChannel } from "@/hooks/useRefreshMyChannel";
import type {
  ChannelAnalyzeResponse,
  ChannelLesson,
  ChannelTopVideo,
  NicheChannelBenchmarks,
} from "@/lib/api-types";
import { env } from "@/lib/env";
import { formatFollowers, formatViews } from "@/lib/formatters";
import { ChannelDiagnosticList } from "./ChannelDiagnosticList";
import { ChannelPulseBlock } from "./ChannelPulseBlock";
import { ChannelRecent7dList } from "./ChannelRecent7dList";

function profileTikTok(p: ProfileRow | null | undefined): string | null {
  const h = (p as { tiktok_handle?: string | null } | null | undefined)?.tiktok_handle;
  return h?.trim() || null;
}

function channelInitial(name: string, handle: string): string {
  const s = (name?.trim() || handle).trim();
  if (!s) return "?";
  return s[0]?.toUpperCase() ?? "?";
}

function kpiDeltaClass(delta: string): string {
  const base = "gv-mono mt-0.5 text-[10.5px] font-semibold";
  if (/↓|▼|−/.test(delta) || /-\s*\d/.test(delta)) return `${base} text-[color:var(--gv-neg-deep)]`;
  if (/↑|▲|\+/.test(delta)) return `${base} text-[color:var(--gv-pos)]`;
  if (delta === "—" || !delta.trim()) return `${base} text-[color:var(--gv-ink-4)]`;
  return `${base} text-[color:var(--gv-ink-3)]`;
}

/** Ước lượng video/tuần từ chuỗi cadence — chỉ để hiển thị KPI. */
function postsPerWeekGuess(cadence: string | null): number | null {
  if (!cadence?.trim()) return null;
  const m = cadence.match(/(\d+)/);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  if (!Number.isFinite(n)) return null;
  if (/tuần|week/i.test(cadence)) return n;
  if (/ngày|day/i.test(cadence) && n > 0) return Math.min(14, Math.round(n * 7));
  return n;
}

function nicheShortLabel(full: string): string {
  const t = full.trim();
  if (t.length <= 24) return t;
  return `${t.slice(0, 22)}…`;
}

type PercentileSpec = { label: string; fillPct: number; topPct: number; barTone: "pos" | "accent" | "ink" | "neg" };

/**
 * Map a user value + niche {p50, p75} into a percentile-band label and bar
 * fill. The RPC only exposes p50 and p75, not the full distribution, so we
 * approximate the user's rank in three bands: top 25% (≥ p75), top 50%
 * (≥ p50, < p75), top 75%+ (< p50). Bar fill scales linearly to p75 capped
 * at 92% so the bar never visually saturates without a literal "you beat
 * the top quartile" signal.
 */
function bandFromBenchmarks(value: number, p50: number, p75: number): { fillPct: number; topPct: number } {
  const clean = Number.isFinite(value) ? Math.max(0, value) : 0;
  if (p75 <= 0) {
    // Niche has no benchmark sample (channel_count = 0). Fall back to a
    // mid-bar so the row renders without claiming a real ranking.
    return { fillPct: 50, topPct: 50 };
  }
  const ratio = clean / p75;
  const fillPct = Math.max(8, Math.min(92, Math.round(ratio * 92)));
  const topPct = clean >= p75 ? 25 : clean >= p50 ? 50 : 75;
  return { fillPct, topPct };
}

function buildPercentiles(data: ChannelAnalyzeResponse, bench: NicheChannelBenchmarks): PercentileSpec[] {
  const er = data.engagement_pct <= 1 ? data.engagement_pct * 100 : data.engagement_pct;
  const posts = postsPerWeekGuess(data.posting_cadence) ?? 0;

  const view = bandFromBenchmarks(data.avg_views, bench.avg_views_p50, bench.avg_views_p75);
  const eng = bandFromBenchmarks(er, bench.engagement_p50, bench.engagement_p75);
  const post = bandFromBenchmarks(posts, bench.posts_per_week_p50, bench.posts_per_week_p75);

  return [
    { label: "View trung bình", fillPct: view.fillPct, topPct: view.topPct, barTone: "ink" },
    { label: "Tương tác", fillPct: eng.fillPct, topPct: eng.topPct, barTone: "accent" },
    { label: "Tần suất post", fillPct: post.fillPct, topPct: post.topPct, barTone: "neg" },
  ];
}

/** Sample-size guard — render benchmark layer only when the niche has enough creators. */
const MIN_BENCHMARK_SAMPLE = 5;

function bestWorstVideos(videos: ChannelTopVideo[], avgViews: number): { best: ChannelTopVideo; worst: ChannelTopVideo } | null {
  if (videos.length < 2 || avgViews <= 0) return null;
  const sorted = [...videos].sort((a, b) => b.views - a.views);
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];
  if (!best || !worst || best.video_id === worst.video_id) return null;
  return { best, worst };
}

function lessonIcon(i: number): { sym: string; className: string } {
  if (i === 0) return { sym: "▲", className: "text-[color:var(--gv-pos-deep)]" };
  if (i === 1) return { sym: "→", className: "text-[color:var(--gv-accent-deep)]" };
  return { sym: "✕", className: "text-[color:var(--gv-neg-deep)]" };
}

function PercentileBarRow({ spec }: { spec: PercentileSpec }) {
  const fillColor =
    spec.barTone === "pos"
      ? "bg-[color:var(--gv-pos)]"
      : spec.barTone === "accent"
        ? "bg-[color:var(--gv-accent)]"
        : spec.barTone === "neg"
          ? "bg-[color:var(--gv-neg)]"
          : "bg-[color:var(--gv-ink-3)]";
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="text-[12px] text-[color:var(--gv-ink-2)]">{spec.label}</span>
        <span className="gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
          top <strong className="text-[color:var(--gv-ink)]">{spec.topPct}%</strong>
        </span>
      </div>
      <div className="relative h-1.5 overflow-hidden rounded-full bg-[color:var(--gv-rule)]">
        <div className={`absolute left-0 top-0 h-full rounded-full ${fillColor}`} style={{ width: `${spec.fillPct}%` }} />
        <div
          className="pointer-events-none absolute bottom-0 top-0 w-px bg-[color:var(--gv-ink)] opacity-30"
          style={{ left: "50%" }}
          aria-hidden
        />
      </div>
    </div>
  );
}

const InsightsFooter = memo(function InsightsFooter({ lessons }: { lessons: ChannelLesson[] }) {
  const rows = lessons.slice(0, 3);
  if (rows.length === 0) return null;
  return (
    <div className="border-t border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-5 py-4 sm:px-6">
      <p className="gv-uc mb-3 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-ink-4)]">
        ● GỢI Ý CHO BẠN
      </p>
      <ul className="flex flex-col gap-2.5">
        {rows.map((it, i) => {
          const { sym, className } = lessonIcon(i);
          return (
            <li key={`${it.title}-${i}`} className="flex gap-2.5">
              <span className={`shrink-0 text-[10px] font-bold leading-[1.45] ${className}`}>{sym}</span>
              <p className="text-[13px] leading-[1.45] text-[color:var(--gv-ink-2)]">
                <span className="font-medium text-[color:var(--gv-ink)]">{it.title}</span>
                {it.body ? (
                  <>
                    {" "}
                    {it.body}
                  </>
                ) : null}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
});

function ConnectedCard({
  data,
  nicheLabel,
  handleDisplay,
}: {
  data: ChannelAnalyzeResponse;
  nicheLabel: string;
  handleDisplay: string;
}) {
  const navigate = useNavigate();
  const at = handleDisplay.startsWith("@") ? handleDisplay : `@${handleDisplay}`;
  // Render the benchmark layer only when the niche has enough creators
  // (>= MIN_BENCHMARK_SAMPLE). Below that, fall back to mid-bars and
  // hide the "Ngách: …" / "Top 25%: …" sub-labels rather than claiming
  // a ranking against a 1-2-channel sample.
  const bench = data.niche_benchmarks;
  const hasBench = !!bench && bench.channel_count >= MIN_BENCHMARK_SAMPLE;
  const percentiles = useMemo(
    () => (bench ? buildPercentiles(data, bench) : null),
    [data, bench],
  );
  const bw = useMemo(() => bestWorstVideos(data.top_videos, data.avg_views), [data.top_videos, data.avg_views]);
  const viewDelta = data.kpis[0]?.delta ?? "—";
  const postsPw = postsPerWeekGuess(data.posting_cadence);

  return (
    <div className="overflow-hidden rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[color:var(--gv-rule)] px-5 py-4 sm:px-6 sm:py-5">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-[18px] font-bold text-white"
            style={{
              background: "linear-gradient(135deg, var(--gv-accent) 0%, var(--gv-accent-2) 100%)",
            }}
            aria-hidden
          >
            {channelInitial(data.name, data.handle)}
          </div>
          <div className="min-w-0">
            <p className="gv-tight truncate text-[15px] font-semibold text-[color:var(--gv-ink)]">{at}</p>
            <p className="mt-0.5 text-[12px] text-[color:var(--gv-ink-3)]">
              {nicheShortLabel(data.niche_label || nicheLabel)} · {data.total_videos.toLocaleString("vi-VN")} video
            </p>
          </div>
        </div>
        <Btn
          variant="ghost"
          size="sm"
          type="button"
          className="shrink-0"
          onClick={() => navigate(`/app/channel?handle=${encodeURIComponent(handleDisplay.replace(/^@/, ""))}`)}
        >
          <span>Soi sâu</span>
          <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
        </Btn>
      </div>

      {/* PR-1 — pulse hero (streak + serif headline) */}
      {data.pulse ? <ChannelPulseBlock pulse={data.pulse} /> : null}

      {/* PR-1 — 7 ngày qua ranked verdict list. Hidden when both pulse
       * AND recent_7d are absent (legacy cached responses): the FE then
       * falls through directly to the existing KPI grid. */}
      {data.recent_7d ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="my-channel-recent7d-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-ink-4)]">
            ● 7 NGÀY QUA
          </p>
          <h3
            id="my-channel-recent7d-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            Video gần nhất
          </h3>
          <p className="mt-1 mb-3.5 text-[12.5px] leading-snug text-[color:var(--gv-ink-3)]">
            Sắp theo độ lệch so với view trung bình kênh ({formatViews(data.avg_views)}).
            Click để mở chi tiết.
          </p>
          <ChannelRecent7dList rows={data.recent_7d} />
        </section>
      ) : null}

      {/* PR-2 — strengths / weaknesses diagnostic blocks. Hidden when
       * both arrays are empty (legacy cached responses pre-schema
       * migration); the FE falls through to the KPI grid in that case
       * and the row's 7-day TTL forces a regenerate next pass. */}
      {data.strengths && data.strengths.length > 0 ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="my-channel-strengths-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-pos-deep)]">
            ▲ ĐANG TỐT
          </p>
          <h3
            id="my-channel-strengths-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            {data.strengths.length} thứ kênh đang làm tốt
          </h3>
          <p className="mt-1 mb-3.5 text-[12.5px] leading-snug text-[color:var(--gv-ink-3)]">
            Đo trực tiếp từ kênh bạn — không so với ngách. Mỗi điểm: tại sao tốt + cách tận dụng.
          </p>
          <ChannelDiagnosticList kind="strength" items={data.strengths} />
        </section>
      ) : null}

      {data.weaknesses && data.weaknesses.length > 0 ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="my-channel-weaknesses-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-neg-deep)]">
            ✕ CẦN CẢI THIỆN
          </p>
          <h3
            id="my-channel-weaknesses-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            {data.weaknesses.length} thứ nên sửa tuần này
          </h3>
          <p className="mt-1 mb-3.5 text-[12.5px] leading-snug text-[color:var(--gv-ink-3)]">
            Mỗi điểm: vấn đề là gì + tại sao xảy ra + cách sửa cụ thể.
          </p>
          <ChannelDiagnosticList kind="weakness" items={data.weaknesses} />
        </section>
      ) : null}

      <div className="grid grid-cols-1 gap-px bg-[color:var(--gv-rule)] sm:grid-cols-3">
        <div className="bg-[color:var(--gv-paper)] px-4 py-4 sm:px-5">
          <p className="gv-uc mb-1 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-ink-4)]">
            Followers
          </p>
          <p className="gv-tight text-2xl font-semibold tracking-[-0.03em] text-[color:var(--gv-ink)]">
            {formatFollowers(data.followers)}
          </p>
          <p className={kpiDeltaClass("—")}>—</p>
        </div>
        <div className="bg-[color:var(--gv-paper)] px-4 py-4 sm:px-5">
          <p className="gv-uc mb-1 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-ink-4)]">
            View TB / video
          </p>
          <p className="gv-tight text-2xl font-semibold tracking-[-0.03em] text-[color:var(--gv-ink)]">
            {formatViews(data.avg_views)}
          </p>
          <p className={kpiDeltaClass(viewDelta)}>{viewDelta}</p>
          <p className="gv-mono mt-0.5 text-[10px] text-[color:var(--gv-ink-4)]">
            {hasBench && bench ? `Ngách: ${formatViews(bench.avg_views_p50)}` : "Ngách: —"}
          </p>
        </div>
        <div className="bg-[color:var(--gv-paper)] px-4 py-4 sm:px-5">
          <p className="gv-uc mb-1 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-ink-4)]">
            Post/tuần
          </p>
          <p className="gv-tight text-2xl font-semibold tracking-[-0.03em] text-[color:var(--gv-ink)]">
            {postsPw != null ? String(postsPw) : "—"}
          </p>
          <p className={kpiDeltaClass("—")}>
            {hasBench && bench
              ? `vs ngách ${bench.posts_per_week_p50.toFixed(1).replace(/\.0$/, "")}`
              : data.posting_cadence?.trim()
                ? "vs ngách —"
                : "—"}
          </p>
          <p className="gv-mono mt-0.5 text-[10px] text-[color:var(--gv-ink-4)]">
            {hasBench && bench
              ? `Top 25%: ${bench.posts_per_week_p75.toFixed(1).replace(/\.0$/, "")}+`
              : "Top 25%: —"}
          </p>
        </div>
      </div>

      <div className="border-t border-[color:var(--gv-rule)] px-5 py-4 sm:px-6">
        <p className="gv-uc mb-3 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-ink-4)]">
          VỊ TRÍ TRONG NGÁCH {(data.niche_label || nicheLabel).toUpperCase()}
        </p>
        {hasBench && percentiles ? (
          <div className="flex flex-col gap-3">
            {percentiles.map((s) => (
              <PercentileBarRow key={s.label} spec={s} />
            ))}
          </div>
        ) : (
          // Niche has < MIN_BENCHMARK_SAMPLE creators meeting the
          // ``HAVING COUNT(*) >= 3`` cut. Surface why the bars are
          // missing instead of rendering a fake ranking.
          <p className="text-[12px] leading-snug text-[color:var(--gv-ink-3)]">
            Chưa đủ kênh trong ngách để dựng thước đo so sánh — quay lại sau khi corpus ngách dày hơn.
          </p>
        )}
      </div>

      {bw ? (
        <div className="grid grid-cols-1 gap-0 border-t border-[color:var(--gv-rule)] sm:grid-cols-2">
          <div className="border-b border-[color:var(--gv-rule)] px-5 py-4 sm:border-b-0 sm:border-r sm:px-6">
            <p className="gv-uc mb-2 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-pos-deep)]">
              ▲ Tuần này
            </p>
            <p className="text-[13px] font-medium leading-snug text-[color:var(--gv-ink)]">{bw.best.title}</p>
            <p className="mt-1 text-[11px] text-[color:var(--gv-ink-3)]">
              {formatViews(bw.best.views)} view ·{" "}
              <span className="font-semibold text-[color:var(--gv-pos-deep)]">
                {(bw.best.views / data.avg_views).toFixed(1).replace(".", ",")}× TB kênh
              </span>
            </p>
          </div>
          <div className="px-5 py-4 sm:px-6">
            <p className="gv-uc mb-2 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-neg-deep)]">
              ▼ Thấp nhất
            </p>
            <p className="text-[13px] font-medium leading-snug text-[color:var(--gv-ink)]">{bw.worst.title}</p>
            <p className="mt-1 text-[11px] text-[color:var(--gv-ink-3)]">
              {formatViews(bw.worst.views)} view ·{" "}
              <span className="font-semibold text-[color:var(--gv-ink-2)]">
                {Math.round((bw.worst.views / data.avg_views) * 100)}% TB kênh
              </span>
            </p>
          </div>
        </div>
      ) : null}

      <InsightsFooter lessons={data.lessons} />
    </div>
  );
}

export const HomeMyChannelSection = memo(function HomeMyChannelSection({
  profile,
  nicheLabel,
}: {
  profile: ProfileRow | null | undefined;
  nicheLabel: string;
}) {
  const navigate = useNavigate();
  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);
  const rawHandle = profileTikTok(profile);
  const handleKey = useMemo(() => channelAnalyzeHandleKey(rawHandle), [rawHandle]);
  const hasHandle = Boolean(handleKey);

  const { data, isPending, isError, error, refetch } = useChannelAnalyze({
    handle: handleKey,
    enabled: Boolean(hasHandle && cloudConfigured),
  });

  // Auto-refresh-on-stale: close the ~24h gap between the nightly batch
  // ingest and the live TikTok feed. The mutation is fire-and-forget —
  // server enforces the 18h staleness gate (returns ``cached`` if fresh,
  // ``refreshed`` if it actually scraped). When new rows land, the
  // mutation invalidates the channel-analyze query so we re-fetch the
  // updated response in the background. UI never blocks: cached data
  // renders immediately, fresh data swaps in on next render.
  const refreshMine = useRefreshMyChannel();
  const fireOnceRef = useRef(false);
  useEffect(() => {
    if (!hasHandle || !cloudConfigured) return;
    if (fireOnceRef.current) return;
    if (refreshMine.isPending || refreshMine.isSuccess || refreshMine.isError) return;
    fireOnceRef.current = true;
    refreshMine.mutate();
  }, [hasHandle, cloudConfigured, refreshMine]);

  const handleForUrl = handleKey ?? "";

  return (
    <section className="mb-12">
      <header
        className={[
          "mb-4 flex justify-between gap-4",
          hasHandle ? "items-end" : "items-start",
        ].join(" ")}
      >
        <div className="min-w-0 flex-1">
          <span className="gv-uc mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold text-[color:var(--gv-accent-deep)]">
            <span className="text-[color:var(--gv-accent)]" aria-hidden>
              ●
            </span>
            KÊNH CỦA BẠN
          </span>
          <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
            <h2 className="gv-tight m-0 text-[28px] font-semibold leading-none tracking-[-0.03em] text-[color:var(--gv-ink)]">
              {hasHandle ? (
                <>
                  Tóm tắt kênh{" "}
                  <span className="text-[color:var(--gv-ink)]">@{handleForUrl}</span>
                </>
              ) : (
                "Kết nối kênh TikTok của bạn"
              )}
            </h2>
            <p className="min-w-0 max-w-prose flex-1 text-[13px] leading-snug text-[color:var(--gv-ink-3)]">
              {hasHandle
                ? `Bạn ở đâu trong ngách ${nicheLabel} — và 3 việc nên làm tuần này.`
                : "Dán handle trong Cài đặt để Getviews hiển thị tóm tắt kênh ngay tại Studio — vị trí trong ngách, video nổi/tụt, gợi ý hành động."}
            </p>
          </div>
        </div>
        {hasHandle ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/settings")}>
              <Pencil className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
              Đổi kênh
            </Btn>
            <Btn
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => navigate(`/app/channel?handle=${encodeURIComponent(handleForUrl)}`)}
            >
              <span>Soi sâu kênh</span>
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            </Btn>
          </div>
        ) : null}
      </header>

      {!hasHandle ? (
        <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-8 sm:px-8">
          <p className="m-0 text-[15px] font-medium text-[color:var(--gv-ink)]">Chưa có TikTok handle trên hồ sơ</p>
          <p className="mt-2 text-[13px] leading-relaxed text-[color:var(--gv-ink-3)]">
            Thêm <span className="font-medium text-[color:var(--gv-ink)]">@handle</span> trong phần thiết lập để tự động tải tóm tắt kênh tại đây.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/settings")}>
              Mở cài đặt
            </Btn>
            <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/channel")}>
              Soi thử một kênh
            </Btn>
          </div>
        </div>
      ) : !cloudConfigured ? (
        <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-[13px] text-[color:var(--gv-ink-3)]">
          Cần cấu hình API để tải dữ liệu kênh.{" "}
          <Link to="/app/channel" className="font-semibold text-[color:var(--gv-ink)] underline-offset-2 hover:underline">
            Mở trang phân tích kênh
          </Link>
          .
        </div>
      ) : isPending ? (
        <div className="animate-pulse rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-8">
          <div className="h-6 w-48 rounded bg-[color:var(--gv-rule)]" />
          <div className="mt-6 h-32 w-full rounded bg-[color:var(--gv-rule)]" />
        </div>
      ) : isError ? (
        <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6">
          <p className="m-0 text-[15px] font-medium text-[color:var(--gv-neg-deep)]">Chưa tải được tóm tắt kênh</p>
          <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">{(error as Error)?.message ?? "Lỗi không xác định"}</p>
          <Btn className="mt-4" variant="ghost" size="sm" type="button" onClick={() => void refetch()}>
            Thử lại
          </Btn>
        </div>
      ) : data ? (
        <ConnectedCard data={data} nicheLabel={nicheLabel} handleDisplay={handleForUrl} />
      ) : null}
    </section>
  );
});
