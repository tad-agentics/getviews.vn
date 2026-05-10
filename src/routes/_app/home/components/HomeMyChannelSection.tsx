import { memo, useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowRight, RefreshCw, Search, Shield } from "lucide-react";
import { Btn } from "@/components/v2/Btn";
import { channelAnalyzeHandleKey, useChannelAnalyze } from "@/hooks/useChannelAnalyze";
import { ChannelBridgeRibbon } from "./ChannelBridgeRibbon";
import { ChannelCadenceBlock } from "./ChannelCadenceBlock";
import { ChannelDiagnosticList } from "./ChannelDiagnosticList";
import { ChannelPulseBlock } from "./ChannelPulseBlock";
import { ChannelRecent7dList } from "./ChannelRecent7dList";
import { scrollToSuggestionsTier, type SuggestionsTier } from "./scrollToTier";
import type { ChannelAnalyzeResponse } from "@/lib/api-types";
import { env } from "@/lib/env";
import { formatFollowers, formatRelativeSinceVi, formatViews } from "@/lib/formatters";

const HANDLE_REGEX = /(?:tiktok\.com\/@|^@)([A-Za-z0-9._]+)/;
const EXAMPLE_HANDLES: ReadonlyArray<string> = ["@an.tech", "@chinasecrets", "@aifreelance"];
const CREDIT_COST = 3;

function parseHandle(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const match = trimmed.match(HANDLE_REGEX);
  if (match) return `@${match[1]}`;
  if (trimmed.startsWith("@")) return trimmed;
  if (/^[A-Za-z0-9._]+$/.test(trimmed)) return `@${trimmed}`;
  return null;
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

// ── Input card ────────────────────────────────────────────────────────

function ExploreInputCard({
  inputValue,
  setInputValue,
  onSubmit,
  credits,
}: {
  inputValue: string;
  setInputValue: (v: string) => void;
  onSubmit: () => void;
  credits: number;
}) {
  const validHandle = useMemo(() => parseHandle(inputValue), [inputValue]);
  const hasCredits = credits >= CREDIT_COST;

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (validHandle && hasCredits) onSubmit();
      }
    },
    [onSubmit, validHandle, hasCredits],
  );

  return (
    <div className="overflow-hidden rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      <div
        className="border-b border-[color:var(--gv-rule)] px-6 py-6 sm:px-7 sm:py-7"
        style={{
          background:
            "linear-gradient(135deg, color-mix(in srgb, var(--gv-accent) 4%, transparent) 0%, color-mix(in srgb, var(--gv-accent-2) 4%, transparent) 100%)",
        }}
      >
        <div
          className="flex items-stretch overflow-hidden rounded-[12px] border-[1.5px] border-[color:var(--gv-ink)] bg-[color:var(--gv-canvas)]"
          style={{ boxShadow: "3px 3px 0 var(--gv-ink)" }}
        >
          <span
            className="gv-mono flex shrink-0 items-center border-r border-[color:var(--gv-rule)] px-3.5 text-[13px] text-[color:var(--gv-ink-3)]"
            aria-hidden
          >
            tiktok.com/
          </span>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="@handle  hoặc dán link đầy đủ"
            aria-label="Handle hoặc URL kênh TikTok"
            className="min-w-0 flex-1 border-0 bg-transparent px-4 py-3.5 text-[15px] font-medium text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)]"
          />
          <button
            type="button"
            onClick={onSubmit}
            disabled={!validHandle || !hasCredits}
            className={
              "flex shrink-0 items-center gap-1.5 border-l border-[color:var(--gv-rule)] px-5 text-[13px] font-semibold text-[color:var(--gv-canvas)] transition-colors " +
              (validHandle && hasCredits
                ? "bg-[color:var(--gv-ink)] hover:bg-[color:var(--gv-ink-2)]"
                : "cursor-not-allowed bg-[color:var(--gv-ink-2)] opacity-60")
            }
          >
            Khám
            <ArrowRight className="h-3 w-3" strokeWidth={2.4} aria-hidden />
          </button>
        </div>

        <div className="mt-3.5 flex flex-wrap items-center gap-2 text-[11px] text-[color:var(--gv-ink-3)]">
          <span>Ví dụ:</span>
          {EXAMPLE_HANDLES.map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => setInputValue(h)}
              className="gv-mono rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-2.5 py-1 text-[11px] text-[color:var(--gv-ink-2)] hover:border-[color:var(--gv-ink)]"
            >
              {h}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 text-[11px] text-[color:var(--gv-ink-3)] sm:px-6">
        <div className="flex items-center gap-1.5">
          <Shield className="h-3 w-3 shrink-0" strokeWidth={1.6} aria-hidden />
          <span>Chỉ đọc dữ liệu công khai. Không cần đăng nhập TikTok.</span>
        </div>
        <span
          className={
            "gv-mono rounded-full px-2.5 py-0.5 text-[10px] font-semibold " +
            (hasCredits
              ? "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]"
              : "bg-[color:var(--gv-neg-pale)] text-[color:var(--gv-neg-deep)]")
          }
        >
          {hasCredits ? `${CREDIT_COST} credit / lần` : `Cần ${CREDIT_COST} credit · còn ${credits}`}
        </span>
      </div>
    </div>
  );
}

// ── Result card ───────────────────────────────────────────────────────

function ResultCard({
  data,
  handleDisplay,
  onRescan,
  isRescanning,
}: {
  data: ChannelAnalyzeResponse;
  handleDisplay: string;
  onRescan: () => void;
  isRescanning: boolean;
}) {
  const navigate = useNavigate();
  const at = handleDisplay.startsWith("@") ? handleDisplay : `@${handleDisplay}`;

  const handleBridgeClick = useCallback((tier: SuggestionsTier) => {
    scrollToSuggestionsTier(tier);
  }, []);
  const handleScrollToSuggestions = useCallback(() => scrollToSuggestionsTier("01"), []);

  const computedAt = data.computed_at ? new Date(data.computed_at) : null;
  const computedAtLabel = formatRelativeSinceVi(new Date(), computedAt);

  return (
    <div className="overflow-hidden rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      {/* Card header */}
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
              {nicheShortLabel(data.niche_label || data.handle)}
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
              className={"h-3.5 w-3.5 " + (isRescanning ? "animate-spin" : "")}
              strokeWidth={2}
              aria-hidden
            />
            {isRescanning ? "Đang khám…" : "Khám lại"}
          </Btn>
          <Btn
            variant="ghost"
            size="sm"
            type="button"
            onClick={() =>
              navigate(`/app/channel?handle=${encodeURIComponent(handleDisplay.replace(/^@/, ""))}`)
            }
          >
            <span>Soi sâu</span>
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
          </Btn>
        </div>
      </div>

      {data.pulse ? <ChannelPulseBlock pulse={data.pulse} /> : null}

      {data.recent_7d ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="channel-explorer-recent7d-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-ink-4)]">
            ● 7 NGÀY QUA
          </p>
          <h3
            id="channel-explorer-recent7d-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            Video gần nhất
          </h3>
          <p className="mt-1 mb-3.5 text-[12.5px] leading-snug text-[color:var(--gv-ink-3)]">
            Sắp theo độ lệch so với view trung bình kênh ({formatViews(data.avg_views)}).
          </p>
          <ChannelRecent7dList rows={data.recent_7d} />
        </section>
      ) : null}

      {data.strengths && data.strengths.length > 0 ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="channel-explorer-strengths-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-pos-deep)]">
            ▲ ĐANG TỐT
          </p>
          <h3
            id="channel-explorer-strengths-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            {data.strengths.length} thứ kênh đang làm tốt
          </h3>
          <ChannelDiagnosticList kind="strength" items={data.strengths} onBridgeClick={handleBridgeClick} />
        </section>
      ) : null}

      {data.weaknesses && data.weaknesses.length > 0 ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="channel-explorer-weaknesses-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-neg-deep)]">
            ✕ CẦN CẢI THIỆN
          </p>
          <h3
            id="channel-explorer-weaknesses-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            {data.weaknesses.length} thứ nên sửa tuần này
          </h3>
          <ChannelDiagnosticList kind="weakness" items={data.weaknesses} onBridgeClick={handleBridgeClick} />
        </section>
      ) : null}

      {data.cadence ? (
        <section
          className="border-b border-[color:var(--gv-rule)] px-5 py-5 sm:px-6"
          aria-labelledby="channel-explorer-cadence-title"
        >
          <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-ink-4)]">
            ◷ NHỊP ĐĂNG
          </p>
          <h3
            id="channel-explorer-cadence-title"
            className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
          >
            {data.cadence.weekly_actual}/{data.cadence.weekly_target} tuần này
          </h3>
          <ChannelCadenceBlock cadence={data.cadence} />
        </section>
      ) : null}

      {(data.strengths && data.strengths.length > 0) || (data.weaknesses && data.weaknesses.length > 0) ? (
        <ChannelBridgeRibbon onScrollToSuggestions={handleScrollToSuggestions} />
      ) : null}
    </div>
  );
}

// ── Main section ──────────────────────────────────────────────────────

export const HomeMyChannelSection = memo(function HomeMyChannelSection({
  credits,
}: {
  credits: number;
}) {
  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);
  const [inputValue, setInputValue] = useState("");
  const [submittedHandle, setSubmittedHandle] = useState<string | null>(null);

  const handleKey = useMemo(() => channelAnalyzeHandleKey(submittedHandle), [submittedHandle]);

  const { data, isPending, isError, error, isFetching, refetch } = useChannelAnalyze({
    handle: handleKey,
    enabled: Boolean(handleKey && cloudConfigured),
  });

  const hasResult = Boolean(handleKey);

  const handleSubmit = useCallback(() => {
    const parsed = parseHandle(inputValue);
    if (!parsed) return;
    const key = channelAnalyzeHandleKey(parsed);
    setSubmittedHandle(key);
  }, [inputValue]);

  const handleRescan = useCallback(() => {
    void refetch();
  }, [refetch]);

  const handleReset = useCallback(() => {
    setSubmittedHandle(null);
    setInputValue("");
  }, []);

  return (
    <section className="mb-12">
      <header className="mb-4 flex min-w-0 flex-col gap-2">
        <span className="gv-uc flex items-center gap-1.5 text-[10px] font-semibold text-[color:var(--gv-accent-deep)]">
          <Search className="h-3 w-3 text-[color:var(--gv-accent)]" aria-hidden />
          KHÁM KÊNH
        </span>
        <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-baseline sm:gap-x-3 sm:gap-y-1">
          <h2 className="gv-tight m-0 w-full text-[22px] font-semibold leading-[1.1] tracking-[-0.03em] text-[color:var(--gv-ink)] sm:w-auto sm:max-w-[min(100%,36rem)] sm:text-[26px] sm:leading-none lg:text-[28px]">
            {hasResult && submittedHandle ? (
              <>
                Phân tích kênh{" "}
                <span className="break-all text-[color:var(--gv-ink)] sm:break-normal">
                  {submittedHandle.startsWith("@") ? submittedHandle : `@${submittedHandle}`}
                </span>
              </>
            ) : (
              "Khám bất kỳ kênh TikTok nào"
            )}
          </h2>
          <p className="min-w-0 w-full text-[12.5px] leading-relaxed text-[color:var(--gv-ink-3)] sm:max-w-prose sm:flex-1 sm:text-[13px] sm:leading-snug">
            {hasResult ? (
              <>Phân tích 60 video gần nhất — điểm mạnh, điểm yếu, nhịp đăng, và 3 việc nên làm tuần này.</>
            ) : (
              <>
                <span className="sm:hidden">
                  Dán @handle hoặc link TikTok — GetViews phân tích kênh bất kỳ trong ngách.
                </span>
                <span className="hidden sm:inline">
                  Dán @handle hoặc link kênh TikTok. GetViews đọc 60 video gần nhất, so sánh với kho video ngách, và trả về
                  chẩn đoán: đang tốt ở đâu, tụt ở đâu, tuần này nên tập trung vào hướng nào.
                </span>
              </>
            )}
          </p>
        </div>
      </header>

      {!hasResult ? (
        !cloudConfigured ? (
          <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-[13px] text-[color:var(--gv-ink-3)]">
            Cần cấu hình Cloud Run API để phân tích kênh.
          </div>
        ) : (
          <ExploreInputCard
            inputValue={inputValue}
            setInputValue={setInputValue}
            onSubmit={handleSubmit}
            credits={credits}
          />
        )
      ) : (
        <>
          {isPending ? (
            <div className="animate-pulse rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-8">
              <div className="h-6 w-48 rounded bg-[color:var(--gv-rule)]" />
              <div className="mt-6 h-32 w-full rounded bg-[color:var(--gv-rule)]" />
              <div className="mt-4 h-24 w-full rounded bg-[color:var(--gv-rule)]" />
            </div>
          ) : isError ? (
            <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6">
              {(error as Error)?.name === "InsufficientCredits" ? (
                <>
                  <p className="m-0 text-[15px] font-medium text-[color:var(--gv-neg-deep)]">
                    Không đủ credit để phân tích
                  </p>
                  <p className="mt-2 text-[13px] text-[color:var(--gv-ink-3)]">
                    Phân tích kênh tốn {CREDIT_COST} credit. Bạn còn {credits} credit.
                  </p>
                </>
              ) : (
                <>
                  <p className="m-0 text-[15px] font-medium text-[color:var(--gv-neg-deep)]">
                    Không tải được phân tích kênh
                  </p>
                  <p className="mt-2 text-[13px] text-[color:var(--gv-ink-3)]">
                    {(error as Error)?.message ?? "Lỗi không xác định"}
                  </p>
                </>
              )}
              <Btn className="mt-4" variant="ghost" size="sm" type="button" onClick={handleReset}>
                Thử kênh khác
              </Btn>
            </div>
          ) : data ? (
            <ResultCard
              data={data}
              handleDisplay={submittedHandle ?? data.handle}
              onRescan={handleRescan}
              isRescanning={isFetching && !isPending}
            />
          ) : null}

          {/* Always show "Khám kênh khác" link when a result (or error) is visible */}
          {!isPending ? (
            <div className="mt-4 flex items-center justify-end">
              <button
                type="button"
                onClick={handleReset}
                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[color:var(--gv-ink-3)] transition-colors hover:text-[color:var(--gv-ink)]"
              >
                <Search className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
                Khám kênh khác
              </button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
});
