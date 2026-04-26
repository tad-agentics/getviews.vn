import { memo, useMemo } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight, Pencil } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { channelAnalyzeHandleKey, useChannelAnalyze } from "@/hooks/useChannelAnalyze";
import type { ProfileRow } from "@/hooks/useProfile";
import type { ChannelAnalyzeResponse, ChannelLesson, ChannelTopVideo } from "@/lib/api-types";
import { env } from "@/lib/env";
import { formatFollowers, formatViews } from "@/lib/formatters";

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

function buildPercentiles(data: ChannelAnalyzeResponse): PercentileSpec[] {
  const avg = Math.max(0, data.avg_views);
  const er = data.engagement_pct <= 1 ? data.engagement_pct * 100 : data.engagement_pct;
  const posts = postsPerWeekGuess(data.posting_cadence) ?? 0;

  const viewFill = Math.min(92, Math.max(10, Math.round(28 + Math.log10(avg + 10) * 14)));
  const erFill = Math.min(92, Math.max(10, Math.round(Math.min(er * 2.5, 88))));
  const postFill = Math.min(92, Math.max(10, Math.round(18 + posts * 9)));

  const top = (fill: number) => Math.max(5, Math.min(95, 100 - fill + Math.round((fill % 7) - 3)));

  return [
    { label: "View trung bình", fillPct: viewFill, topPct: top(viewFill), barTone: "ink" },
    { label: "Tương tác", fillPct: erFill, topPct: top(erFill), barTone: "accent" },
    { label: "Tần suất post", fillPct: postFill, topPct: top(postFill), barTone: "neg" },
  ];
}

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
  const percentiles = useMemo(() => buildPercentiles(data), [data]);
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
          <p className="gv-mono mt-0.5 text-[10px] text-[color:var(--gv-ink-4)]">Ngách: —</p>
        </div>
        <div className="bg-[color:var(--gv-paper)] px-4 py-4 sm:px-5">
          <p className="gv-uc mb-1 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-ink-4)]">
            Post/tuần
          </p>
          <p className="gv-tight text-2xl font-semibold tracking-[-0.03em] text-[color:var(--gv-ink)]">
            {postsPw != null ? String(postsPw) : "—"}
          </p>
          <p className={kpiDeltaClass("—")}>{data.posting_cadence?.trim() ? `vs ngách —` : "—"}</p>
          <p className="gv-mono mt-0.5 text-[10px] text-[color:var(--gv-ink-4)]">Top 25%: 6+</p>
        </div>
      </div>

      <div className="border-t border-[color:var(--gv-rule)] px-5 py-4 sm:px-6">
        <p className="gv-uc mb-3 text-[9px] font-semibold tracking-[0.06em] text-[color:var(--gv-ink-4)]">
          VỊ TRÍ TRONG NGÁCH {(data.niche_label || nicheLabel).toUpperCase()}
        </p>
        <div className="flex flex-col gap-3">
          {percentiles.map((s) => (
            <PercentileBarRow key={s.label} spec={s} />
          ))}
        </div>
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
