import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router";
import { ArrowRight, Shield } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import { useChannelDiagnose } from "@/hooks/useChannelDiagnose";
import { useChannelQuickPeek } from "@/hooks/useChannelQuickPeek";
import { useCreatorNiches } from "@/hooks/useCreatorNiches";
import { useProfile } from "@/hooks/useProfile";
import {
  extractChannelHandleFromMessage,
  normalizeChannelHandleInput,
  parseChannelExploreHandle,
} from "@/lib/channelHandle";
import {
  CHANNEL_SAU_CREDIT_COST,
  channelDepthCreditCost,
  parseChannelDepth,
  type ChannelDepth,
} from "@/lib/channelDepth";
import { env } from "@/lib/env";
import { pushChannelHistory } from "@/lib/channelHistory";
import { useAuth } from "@/lib/auth";
import { ChannelBenchmarkStrip } from "./ChannelBenchmarkStrip";
import { ChannelDepthPicker } from "./ChannelDepthPicker";
import { ChannelDiagnosisBody } from "./ChannelDiagnosisBody";
import { ChannelNhanhPanel } from "./ChannelNhanhPanel";

const CREDIT_COST = CHANNEL_SAU_CREDIT_COST;

/**
 * F4/F5 channel analysis — embedded in Studio Home (§6).
 * URL state lives on `/app?handle=&depth=` (see ``channelStudioHandoff``).
 */
export function ChannelStudioPanel({
  defaultHandle,
  onBridgeEligible,
}: {
  /** Profile ``tiktok_handle`` when no ``?handle=`` query param. */
  defaultHandle?: string | null;
  /** Fired when Nhanh findings or Sâu diagnosis qualify for Gợi ý bridge. */
  onBridgeEligible?: () => void;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const { user } = useAuth();
  const { data: profile } = useProfile();
  const { data: creatorNiches = [] } = useCreatorNiches();

  const rawHandle = searchParams.get("handle") ?? defaultHandle ?? "";
  const channelDepth = parseChannelDepth(searchParams.get("depth"));
  const handleKey = useMemo(() => normalizeChannelHandleInput(rawHandle), [rawHandle]);

  const creatorNicheParam = useMemo(() => {
    const r = searchParams.get("creator_niche_id");
    if (!r) return null;
    const n = parseInt(r, 10);
    return Number.isFinite(n) && n >= 1 ? n : null;
  }, [searchParams]);

  const prefillVideoUrl = useMemo(() => {
    const fromQuery = searchParams.get("video_url") ?? "";
    const fromState = (location.state as { prefillVideoUrlForChannel?: string } | null)
      ?.prefillVideoUrlForChannel ?? "";
    return fromQuery || fromState;
  }, [searchParams, location.state]);

  const [videoUrlInput, setVideoUrlInput] = useState(prefillVideoUrl);
  const [showVideoUrlInput, setShowVideoUrlInput] = useState(Boolean(prefillVideoUrl));

  useEffect(() => {
    if (prefillVideoUrl) {
      setVideoUrlInput(prefillVideoUrl);
      setShowVideoUrlInput(true);
    }
  }, [prefillVideoUrl]);

  const diagnose = useChannelDiagnose();
  const lastDiagnoseHandleRef = useRef<string | null>(null);
  const syncedDefaultHandleRef = useRef(false);
  const forceRefreshPending = searchParams.get("force_refresh") === "1";

  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);
  const quickPeekQuery = useChannelQuickPeek(handleKey, Boolean(handleKey && cloudConfigured));
  const quickPeek = quickPeekQuery.data;

  const [draftHandle, setDraftHandle] = useState("");
  const [handleError, setHandleError] = useState<string | null>(null);

  const credits = (profile as { credits_remaining?: number } | null | undefined)?.credits_remaining ?? 0;
  const creditCost = channelDepthCreditCost(channelDepth);
  const hasCredits = channelDepth === "nhanh" || credits >= CREDIT_COST;

  const setChannelDepth = useCallback(
    (depth: ChannelDepth) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (depth === "nhanh") next.delete("depth");
          else next.set("depth", depth);
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

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
      syncedDefaultHandleRef.current = false;
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set("handle", k);
          next.delete("force_refresh");
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const nicheId = creatorNicheParam ?? profile?.creator_niche_id ?? creatorNiches[0]?.id ?? 0;
  const diagnoseKey = handleKey ? `${handleKey}::${nicheId}` : "";

  // Share/bookmark: promote profile handle into ?handle= once.
  useEffect(() => {
    if (searchParams.get("handle")) return;
    const clean = defaultHandle?.replace(/^@/, "").trim();
    if (!clean || syncedDefaultHandleRef.current) return;
    syncedDefaultHandleRef.current = true;
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("handle", clean);
        return next;
      },
      { replace: true },
    );
  }, [defaultHandle, searchParams, setSearchParams]);

  useEffect(() => {
    if (channelDepth !== "sau") return;
    if (!handleKey || !nicheId || !cloudConfigured || !hasCredits) return;
    if (lastDiagnoseHandleRef.current === diagnoseKey && !forceRefreshPending) return;
    lastDiagnoseHandleRef.current = diagnoseKey;
    if (user?.id) pushChannelHistory(user.id, handleKey);
    void diagnose.start(handleKey, nicheId, videoUrlInput || undefined);
    if (forceRefreshPending) {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete("force_refresh");
          return next;
        },
        { replace: true },
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [diagnoseKey, cloudConfigured, hasCredits, channelDepth, forceRefreshPending]);

  useEffect(() => {
    if (diagnose.status === "done") {
      onBridgeEligible?.();
    }
  }, [diagnose.status, onBridgeEligible]);

  useEffect(() => {
    if (!quickPeek || quickPeek.corpus_video_count < 3) return;
    if (quickPeek.findings.length > 0 || quickPeek.teaser) {
      onBridgeEligible?.();
    }
  }, [quickPeek, onBridgeEligible]);

  const emptyParams = !handleKey;

  if (!cloudConfigured) {
    return (
      <div className="rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 text-sm text-[color:var(--gv-ink-3)]">
        Cần cấu hình Cloud Run API để phân tích kênh.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <ChannelDepthPicker
        depth={channelDepth}
        onDepthChange={(depth) => {
          lastDiagnoseHandleRef.current = null;
          setChannelDepth(depth);
        }}
        creditsRemaining={credits}
        sauCreditCost={CREDIT_COST}
      />

      {emptyParams ? (
        <>
          <div
            className="flex items-stretch overflow-hidden rounded-xl border-[1.5px] border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)]"
            style={{ boxShadow: "3px 3px 0 var(--gv-ink)" }}
          >
            <span
              className="gv-mono flex shrink-0 items-center border-r border-[color:var(--gv-rule)] px-3.5 text-sm text-[color:var(--gv-ink-3)]"
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
                placeholder="@handle  hoặc dán link profile"
                aria-label="Handle hoặc URL kênh TikTok"
                className="min-w-0 flex-1 border-0 bg-transparent px-4 py-3.5 text-base font-medium text-[color:var(--gv-ink)] outline-none placeholder:text-[color:var(--gv-ink-4)] focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[color:var(--gv-accent)]"
              />
              <button
                type="submit"
                disabled={!draftHandle.trim() || !hasCredits}
                className={
                  "flex shrink-0 items-center gap-1.5 border-l border-[color:var(--gv-rule)] px-5 text-sm font-semibold text-[color:var(--gv-canvas)] transition-colors " +
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

          <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-[color:var(--gv-ink-4)]">
            <div className="flex items-center gap-1.5">
              <Shield className="h-3 w-3 shrink-0" strokeWidth={1.6} aria-hidden />
              <span>Chỉ đọc dữ liệu công khai. Không cần đăng nhập TikTok.</span>
            </div>
            <span
              className={
                "gv-mono rounded-full px-2.5 py-0.5 text-[11px] font-semibold " +
                (hasCredits
                  ? "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]"
                  : "bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg-deep)]")
              }
            >
              {hasCredits
                ? `${creditCost} credit / lần`
                : channelDepth === "sau"
                  ? `Cần ${CREDIT_COST} credit · còn ${credits}`
                  : "0 credit / lần"}
            </span>
          </div>

          {!defaultHandle?.trim() ? (
            <p className="m-0 text-xs leading-relaxed text-[color:var(--gv-ink-3)]">
              Gắn handle TikTok của bạn trong{" "}
              <Link to="/app/settings" className="font-medium text-[color:var(--gv-accent)] underline-offset-2 hover:underline">
                Cài đặt
              </Link>{" "}
              để tự điền kênh mỗi lần vào Studio.
            </p>
          ) : null}

          {handleError ? (
            <span role="alert" className="text-sm text-[color:var(--gv-neg-deep)]">
              {handleError}
            </span>
          ) : null}
        </>
      ) : (
        <>
          {channelDepth === "sau" && !hasCredits ? (
            <p className="m-0 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-neg-soft)] px-4 py-3 text-sm text-[color:var(--gv-neg-deep)]">
              Cần {CREDIT_COST} credit để chạy Sâu — bạn còn {credits}. Chuyển sang Nhanh hoặc nạp thêm
              credit.
            </p>
          ) : null}
          {quickPeek && quickPeek.corpus_video_count >= 3 ? (
            <ChannelBenchmarkStrip data={quickPeek} />
          ) : null}
          {channelDepth === "nhanh" ? (
            <ChannelNhanhPanel
              handle={handleKey ?? ""}
              onUpgradeToSau={() => setChannelDepth("sau")}
              peekData={quickPeek ?? null}
              peekLoading={quickPeekQuery.isLoading}
              peekError={quickPeekQuery.isError}
            />
          ) : (
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
          )}
        </>
      )}
    </div>
  );
}
