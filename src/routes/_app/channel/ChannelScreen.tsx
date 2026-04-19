import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ArrowLeft, Loader2, Play } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { SectionMini } from "@/components/SectionMini";
import { Btn } from "@/components/v2/Btn";
import { Chip } from "@/components/v2/Chip";
import { FormulaBar } from "@/components/v2/FormulaBar";
import { KpiGrid } from "@/components/v2/KpiGrid";
import { TopBar } from "@/components/v2/TopBar";
import { useHomePulse } from "@/hooks/useHomePulse";
import { channelAnalyzeHandleKey, useChannelAnalyze } from "@/hooks/useChannelAnalyze";
import { env } from "@/lib/env";
import type { ChannelAnalyzeResponse, VideoKpi } from "@/lib/api-types";
import { formatFollowers, formatRelativeSinceVi, formatViews } from "@/lib/formatters";

function formatViewsVi(n: number): string {
  return n.toLocaleString("vi-VN");
}

function engagementDisplay(pct: number): string {
  if (pct <= 0) return "—";
  const v = pct <= 1 ? pct * 100 : pct;
  return `${v.toFixed(1)}%`;
}

function kpiDeltaClassName(delta: string): string | undefined {
  const base = "gv-mono mt-1.5 text-[10px]";
  if (/↓|−/.test(delta) || /-\s*\d/.test(delta)) {
    return `${base} text-[color:var(--gv-neg-deep)]`;
  }
  if (/↑|\+/.test(delta)) {
    return `${base} text-[color:var(--gv-pos-deep)]`;
  }
  if (delta === "—" || delta.trim() === "") {
    return `${base} text-[color:var(--gv-ink-4)]`;
  }
  return `${base} text-[color:var(--gv-ink-3)]`;
}

function mapChannelKpis(data: ChannelAnalyzeResponse): VideoKpi[] {
  return data.kpis.map((k) => ({
    label: k.label,
    value: k.value,
    delta: k.delta,
    deltaClassName: kpiDeltaClassName(k.delta),
  }));
}

function channelInitial(name: string, handle: string): string {
  const s = (name?.trim() || handle).trim();
  if (!s) return "?";
  return s[0]?.toUpperCase() ?? "?";
}

export default function ChannelScreen() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const rawHandle = searchParams.get("handle");
  const handleKey = useMemo(() => channelAnalyzeHandleKey(rawHandle), [rawHandle]);
  const forceRefresh =
    searchParams.get("force_refresh") === "1" || searchParams.get("force_refresh") === "true";
  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);
  const { data: pulse } = useHomePulse(cloudConfigured);

  const asOf = useMemo(() => {
    if (!pulse?.as_of) return null;
    const d = new Date(pulse.as_of);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [pulse?.as_of]);
  const asOfRelative = useMemo(() => formatRelativeSinceVi(new Date(), asOf), [asOf]);

  const { data, isPending, isError, error, refetch, isFetching } = useChannelAnalyze({
    handle: rawHandle,
    forceRefresh,
    enabled: Boolean(handleKey && cloudConfigured),
  });

  const [draftHandle, setDraftHandle] = useState("");

  const openHandle = (h: string) => {
    const k = channelAnalyzeHandleKey(h);
    if (!k) return;
    setSearchParams({ handle: k }, { replace: true });
  };

  const emptyParams = !handleKey;

  return (
    <AppLayout enableMobileSidebar>
      <TopBar
        kicker="ĐỐI THỦ"
        title="Phân Tích Kênh"
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
            <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/kol")}>
              KOL
            </Btn>
          </>
        }
      />
      <main className="gv-route-main gv-route-main--1280">
        <div className="mb-5">
          <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app")}>
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            Về Studio
          </Btn>
        </div>

        {emptyParams ? (
          <div className="flex flex-col gap-6">
            <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6 text-center text-[color:var(--gv-ink-3)]">
              <p className="gv-tight m-0 text-lg text-[color:var(--gv-ink)]">Soi kênh trong corpus</p>
              <p className="mt-2 text-sm">
                Thêm <span className="font-[family-name:var(--gv-font-mono)]">?handle=tiktok</span> vào URL, hoặc
                nhập handle bên dưới.
              </p>
            </div>
            <form
              className="flex flex-col gap-3 sm:flex-row sm:items-end"
              onSubmit={(e) => {
                e.preventDefault();
                openHandle(draftHandle);
              }}
            >
              <label className="flex min-w-0 flex-1 flex-col gap-1.5 text-left">
                <span className="gv-mono text-[10px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">
                  Handle TikTok
                </span>
                <input
                  value={draftHandle}
                  onChange={(e) => setDraftHandle(e.target.value)}
                  placeholder="@creator hoặc creator"
                  className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2.5 text-sm text-[color:var(--gv-ink)] outline-none focus:border-[color:var(--gv-ink)]"
                  autoComplete="off"
                />
              </label>
              <Btn type="submit" variant="ink" size="md" disabled={!draftHandle.trim()}>
                Mở phân tích
              </Btn>
            </form>
            {!cloudConfigured ? (
              <p className="text-sm text-[color:var(--gv-ink-3)]">
                Cần <span className="font-[family-name:var(--gv-font-mono)]">VITE_CLOUD_RUN_API_URL</span> trong môi
                trường build.
              </p>
            ) : null}
          </div>
        ) : !cloudConfigured ? (
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Phân tích kênh cần <span className="font-[family-name:var(--gv-font-mono)]">VITE_CLOUD_RUN_API_URL</span>{" "}
            trong môi trường build.
          </p>
        ) : isPending || isFetching ? (
          <div
            className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-[color:var(--gv-ink-3)]"
            role="status"
            aria-label="Đang tải phân tích kênh"
          >
            <Loader2 className="h-8 w-8 animate-spin text-[color:var(--gv-accent)]" strokeWidth={1.5} />
            <span className="text-sm">Đang tải phân tích kênh…</span>
          </div>
        ) : isError ? (
          <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
            <p className="gv-tight m-0 text-lg text-[color:var(--gv-neg-deep)]">Không tải được phân tích</p>
            <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">{error?.message ?? "Lỗi không xác định"}</p>
            <Btn className="mt-4" type="button" variant="ghost" onClick={() => refetch()}>
              Thử lại
            </Btn>
          </div>
        ) : data ? (
          <ChannelBody data={data} handleDisplay={handleKey ?? data.handle} onChangeHandle={openHandle} />
        ) : null}
      </main>
    </AppLayout>
  );
}

function ChannelBody({
  data,
  handleDisplay,
  onChangeHandle,
}: {
  data: ChannelAnalyzeResponse;
  handleDisplay: string;
  onChangeHandle: (h: string) => void;
}) {
  const [another, setAnother] = useState("");
  const nicheKicker = data.niche_label?.trim()
    ? `HỒ SƠ KÊNH · ${data.niche_label.trim().toUpperCase()}`
    : "HỒ SƠ KÊNH";
  const at = handleDisplay.startsWith("@") ? handleDisplay : `@${handleDisplay}`;
  const kpis = useMemo(() => mapChannelKpis(data), [data]);

  return (
    <div className="flex flex-col gap-7">
      <form
        className="flex flex-col gap-2 border-b border-[color:var(--gv-rule)] pb-4 sm:flex-row sm:items-end sm:gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          onChangeHandle(another);
        }}
      >
        <label className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="gv-mono text-[10px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">
            Kênh khác
          </span>
          <input
            value={another}
            onChange={(e) => setAnother(e.target.value)}
            placeholder={at}
            className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-sm text-[color:var(--gv-ink)] outline-none focus:border-[color:var(--gv-ink)]"
            autoComplete="off"
          />
        </label>
        <Btn type="submit" variant="ghost" size="sm" disabled={!another.trim()}>
          Tải
        </Btn>
      </form>

      {/* Hero — ref channel.jsx ch-hero */}
      <div className="ch-hero grid gap-8 rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-7 min-[900px]:grid-cols-2">
        <div>
          <div className="gv-uc mb-2.5 text-[9.5px] text-[color:var(--gv-ink-4)]">{nicheKicker}</div>
          <div className="mb-3.5 flex items-center gap-4">
            <div
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-[color:var(--gv-accent)] text-[22px] font-medium text-white gv-tight"
              aria-hidden
            >
              {channelInitial(data.name, data.handle)}
            </div>
            <div className="min-w-0">
              <h2 className="gv-tight m-0 truncate text-[38px] leading-none text-[color:var(--gv-ink)]">
                {data.name || data.handle}
              </h2>
              <p className="gv-mono mt-1 text-xs text-[color:var(--gv-ink-3)]">
                {at} · {formatFollowers(data.followers)} follower
              </p>
            </div>
          </div>
          {data.bio ? (
            <p className="gv-tight m-0 max-w-[460px] text-lg italic leading-snug text-[color:var(--gv-ink-2)]">
              &ldquo;{data.bio}&rdquo;
            </p>
          ) : (
            <p className="text-sm text-[color:var(--gv-ink-4)]">Chưa có bio trong corpus.</p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {data.posting_cadence ? (
              <Chip size="md" variant="default">
                Đăng {data.posting_cadence}
              </Chip>
            ) : null}
            <Chip size="md" variant="accent">
              Engagement {engagementDisplay(data.engagement_pct)}
            </Chip>
            <Chip size="md" variant="default">
              {formatViewsVi(data.total_videos)} video
            </Chip>
          </div>
        </div>
        <div className="self-center">
          <KpiGrid kpis={kpis} />
        </div>
      </div>

      <section>
        <SectionMini
          kicker="CÔNG THỨC PHÁT HIỆN"
          title={`"${data.name || data.handle} Formula" — các bước lặp lại`}
        />
        <FormulaBar steps={data.formula} formulaGate={data.formula_gate} />
      </section>

      {/* Two col — ref ch-grid */}
      <div className="ch-grid grid gap-8 min-[900px]:grid-cols-2">
        <div>
          <SectionMini kicker="VIDEO ĐỈNH" title="Top video gây tiếng vang" />
          <div className="grid grid-cols-2 gap-3">
            {data.top_videos.slice(0, 4).map((v) => (
              <Link
                key={v.video_id}
                to={`/app/video?video_id=${encodeURIComponent(v.video_id)}`}
                className="group block text-left"
              >
                <div
                  className="relative aspect-[9/16] overflow-hidden rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
                  style={
                    v.bg_color
                      ? { backgroundColor: v.bg_color }
                      : undefined
                  }
                >
                  {v.thumbnail_url ? (
                    <img
                      src={v.thumbnail_url}
                      alt=""
                      className="absolute inset-0 h-full w-full object-cover"
                      loading="lazy"
                    />
                  ) : null}
                  <div className="absolute inset-x-2.5 bottom-2 flex items-center gap-1 text-white drop-shadow-md">
                    <Play className="h-3 w-3 shrink-0 opacity-90" aria-hidden />
                    <span className="gv-mono text-[10px]">↑ {formatViews(v.views)}</span>
                  </div>
                </div>
                <p className="mt-1.5 line-clamp-2 text-[11px] text-[color:var(--gv-ink-3)] group-hover:text-[color:var(--gv-ink)]">
                  {v.title}
                </p>
              </Link>
            ))}
          </div>
        </div>
        <div>
          <SectionMini kicker="ĐIỀU NÊN COPY" title="Học gì từ kênh này" />
          <div className="flex flex-col gap-2">
            {data.lessons.length === 0 ? (
              <p className="text-sm text-[color:var(--gv-ink-3)]">
                {data.formula_gate === "thin_corpus"
                  ? "Cần ≥10 video trong ngách để tổng hợp bài học."
                  : "Chưa có bài học từ mô hình."}
              </p>
            ) : (
              data.lessons.map((lesson, i) => (
                <div
                  key={`${lesson.title}-${i}`}
                  className="flex gap-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3.5"
                >
                  <span className="gv-mono shrink-0 text-xs font-semibold text-[color:var(--gv-accent-deep)]">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p className="m-0 text-[13px] font-medium text-[color:var(--gv-ink)]">{lesson.title}</p>
                    <p className="mt-0.5 text-xs leading-snug text-[color:var(--gv-ink-3)]">{lesson.body}</p>
                  </div>
                </div>
              ))
            )}
          </div>
          <Btn className="mt-4 w-full justify-center" variant="accent" type="button" disabled title="Sắp có">
            Tạo kịch bản theo công thức này
          </Btn>
        </div>
      </div>

      {data.computed_at ? (
        <p className="gv-mono text-center text-[10px] text-[color:var(--gv-ink-4)]">
          Phân tích kênh cập nhật: {new Date(data.computed_at).toLocaleString("vi-VN")}
          {data.cache_hit === true ? " · cache" : null}
        </p>
      ) : null}
    </div>
  );
}
