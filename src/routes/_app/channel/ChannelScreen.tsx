import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { ArrowLeft, ArrowRight, FileText, Search, Shield } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { TopBar } from "@/components/v2/TopBar";
import { DataFreshnessPill } from "@/components/v2/DataFreshnessPill";
import { useHomePulse } from "@/hooks/useHomePulse";
import { useChannelDiagnose } from "@/hooks/useChannelDiagnose";
import { useChannelUserSearch } from "@/hooks/useChannelUserSearch";
import { useCreatorNiches } from "@/hooks/useCreatorNiches";
import { useProfile } from "@/hooks/useProfile";
import { extractChannelHandleFromMessage, normalizeChannelHandleInput, parseChannelExploreHandle } from "@/lib/channelHandle";
import { analysisErrorCopy } from "@/lib/errorMessages";
import { env } from "@/lib/env";
import { logUsage } from "@/lib/logUsage";
import { SectionRenderer } from "./components/SectionRenderer";
import { ScoreCard, ScoreCardSkeleton } from "./components/ScoreCard";
import { StepProgress, TRAJECTORY_LABELS } from "./components/StepProgress";
import { ProvenanceLine } from "./components/ProvenanceLine";

const CREDIT_COST = 3;

function channelInitial(name: string, handle: string): string {
  const s = (name?.trim() || handle).trim();
  if (!s) return "?";
  return s[0]?.toUpperCase() ?? "?";
}

export default function ChannelScreen() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: profile } = useProfile();
  const { data: creatorNiches = [] } = useCreatorNiches();
  const rawHandle = searchParams.get("handle");
  const handleKey = useMemo(() => normalizeChannelHandleInput(rawHandle), [rawHandle]);
  const creatorNicheParam = useMemo(() => {
    const r = searchParams.get("creator_niche_id");
    if (!r) return null;
    const n = parseInt(r, 10);
    return Number.isFinite(n) && n >= 1 ? n : null;
  }, [searchParams]);

  // Optional target video URL — from ?video_url query param or navigation state
  const prefillVideoUrl = useMemo(() => {
    const fromQuery = searchParams.get("video_url") ?? "";
    const fromState = (location.state as { prefillVideoUrlForChannel?: string } | null)
      ?.prefillVideoUrlForChannel ?? "";
    return fromQuery || fromState;
  }, [searchParams, location.state]);

  const [videoUrlInput, setVideoUrlInput] = useState(prefillVideoUrl);
  const [showVideoUrlInput, setShowVideoUrlInput] = useState(Boolean(prefillVideoUrl));

  // Sync external prefill into the input if it changes after mount
  useEffect(() => {
    if (prefillVideoUrl) {
      setVideoUrlInput(prefillVideoUrl);
      setShowVideoUrlInput(true);
    }
  }, [prefillVideoUrl]);

  // Diagnosis SSE hook
  const diagnose = useChannelDiagnose();
  const lastDiagnoseHandleRef = useRef<string | null>(null);

  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);
  const { data: pulse } = useHomePulse(cloudConfigured);

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
        fromUrl ?? (parsed ? normalizeChannelHandleInput(parsed) : null) ?? normalizeChannelHandleInput(trimmed);
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

  // Auto-start diagnosis when handle + nicheId are available, deduplicated by
  // (handle, niche). The previous dedupe key was handleKey alone, so switching
  // the "Ngách so sánh" dropdown after the first run silently left the report
  // stale: the URL param flipped, the niche pill re-rendered, but the effect
  // short-circuited and never re-fetched against the new niche.
  //
  // Also gate on hasCredits: a deep link ?handle=foo with an out-of-credits
  // user would otherwise fire start(), watch the BE reject with
  // insufficient_credits, and flash a "streaming" state at the user for one
  // frame. With the gate the upsell copy ("Cần N credit") renders straight away.
  const nicheId = creatorNicheParam ?? profile?.creator_niche_id ?? creatorNiches[0]?.id ?? 0;
  const diagnoseKey = handleKey ? `${handleKey}::${nicheId}` : "";
  useEffect(() => {
    if (!handleKey || !nicheId || !cloudConfigured || !hasCredits) return;
    if (lastDiagnoseHandleRef.current === diagnoseKey) return;
    lastDiagnoseHandleRef.current = diagnoseKey;
    void diagnose.start(handleKey, nicheId, videoUrlInput || undefined);
    // diagnose.start identity is stable (useCallback[qc])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [diagnoseKey, cloudConfigured, hasCredits]);

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
                Dán @handle hoặc tìm kênh để phân tích 60 video gần nhất — kết quả trả về kết luận tổng quan,
                video hiệu quả nhất, video kéo điểm, so sánh với kênh cùng ngách và 3–5 đề xuất hành động cụ thể.
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
                          : "bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg-deep)]")
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
            <ChannelDiagnosisBody
              handle={handleKey ?? ""}
              nicheId={nicheId}
              videoUrlInput={videoUrlInput}
              setVideoUrlInput={setVideoUrlInput}
              showVideoUrlInput={showVideoUrlInput}
              setShowVideoUrlInput={setShowVideoUrlInput}
              diagnose={diagnose}
              onRestart={() => {
                lastDiagnoseHandleRef.current = null;
                void diagnose.start(handleKey ?? "", nicheId, videoUrlInput || undefined);
                lastDiagnoseHandleRef.current = diagnoseKey;
              }}
              onChangeHandle={openHandle}
            />
          </>
        )}
      </main>
    </AppLayout>
  );
}


// ---------------------------------------------------------------------------
// ChannelDiagnosisBody — Lightreel-style narrative view (Layer 4c)
// ---------------------------------------------------------------------------

type DiagnoseHook = ReturnType<typeof useChannelDiagnose>;

function ChannelDiagnosisBody({
  handle,
  nicheId,
  videoUrlInput,
  setVideoUrlInput,
  showVideoUrlInput,
  setShowVideoUrlInput,
  diagnose,
  onRestart,
  onChangeHandle,
}: {
  handle: string;
  nicheId: number;
  videoUrlInput: string;
  setVideoUrlInput: (v: string) => void;
  showVideoUrlInput: boolean;
  setShowVideoUrlInput: (v: boolean) => void;
  diagnose: DiagnoseHook;
  onRestart: () => void;
  onChangeHandle: (h: string) => void;
}) {
  const navigate = useNavigate();
  const [another, setAnother] = useState("");

  const at = handle.startsWith("@") ? handle : `@${handle}`;

  const errorMessages: Record<string, string> = {
    insufficient_credits: "Không đủ credit để phân tích kênh này.",
    channel_not_found: "Không tìm thấy kênh — hãy kiểm tra lại @handle.",
    stream_failed: "Phân tích thất bại — vui lòng thử lại.",
    no_cloud_run: "Chưa cấu hình Cloud Run API.",
    no_session: "Phiên đăng nhập hết hạn — vui lòng đăng nhập lại.",
    already_in_flight: "Đang có phân tích cùng kênh đang chạy — vui lòng chờ.",
    stream_timeout: "Phân tích quá thời gian — vui lòng thử lại.",
  };

  const errorMessage = diagnose.error
    ? (errorMessages[diagnose.error] ?? `Lỗi: ${diagnose.error}`)
    : null;

  // Build "Tạo kịch bản" URL from the final payload when available
  const scriptHref = useMemo(() => {
    const fp = diagnose.finalPayload;
    if (!fp) return null;
    const fmt = fp.channel_persona?.dominant_format ?? fp.dominant_format ?? "";
    if (!fmt || !handle) return null;
    const params = new URLSearchParams({
      prefill_handle: handle,
      prefill_format: fmt,
    });
    return `/app/script?${params.toString()}`;
  }, [diagnose.finalPayload, handle]);

  const isDone = diagnose.status === "done";
  const isStreaming = diagnose.status === "streaming";
  const isError = diagnose.status === "error";

  return (
    <div className="flex flex-col gap-6">
      {/* Change handle form */}
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

      {/* Optional video URL input (collapsible) */}
      <div>
        <button
          type="button"
          className="text-xs text-[color:var(--gv-accent)] underline-offset-2 hover:underline"
          onClick={() => setShowVideoUrlInput(!showVideoUrlInput)}
        >
          {showVideoUrlInput ? "Ẩn video so sánh" : "+ So sánh với video cụ thể"}
        </button>
        {showVideoUrlInput && (
          <div className="mt-2 flex gap-2">
            <input
              type="url"
              value={videoUrlInput}
              onChange={(e) => setVideoUrlInput(e.target.value)}
              placeholder="https://tiktok.com/@handle/video/..."
              className="min-w-0 flex-1 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-sm text-[color:var(--gv-ink)] outline-none focus:border-[color:var(--gv-ink)]"
              autoComplete="off"
            />
            <Btn
              type="button"
              variant="ghost"
              size="sm"
              onClick={onRestart}
              disabled={isStreaming}
            >
              Phân tích lại
            </Btn>
          </div>
        )}
      </div>

      {/* Channel header */}
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[color:var(--gv-canvas-2)] text-xl font-semibold text-[color:var(--gv-ink)]">
          {channelInitial("", handle)}
        </div>
        <div>
          <h1 className="gv-tight m-0 text-[20px] font-semibold leading-tight">{at}</h1>
          {diagnose.trajectoryShape && (
            <p className="text-xs text-[color:var(--gv-ink-3)] mt-0.5">
              {TRAJECTORY_LABELS[diagnose.trajectoryShape] ?? diagnose.trajectoryShape.replace(/_/g, " ")}
            </p>
          )}
        </div>
      </div>

      {/* Streaming progress */}
      {isStreaming && diagnose.sections.length === 0 && (
        <div className="rounded-[14px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
          <StepProgress
            activeStepIndex={diagnose.activeStepIndex}
            activeStepLabel={diagnose.activeStepLabel}
            heartbeatCount={diagnose.heartbeatCount}
            trajectoryShape={diagnose.trajectoryShape}
          />
        </div>
      )}

      {/* Narrative sections */}
      {diagnose.sections.length > 0 && (
        <div className="rounded-[14px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 sm:px-7">
          {isStreaming && !diagnose.scoreCard ? <ScoreCardSkeleton /> : null}
          {diagnose.scoreCard ? <ScoreCard card={diagnose.scoreCard} /> : null}
          {diagnose.sections.map((section) => (
            <SectionRenderer
              key={section.section_id}
              section={section}
              recommendations={
                section.section_id === "recommendations" ? diagnose.recommendations : []
              }
              // Cursor scopes to the currently-active section only.
              // section_done clears activeSectionId so completed sections
              // stop showing the blinking caret.
              streaming={isStreaming && diagnose.activeSectionId === section.section_id}
            />
          ))}

          {/* Provenance + cache */}
          {isDone && diagnose.finalPayload && (
            <ProvenanceLine
              provenance={diagnose.finalPayload.provenance}
              cacheHit={diagnose.finalPayload.cache_hit}
            />
          )}

          {/* Niche thin disclaimer */}
          {isDone && (diagnose.peerSource === "thin" || diagnose.finalPayload?.niche_thin) && (
            <p className="mt-2 text-xs text-[color:var(--gv-ink-3)] italic">
              Kho dữ liệu ngách này chưa đủ để benchmark chính xác — kết quả mang tính tham khảo.
            </p>
          )}
        </div>
      )}

      {/* Error state */}
      {isError && errorMessage && (
        <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
          <p className="text-sm text-[color:var(--gv-neg-deep)]">{errorMessage}</p>
          <Btn className="mt-3" type="button" variant="ghost" size="sm" onClick={onRestart}>
            Thử lại
          </Btn>
        </div>
      )}

      {/* Tạo kịch bản CTA */}
      {isDone && scriptHref && (
        <div className="flex justify-end pb-2">
          <Btn
            type="button"
            onClick={() => {
              logUsage("channel_diagnose_to_script", { handle });
              navigate(scriptHref);
            }}
          >
            <FileText className="mr-1.5 size-[13px] shrink-0" strokeWidth={1.7} aria-hidden />
            Tạo kịch bản theo phân tích này
          </Btn>
        </div>
      )}
    </div>
  );
}
