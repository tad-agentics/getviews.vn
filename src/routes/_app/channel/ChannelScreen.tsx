import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ArrowLeft, ArrowRight, FileText, Loader2, Search, Shield } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { SectionMini } from "@/components/SectionMini";
import { Btn } from "@/components/v2/Btn";
import { Chip } from "@/components/v2/Chip";
import { FormulaBar } from "@/components/v2/FormulaBar";
import { KpiGrid } from "@/components/v2/KpiGrid";
import { PostingHeatmap } from "@/components/v2/channel/PostingHeatmap";
import { TopBar } from "@/components/v2/TopBar";
import { DataFreshnessPill } from "@/components/v2/DataFreshnessPill";
import { useHomePulse } from "@/hooks/useHomePulse";
import { channelAnalyzeHandleKey, useChannelAnalyze } from "@/hooks/useChannelAnalyze";
import { useChannelUserSearch } from "@/hooks/useChannelUserSearch";
import { useCreatorNiches } from "@/hooks/useCreatorNiches";
import { useProfile } from "@/hooks/useProfile";
import { extractChannelHandleFromMessage, parseChannelExploreHandle } from "@/lib/channelHandle";
import { analysisErrorCopy } from "@/lib/errorMessages";
import { env } from "@/lib/env";
import { logUsage } from "@/lib/logUsage";
import { scriptPrefillFromChannel } from "@/lib/scriptPrefill";
import type { ChannelAnalyzeResponse, VideoKpi } from "@/lib/api-types";
import { formatFollowers, formatViews } from "@/lib/formatters";
import { ChannelBridgeRibbon } from "../home/components/ChannelBridgeRibbon";
import { ChannelCadenceBlock } from "../home/components/ChannelCadenceBlock";
import { ChannelDiagnosticList } from "../home/components/ChannelDiagnosticList";
import { ChannelPulseBlock } from "../home/components/ChannelPulseBlock";
import { ChannelRecent7dList } from "../home/components/ChannelRecent7dList";
import { goToStudioSuggestionsTier, type SuggestionsTier } from "../home/components/scrollToTier";

const CREDIT_COST = 3;

function formatViewsVi(n: number): string {
  return n.toLocaleString("vi-VN");
}

function engagementDisplay(pct: number): string {
  if (pct <= 0) return "—";
  const v = pct <= 1 ? pct * 100 : pct;
  return `${v.toFixed(1)}%`;
}

function postingCadenceChipText(cadence: string | null, time: string | null): string | null {
  const c = cadence?.trim();
  const t = time?.trim();
  if (c && t) return `${c} · ${t}`;
  if (c) return c;
  if (t) return t;
  return null;
}

function kpiDeltaClassName(delta: string): string | undefined {
  const base = "gv-mono mt-1 text-[10px]";
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
  const { data: profile } = useProfile();
  const { data: creatorNiches = [] } = useCreatorNiches();
  const rawHandle = searchParams.get("handle");
  const handleKey = useMemo(() => channelAnalyzeHandleKey(rawHandle), [rawHandle]);
  const creatorNicheParam = useMemo(() => {
    const r = searchParams.get("creator_niche_id");
    if (!r) return null;
    const n = parseInt(r, 10);
    return Number.isFinite(n) && n >= 1 ? n : null;
  }, [searchParams]);

  const forceRefresh =
    searchParams.get("force_refresh") === "1" || searchParams.get("force_refresh") === "true";
  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);
  const { data: pulse } = useHomePulse(cloudConfigured);

  const { data, isPending, isError, error, refetch, isFetching } = useChannelAnalyze({
    handle: rawHandle,
    creatorNicheId: creatorNicheParam,
    forceRefresh,
    enabled: Boolean(handleKey && cloudConfigured),
  });

  const [draftHandle, setDraftHandle] = useState("");
  const [handleError, setHandleError] = useState<string | null>(null);
  const [userSearchDraft, setUserSearchDraft] = useState("");
  const [debouncedUserSearch, setDebouncedUserSearch] = useState("");

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedUserSearch(userSearchDraft.trim()), 350);
    return () => window.clearTimeout(t);
  }, [userSearchDraft]);

  const {
    data: userSearchData,
    isFetching: userSearchLoading,
    isError: userSearchIsError,
    error: userSearchError,
  } = useChannelUserSearch(debouncedUserSearch);

  const credits = (profile as { deep_credits_remaining?: number } | null | undefined)?.deep_credits_remaining ?? 0;
  const hasCredits = credits >= CREDIT_COST;

  const openHandle = useCallback(
    (h: string) => {
      const trimmed = h.trim();
      if (!trimmed) {
        setHandleError("Nhập handle TikTok trước (ví dụ: @creator).");
        return;
      }
      const fromUrl = extractChannelHandleFromMessage(trimmed);
      const parsed = parseChannelExploreHandle(trimmed);
      const k =
        fromUrl ?? (parsed ? channelAnalyzeHandleKey(parsed) : null) ?? channelAnalyzeHandleKey(trimmed);
      if (!k) {
        setHandleError("Không nhận diện được handle — dán link profile hoặc nhập @creator.");
        return;
      }
      if (/\/(video|photo)\//i.test(trimmed)) {
        setHandleError("Link này là video, không phải kênh — chỉ phân tích kênh tại đây.");
        return;
      }
      setHandleError(null);
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("handle", k);
        next.delete("force_refresh");
        return next;
      }, { replace: true });
    },
    [setSearchParams],
  );

  const emptyParams = !handleKey;

  const nicheSelectValue = String(
    creatorNicheParam ?? profile?.creator_niche_id ?? creatorNiches[0]?.id ?? "",
  );

  const onNicheChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const id = parseInt(e.target.value, 10);
      if (!Number.isFinite(id)) return;
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (id === profile?.creator_niche_id) next.delete("creator_niche_id");
        else next.set("creator_niche_id", String(id));
        return next;
      }, { replace: true });
    },
    [profile?.creator_niche_id, setSearchParams],
  );

  return (
    <AppLayout active="channel" enableMobileSidebar>
      <TopBar
        kicker="KÊNH"
        title="Khám kênh"
        right={
          <>
            <DataFreshnessPill asOfIso={pulse?.as_of} />
          </>
        }
      />
      <main className="gv-route-main gv-route-main--1280">
        <div className="mb-[18px]">
          <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app")}>
            <ArrowLeft className="mr-1.5 h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            Về Studio
          </Btn>
        </div>

        {emptyParams ? (
          <div className="flex flex-col gap-6">
            <header className="flex min-w-0 flex-col gap-2">
              <span className="gv-uc flex items-center gap-1.5 text-[10px] font-semibold text-[color:var(--gv-accent-deep)]">
                <Search className="h-3 w-3 text-[color:var(--gv-accent)]" aria-hidden />
                KHÁM KÊNH
              </span>
              <h1 className="gv-tight m-0 text-[22px] font-semibold leading-[1.1] tracking-[-0.03em] text-[color:var(--gv-ink)] sm:text-[26px] lg:text-[28px]">
                Khám bất kỳ kênh TikTok nào
              </h1>
              <p className="max-w-prose text-[12.5px] leading-relaxed text-[color:var(--gv-ink-3)] sm:text-[13px]">
                Chọn ngách so sánh với kho video GetViews, dán @handle hoặc tìm kênh trực tiếp. Phân tích 60 video gần
                nhất — điểm mạnh, điểm yếu, nhịp đăng và gợi ý tuần này.
              </p>
            </header>

            {creatorNiches.length > 0 ? (
              <label className="flex max-w-md flex-col gap-1.5">
                <span className="gv-mono text-[10px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">
                  Ngách so sánh
                </span>
                <select
                  value={nicheSelectValue}
                  onChange={onNicheChange}
                  className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2.5 text-[16px] text-[color:var(--gv-ink)] outline-none focus:border-[color:var(--gv-ink)] sm:text-sm"
                >
                  {creatorNiches.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {!cloudConfigured ? (
              <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-[13px] text-[color:var(--gv-ink-3)]">
                Cần cấu hình Cloud Run API để phân tích kênh.
              </div>
            ) : (
              <>
                <div className="overflow-hidden rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
                  <div
                    className="border-b border-[color:var(--gv-rule)] px-6 py-6 sm:px-7 sm:py-7"
                    style={{
                      background:
                        "linear-gradient(135deg, color-mix(in srgb, var(--gv-accent) 4%, transparent) 0%, color-mix(in srgb, var(--gv-accent-2) 4%, transparent) 100%)",
                    }}
                  >
                    <label className="gv-mono mb-2 block text-[10px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">
                      Tìm kênh trên TikTok
                    </label>
                    <input
                      type="search"
                      value={userSearchDraft}
                      onChange={(e) => setUserSearchDraft(e.target.value)}
                      placeholder="Gõ tên hoặc @handle để gợi ý"
                      autoComplete="off"
                      className="mb-3 w-full rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2.5 text-[16px] text-[color:var(--gv-ink)] outline-none focus:border-[color:var(--gv-ink)] sm:text-sm"
                    />
                    {debouncedUserSearch.length >= 2 ? (
                      <ul
                        className="max-h-48 overflow-y-auto rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)]"
                        role="listbox"
                        aria-label="Kết quả tìm kênh"
                      >
                        {userSearchLoading ? (
                          <li className="px-3 py-2 text-sm text-[color:var(--gv-ink-3)]">Đang tìm…</li>
                        ) : userSearchIsError ? (
                          <li className="px-3 py-2 text-sm text-[color:var(--gv-neg-deep)]">
                            {analysisErrorCopy(userSearchError)}
                          </li>
                        ) : userSearchData?.users?.length ? (
                          userSearchData.users.map((u) => (
                            <li key={u.unique_id}>
                              <button
                                type="button"
                                className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm hover:bg-[color:var(--gv-canvas-2)]"
                                onClick={() => {
                                  setDraftHandle(`@${u.unique_id}`);
                                  setUserSearchDraft("");
                                  setDebouncedUserSearch("");
                                }}
                              >
                                {u.avatar_url ? (
                                  <img src={u.avatar_url} alt="" className="h-9 w-9 shrink-0 rounded-full object-cover" />
                                ) : (
                                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[color:var(--gv-rule)] text-xs text-[color:var(--gv-ink-3)]">
                                    @
                                  </span>
                                )}
                                <span className="min-w-0 flex-1">
                                  <span className="block truncate font-medium text-[color:var(--gv-ink)]">
                                    @{u.unique_id}
                                  </span>
                                  <span className="block truncate text-xs text-[color:var(--gv-ink-3)]">
                                    {u.nickname || "—"} · {u.follower_count.toLocaleString("vi-VN")} follow
                                  </span>
                                </span>
                              </button>
                            </li>
                          ))
                        ) : (
                          <li className="px-3 py-2 text-sm text-[color:var(--gv-ink-3)]">Không có kết quả.</li>
                        )}
                      </ul>
                    ) : null}
                  </div>

                  <div
                    className="flex items-stretch overflow-hidden rounded-[12px] border-[1.5px] border-[color:var(--gv-ink)] bg-[color:var(--gv-canvas)] m-6 mt-0"
                    style={{ boxShadow: "3px 3px 0 var(--gv-ink)" }}
                  >
                    <span
                      className="gv-mono flex shrink-0 items-center border-r border-[color:var(--gv-rule)] px-3.5 text-[13px] text-[color:var(--gv-ink-3)]"
                      aria-hidden
                    >
                      tiktok.com/
                    </span>
                    <form
                      className="flex min-w-0 flex-1"
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (!hasCredits) return;
                        openHandle(draftHandle);
                      }}
                    >
                      <input
                        type="text"
                        value={draftHandle}
                        onChange={(e) => {
                          setDraftHandle(e.target.value);
                          if (handleError) setHandleError(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            if (hasCredits && draftHandle.trim()) openHandle(draftHandle);
                          }
                        }}
                        placeholder="@handle  hoặc dán link đầy đủ"
                        aria-label="Handle hoặc URL kênh TikTok"
                        className="min-w-0 flex-1 border-0 bg-transparent px-4 py-3.5 text-[15px] font-medium text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)]"
                      />
                      <button
                        type="submit"
                        disabled={!draftHandle.trim() || !hasCredits}
                        className={
                          "flex shrink-0 items-center gap-1.5 border-l border-[color:var(--gv-rule)] px-5 text-[13px] font-semibold text-[color:var(--gv-canvas)] transition-colors " +
                          (draftHandle.trim() && hasCredits
                            ? "bg-[color:var(--gv-ink)] hover:bg-[color:var(--gv-ink-2)]"
                            : "cursor-not-allowed bg-[color:var(--gv-ink-2)] opacity-60")
                        }
                      >
                        Khám
                        <ArrowRight className="h-3 w-3" strokeWidth={2.4} aria-hidden />
                      </button>
                    </form>
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
                {handleError ? (
                  <span role="alert" className="text-sm text-[color:var(--gv-neg-deep)]">
                    {handleError}
                  </span>
                ) : null}
              </>
            )}
          </div>
        ) : !cloudConfigured ? (
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Phân tích kênh cần <span className="font-[family-name:var(--gv-font-mono)]">VITE_CLOUD_RUN_API_URL</span>{" "}
            trong môi trường build.
          </p>
        ) : (
          <>
            {creatorNiches.length > 0 ? (
              <div className="mb-6 flex max-w-md flex-col gap-1.5">
                <span className="gv-mono text-[10px] uppercase tracking-[0.12em] text-[color:var(--gv-ink-4)]">
                  Ngách so sánh
                </span>
                <select
                  value={nicheSelectValue}
                  onChange={onNicheChange}
                  className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2.5 text-[16px] text-[color:var(--gv-ink)] outline-none focus:border-[color:var(--gv-ink)] sm:text-sm"
                >
                  {creatorNiches.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
            {isPending || isFetching ? (
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
                <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">{analysisErrorCopy(error)}</p>
                <Btn className="mt-4" type="button" variant="ghost" onClick={() => void refetch()}>
                  Thử lại
                </Btn>
              </div>
            ) : data ? (
              <ChannelBody data={data} handleDisplay={handleKey ?? data.handle} onChangeHandle={openHandle} />
            ) : null}
          </>
        )}
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
  const navigate = useNavigate();
  const [another, setAnother] = useState("");
  const nicheKicker = data.niche_label?.trim()
    ? `HỒ SƠ KÊNH · ${data.niche_label.trim().toUpperCase()}`
    : "HỒ SƠ KÊNH";
  const at = handleDisplay.startsWith("@") ? handleDisplay : `@${handleDisplay}`;
  const kpis = useMemo(() => mapChannelKpis(data), [data]);
  const postingChip = useMemo(
    () => postingCadenceChipText(data.posting_cadence, data.posting_time),
    [data.posting_cadence, data.posting_time],
  );

  const scriptFromFormulaHref = useMemo(() => scriptPrefillFromChannel(data), [data]);

  const handleBridgeClick = useCallback(
    (tier: SuggestionsTier) => {
      goToStudioSuggestionsTier(tier, navigate);
    },
    [navigate],
  );
  const handleScrollToSuggestions = useCallback(() => {
    goToStudioSuggestionsTier("01", navigate);
  }, [navigate]);

  return (
    <div className="flex flex-col">
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

        {/* Hero — ref channel.jsx ch-hero (padding 28×32, radius 12, gap 32, mb 28 to formula) */}
        <div className="ch-hero grid grid-cols-1 gap-6 rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-6 sm:gap-8 sm:px-8 sm:py-7 min-[900px]:grid-cols-2">
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
                <h2 className="gv-tight m-0 truncate text-[26px] leading-tight sm:text-[38px] sm:leading-none text-[color:var(--gv-ink)]">
                  {data.name || data.handle}
                </h2>
                <p className="gv-mono mt-1 text-xs text-[color:var(--gv-ink-3)]">
                  {at} · {formatFollowers(data.followers)} follower
                </p>
              </div>
            </div>
            {data.bio ? (
              <p className="gv-tight m-0 max-w-[460px] text-lg italic leading-[1.4] text-[color:var(--gv-ink-2)]">
                {`"${data.bio}"`}
              </p>
            ) : (
              <p className="text-sm text-[color:var(--gv-ink-4)]">Chưa có thông tin bio.</p>
            )}
            <div className="mt-[18px] flex flex-wrap gap-2">
              {postingChip ? (
                <Chip size="md" variant="default">
                  Đăng {postingChip}
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
            <KpiGrid variant="channel" kpis={kpis} />
          </div>
        </div>

        {data.pulse ? <ChannelPulseBlock pulse={data.pulse} /> : null}

        {data.recent_7d ? (
          <section
            className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-5 sm:px-6"
            aria-labelledby="channel-recent7d-title"
          >
            <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-ink-4)]">
              ● 7 NGÀY QUA
            </p>
            <h3
              id="channel-recent7d-title"
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
            className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-5 sm:px-6"
            aria-labelledby="channel-strengths-title"
          >
            <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-pos-deep)]">
              ▲ ĐANG TỐT
            </p>
            <h3
              id="channel-strengths-title"
              className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
            >
              {data.strengths.length} thứ kênh đang làm tốt
            </h3>
            <ChannelDiagnosticList kind="strength" items={data.strengths} onBridgeClick={handleBridgeClick} />
          </section>
        ) : null}

        {data.weaknesses && data.weaknesses.length > 0 ? (
          <section
            className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-5 sm:px-6"
            aria-labelledby="channel-weaknesses-title"
          >
            <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-neg-deep)]">
              ✕ CẦN CẢI THIỆN
            </p>
            <h3
              id="channel-weaknesses-title"
              className="gv-tight m-0 text-[18px] font-semibold leading-snug tracking-[-0.02em] text-[color:var(--gv-ink)]"
            >
              {data.weaknesses.length} thứ nên sửa tuần này
            </h3>
            <ChannelDiagnosticList kind="weakness" items={data.weaknesses} onBridgeClick={handleBridgeClick} />
          </section>
        ) : null}

        {data.cadence ? (
          <section
            className="rounded-[12px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-5 sm:px-6"
            aria-labelledby="channel-cadence-title"
          >
            <p className="gv-uc gv-mono mb-1.5 text-[10px] font-bold tracking-[0.1em] text-[color:var(--gv-ink-4)]">
              ◷ NHỊP ĐĂNG
            </p>
            <h3
              id="channel-cadence-title"
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

        {/* PR — PostingHeatmap was previously tucked inside the hero
         * right column, which conflicted with the design pack's clean
         * 2-col hero (left: identity + chips, right: KPI grid only —
         * see ``screens/channel.jsx`` lines 14-61). Lifted out here so
         * the heatmap stays accessible but the hero matches design. */}
        {data.posting_heatmap && data.posting_heatmap.length > 0 ? (
          <section>
            <SectionMini kicker="LỊCH ĐĂNG · 7×8 HEATMAP" title="Khung giờ kênh hay đăng" />
            <PostingHeatmap grid={data.posting_heatmap} />
          </section>
        ) : null}

        <section>
          <SectionMini
            kicker="CÔNG THỨC PHÁT HIỆN"
            title={
              data.formula_gate === "thin_corpus" || !data.formula || data.formula.length === 0
                ? `Đang phân tích kênh "${data.name || data.handle}"…`
                : `"${data.name || data.handle} Formula" — ${data.formula.length} bước lặp đi lặp lại`
            }
          />
          <FormulaBar steps={data.formula} formulaGate={data.formula_gate} />
        </section>
      </div>

      {/* Two col — ref ch-grid; mt-9 = 36px after formula block (channel.jsx marginBottom 36) */}
      <div className="ch-grid mt-9 grid grid-cols-1 gap-8 min-[900px]:grid-cols-2">
        <div>
          <SectionMini kicker="VIDEO ĐỈNH" title="Top 4 video gây tiếng vang" />
          <div className="grid grid-cols-2 gap-3">
            {data.top_videos.slice(0, 4).map((v) => (
              <Link
                key={v.video_id}
                to="/app/answer"
                state={{
                  prefillUrl: `https://www.tiktok.com/@${(data.handle ?? "").replace(/^@/, "")}/video/${v.video_id}`,
                }}
                className="group block text-left"
              >
                <div
                  className="relative aspect-[9/16] overflow-hidden rounded-md bg-[color:var(--gv-canvas-2)]"
                  style={v.bg_color ? { backgroundColor: v.bg_color } : undefined}
                >
                  {v.thumbnail_url ? (
                    <img
                      src={v.thumbnail_url}
                      alt=""
                      className="absolute inset-0 h-full w-full object-cover"
                      loading="lazy"
                    />
                  ) : null}
                  <div className="absolute inset-x-2.5 bottom-2 text-white drop-shadow-md">
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
                    <p className="mb-0.5 text-[13px] font-medium leading-none text-[color:var(--gv-ink)]">
                      {lesson.title}
                    </p>
                    <p className="text-xs leading-normal text-[color:var(--gv-ink-3)]">{lesson.body}</p>
                  </div>
                </div>
              ))
            )}
          </div>
          <Btn
            className="mt-4 w-full justify-center"
            variant="accent"
            type="button"
            onClick={() => {
              logUsage("channel_to_script", { niche_id: data.niche_id, handle: data.handle });
              navigate(scriptFromFormulaHref);
            }}
          >
            <FileText className="mr-1.5 size-[13px] shrink-0" strokeWidth={1.7} aria-hidden />
            Tạo kịch bản theo công thức này
          </Btn>
        </div>
      </div>

      {data.computed_at ? (
        <p className="gv-mono text-center text-[10px] text-[color:var(--gv-ink-4)]">
          Phân tích kênh cập nhật: {new Date(data.computed_at).toLocaleString("vi-VN")}
          {import.meta.env.DEV && data.cache_hit === true ? " · cache" : null}
        </p>
      ) : null}
    </div>
  );
}
