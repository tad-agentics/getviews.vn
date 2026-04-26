import { memo, useCallback, useEffect, useMemo, useRef } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowRight, RefreshCw } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { channelAnalyzeHandleKey, useChannelAnalyze } from "@/hooks/useChannelAnalyze";
import type { ProfileRow } from "@/hooks/useProfile";
import { useRefreshMyChannel } from "@/hooks/useRefreshMyChannel";
import type { ChannelAnalyzeResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { formatFollowers, formatRelativeSinceVi, formatViews } from "@/lib/formatters";
import { ChannelBridgeRibbon } from "./ChannelBridgeRibbon";
import { ChannelCadenceBlock } from "./ChannelCadenceBlock";
import { ChannelDiagnosticList } from "./ChannelDiagnosticList";
import { ChannelPulseBlock } from "./ChannelPulseBlock";
import { ChannelRecent7dList } from "./ChannelRecent7dList";
import { ConnectChannelCard } from "./ConnectChannelCard";
import { scrollToSuggestionsTier, type SuggestionsTier } from "./scrollToTier";

function profileTikTok(p: ProfileRow | null | undefined): string | null {
  const h = (p as { tiktok_handle?: string | null } | null | undefined)?.tiktok_handle;
  return h?.trim() || null;
}

function channelInitial(name: string, handle: string): string {
  const s = (name?.trim() || handle).trim();
  if (!s) return "?";
  return s[0]?.toUpperCase() ?? "?";
}

function nicheShortLabel(full: string): string {
  const t = full.trim();
  if (t.length <= 24) return t;
  return `${t.slice(0, 22)}…`;
}

function ConnectedCard({
  data,
  nicheLabel,
  handleDisplay,
  onRescan,
  isRescanning,
}: {
  data: ChannelAnalyzeResponse;
  nicheLabel: string;
  handleDisplay: string;
  onRescan: () => void;
  isRescanning: boolean;
}) {
  const navigate = useNavigate();
  const at = handleDisplay.startsWith("@") ? handleDisplay : `@${handleDisplay}`;
  // PR-4 — diagnostic bridge pills + bottom ribbon scroll into the
  // GỢI Ý HÔM NAY tier section that lives further down on HomeScreen.
  const handleBridgeClick = useCallback(
    (tier: SuggestionsTier) => {
      scrollToSuggestionsTier(tier);
    },
    [],
  );
  const handleScrollToSuggestions = useCallback(
    () => scrollToSuggestionsTier("01"),
    [],
  );

  // PR-cleanup-B — design pack §"Cập nhật {asOf}" mono timestamp on the
  // inner card header. Reads ``data.computed_at`` (ISO from the cached
  // ``channel_formulas`` row or fresh run); falls through to "—" when
  // missing on legacy responses.
  const computedAt = data.computed_at ? new Date(data.computed_at) : null;
  const computedAtLabel = formatRelativeSinceVi(new Date(), computedAt);

  return (
    <div className="overflow-hidden rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--gv-rule)] px-5 py-4 sm:px-6 sm:py-[18px]">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[16px] font-bold text-white"
            style={{
              background: "linear-gradient(135deg, var(--gv-accent) 0%, var(--gv-accent-2) 100%)",
            }}
            aria-hidden
          >
            {channelInitial(data.name, data.handle)}
          </div>
          <div className="min-w-0">
            <p className="gv-tight truncate text-[14px] font-semibold tracking-[-0.01em] text-[color:var(--gv-ink)]">
              {at}
            </p>
            <p className="mt-0.5 text-[11.5px] text-[color:var(--gv-ink-3)]">
              {nicheShortLabel(data.niche_label || nicheLabel)}
              {data.followers > 0 ? <> · {formatFollowers(data.followers)} follow</> : null}
              {" · "}
              {data.total_videos.toLocaleString("vi-VN")} video
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2.5">
          <span className="gv-mono hidden text-[10.5px] text-[color:var(--gv-ink-4)] sm:inline">
            Cập nhật {computedAtLabel}
          </span>
          <Btn
            variant="ghost"
            size="sm"
            type="button"
            disabled={isRescanning}
            onClick={onRescan}
            title="Khám lại — đọc lại 60 video gần nhất"
          >
            <RefreshCw
              className={
                "h-3.5 w-3.5 " + (isRescanning ? "animate-spin" : "")
              }
              strokeWidth={2}
              aria-hidden
            />
            {isRescanning ? "Đang khám…" : "Khám lại"}
          </Btn>
          <Btn
            variant="ghost"
            size="sm"
            type="button"
            onClick={() => navigate(`/app/channel?handle=${encodeURIComponent(handleDisplay.replace(/^@/, ""))}`)}
          >
            <span>Soi sâu</span>
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
          </Btn>
        </div>
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
          <ChannelDiagnosticList
            kind="strength"
            items={data.strengths}
            onBridgeClick={handleBridgeClick}
          />
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
          <ChannelDiagnosticList
            kind="weakness"
            items={data.weaknesses}
            onBridgeClick={handleBridgeClick}
          />
        </section>
      ) : null}

      {/* PR-3 — NHỊP ĐĂNG block: 14-day calendar + best hour/day pair.
       * Hidden when the BE returned ``cadence: null`` (insufficient
       * temporal data). */}
      {data.cadence ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="my-channel-cadence-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-ink-4)]">
            ◷ NHỊP ĐĂNG
          </p>
          <h3
            id="my-channel-cadence-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            {data.cadence.weekly_actual}/{data.cadence.weekly_target} tuần này
            {data.pulse && data.pulse.streak_days > 0 ? (
              <span className="font-normal text-[color:var(--gv-ink-3)]">
                {" "}· streak {data.pulse.streak_days} ngày
              </span>
            ) : null}
          </h3>
          <p className="mt-1 mb-3.5 text-[12.5px] leading-snug text-[color:var(--gv-ink-3)]">
            Mỗi ô = 1 ngày. Đậm = đã đăng. Đo từ chính kênh bạn.
          </p>
          <ChannelCadenceBlock cadence={data.cadence} />
        </section>
      ) : null}

      {/* PR-4 — bottom bridge ribbon. Only renders when the diagnostic
       * blocks have content to bridge from; on legacy cached responses
       * (empty strengths/weaknesses) we suppress the ribbon since the
       * "đã ưu tiên các ý tưởng bám theo điểm mạnh & sửa điểm yếu" copy
       * would be misleading. */}
      {(data.strengths && data.strengths.length > 0)
        || (data.weaknesses && data.weaknesses.length > 0) ? (
        <ChannelBridgeRibbon onScrollToSuggestions={handleScrollToSuggestions} />
      ) : null}
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

  // PR-cleanup-B — manual rescan handler. Kicks the same mutation as
  // the auto-refresh, but bypasses the once-only guard so creators can
  // re-scan after they've posted a new video on TikTok and want the
  // numbers caught up immediately.
  const handleRescan = useCallback(() => {
    if (refreshMine.isPending) return;
    refreshMine.mutate();
  }, [refreshMine]);

  return (
    <section className="mb-12">
      {/* PR-cleanup-B — outer SectionHeader is now action-less per the
       * design pack (home.jsx:497-504). The Khám lại + Soi sâu actions
       * moved into the inner card header next to the channel identity
       * row so they sit closer to the data they affect. */}
      <header className="mb-4 flex flex-col gap-1 min-w-0">
        <span className="gv-uc flex items-center gap-1.5 text-[10px] font-semibold text-[color:var(--gv-accent-deep)]">
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
              : "Dán link để Getviews soi gương kênh của bạn — bạn ở đâu trong ngách, video nào đang lên / tụt, nên làm gì tuần này."}
          </p>
        </div>
      </header>

      {!hasHandle ? (
        // PR-cleanup-D — inline paste-flow card. Replaces the previous
        // "go to /app/settings" detour so new creators can connect
        // their kênh without leaving Studio.
        <ConnectChannelCard />
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
        <ConnectedCard
          data={data}
          nicheLabel={nicheLabel}
          handleDisplay={handleForUrl}
          onRescan={handleRescan}
          isRescanning={refreshMine.isPending}
        />
      ) : null}
    </section>
  );
});
