import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";
import { Plus } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { QueryComposer } from "@/components/v2/QueryComposer";
import { TopBar } from "@/components/v2/TopBar";
import { useHomePulse } from "@/hooks/useHomePulse";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useNicheRowsForIds } from "@/hooks/useTopNiches";
import { useQuery } from "@tanstack/react-query";
import { useTopPatterns, type TopPatternsScope } from "@/hooks/useTopPatterns";
import { fetchContentClassIdsForCreatorNiche } from "@/lib/corpusNicheFilter";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { logUsage } from "@/lib/logUsage";
import type { AnswerHandoffDepth } from "@/lib/answerHandoff";
import { CHANNEL_SAU_CREDIT_COST } from "@/lib/channelDepth";
import { profileFirstNicheId, profileCreatorNicheId } from "@/lib/profileNiches";
import { readStudioNicheId, writeStudioNicheId } from "@/lib/studioNicheSession";
import {
  planStudioComposerSubmit,
  studioComposerPlaceholder,
  type StudioComposerPill,
} from "@/lib/studioComposer";
import { queryUrlChipState } from "@/lib/tiktokUrl";
import { TickerMarquee } from "./components/TickerMarquee";
import { FirstRunWelcomeStrip } from "./components/FirstRunWelcomeStrip";
import { HomeSuggestionsToday } from "./components/HomeSuggestionsToday";
import { NichePicker } from "./components/NichePicker";
import { DateChip } from "./components/DateChip";
import { useIsFirstRun } from "./components/useIsFirstRun";
import {
  unfilledPasteTemplateHint,
} from "./pasteTemplates";
import { scrollToSuggestionsTier, type SuggestionsTier } from "./components/scrollToTier";
import { useHomeGreetingFit } from "./useHomeGreetingFit";

/**
 * Getviews Studio — Home screen (Phase A · A3.4).
 *
 * Order: ticker → greeting → composer (4 pills + depth) → GỢI Ý HÔM NAY.
 */

export default function HomeScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  // Deep-link from channel diagnostics → scroll to Gợi ý hôm nay tier.
  useEffect(() => {
    const raw = searchParams.get("scrollTier");
    if (raw !== "01" && raw !== "02" && raw !== "03") return;
    const tier = raw as SuggestionsTier;
    const id = window.requestAnimationFrame(() => {
      scrollToSuggestionsTier(tier);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete("scrollTier");
          return next;
        },
        { replace: true },
      );
    });
    return () => window.cancelAnimationFrame(id);
  }, [searchParams, setSearchParams]);

  const composerRef = useRef<HTMLTextAreaElement>(null);
  const [composerText, setComposerText] = useState("");
  const [analysisDepth, setAnalysisDepth] = useState<AnswerHandoffDepth>("basic");
  const [studioPill, setStudioPill] = useState<StudioComposerPill>("video_flop");
  // L1.5 audit follow-up — surfaces a Vietnamese hint when the user
  // submits an unfilled paste-template chip (legacy template text in composer).
  const [placeholderHint, setPlaceholderHint] = useState<string | null>(null);
  const { data: profile, isPending: profilePending } = useProfile();
  const { data: niches = [] } = useNicheTaxonomy();

  // Single niche per user — Home anchors to ``profileFirstNicheId(profile)`` (creator_niche_id → legacy niche_taxonomy row).
  // Trends pills browse other niches; this surface stays on the user's pick.
  const followedNicheIds = useMemo(() => {
    const id = profileFirstNicheId(profile);
    return id != null ? [id] : [];
  }, [profile]);
  const { data: followedNiches = [] } = useNicheRowsForIds(followedNicheIds);
  const defaultNicheId = followedNicheIds[0] ?? null;
  const [selectedNicheId, setSelectedNicheId] = useState<number | null>(defaultNicheId);

  // Resync when the profile follow list or default slot changes
  // (e.g. user just edited their niches in /app/settings).
  useEffect(() => {
    if (selectedNicheId == null) {
      setSelectedNicheId(defaultNicheId);
      return;
    }
    if (
      followedNicheIds.length > 0 &&
      !followedNicheIds.includes(selectedNicheId)
    ) {
      setSelectedNicheId(defaultNicheId);
    }
  }, [defaultNicheId, followedNicheIds, selectedNicheId]);

  // Prefer last ``gv:studio_niche_id`` before other effects (so the write below doesn't overwrite
  // it on first paint) — keeps Home ↔ Xu hướng aligned when re-entering /app/home.
  useLayoutEffect(() => {
    if (location.pathname !== "/app/home") return;
    if (followedNicheIds.length === 0) return;
    const s = readStudioNicheId();
    if (s == null || !followedNicheIds.includes(s)) return;
    setSelectedNicheId(s);
  }, [location.key, location.pathname, followedNicheIds]);

  // Keep Xu hướng (`/app/trends`) in sync: same session key as ExploreScreen + URL `?niche=`.
  useEffect(() => {
    if (selectedNicheId != null) writeStudioNicheId(selectedNicheId);
  }, [selectedNicheId]);

  const { data: pulse } = useHomePulse(true, selectedNicheId);

  // D7 — LIVE badge surfaces a relative timestamp ("• LIVE • CẬP NHẬT
  // 2 PHÚT TRƯỚC") per design pack ``screens/home.jsx`` line 98.
  // Falls back to "• LIVE • STUDIO" when ``pulse.as_of`` isn't loaded
  // yet so the chip renders something during the first paint.
  const liveBadgeLabel = useMemo(() => {
    if (!pulse?.as_of) return "• LIVE • STUDIO";
    const rel = formatRelativeSinceVi(new Date(), new Date(pulse.as_of));
    if (rel === "—") return "• LIVE • STUDIO";
    return `• LIVE • CẬP NHẬT ${rel.toUpperCase()}`;
  }, [pulse?.as_of]);

  const nicheLabel = useMemo(() => {
    const id = selectedNicheId;
    if (!id) return "ngách của bạn";
    return niches.find((n) => n.id === id)?.name ?? "ngách của bạn";
  }, [selectedNicheId, niches]);

  const creatorNicheId = profileCreatorNicheId(profile);

  const { data: homeContentClassIds = [] } = useQuery({
    queryKey: ["creator_niche_content_classes", creatorNicheId],
    queryFn: () => fetchContentClassIdsForCreatorNiche(creatorNicheId!),
    enabled: creatorNicheId != null,
    staleTime: 10 * 60_000,
  });

  const patternScope = useMemo<TopPatternsScope | null>(() => {
    if (selectedNicheId == null && homeContentClassIds.length === 0) return null;
    return {
      contentClassIds: homeContentClassIds,
      legacyNicheId: selectedNicheId,
      creatorNicheId,
    };
  }, [homeContentClassIds, selectedNicheId, creatorNicheId]);

  // PR-cleanup-E — greeting + composer signals.
  // ``newHookCount``: count of hot patterns whose previous-week instance
  // count was 0 (true "mới" rather than "đang lên"). Same query
  // HooksTable already fires (limit=6, dedupes via React Query cache).
  const { data: topPatterns = [] } = useTopPatterns(patternScope);
  const newHookCount = useMemo(
    () => topPatterns.filter((p) => p.weekly_instance_count_prev === 0).length,
    [topPatterns],
  );

  // Capitalised because ``firstName`` now leads the H1 (was preceded by
  // "Chào "); lowercase looks wrong at the start of a sentence.
  const displayName = profile?.display_name?.trim() || "Bạn";
  const firstName = displayName.split(/\s+/).pop() ?? displayName;
  const { containerRef: greetingRef, line1Ref, line2Ref } = useHomeGreetingFit([
    firstName,
    nicheLabel,
    newHookCount,
  ]);
  const creditsRemaining =
    (profile as { credits_remaining?: number } | null | undefined)?.credits_remaining ?? 0;

  useEffect(() => {
    if (profilePending) return;
    if (
      studioPill === "channel" &&
      analysisDepth === "deep" &&
      creditsRemaining < CHANNEL_SAU_CREDIT_COST
    ) {
      setAnalysisDepth("basic");
    }
  }, [studioPill, analysisDepth, creditsRemaining, profilePending]);

  const launchChat = (text: string) => {
    logUsage("studio_composer_submit", {
      surface: "home",
      length: text.length,
      analysis_depth: analysisDepth,
      studio_pill: studioPill,
    });
    const plan = planStudioComposerSubmit(studioPill, text, analysisDepth);
    if (plan.kind === "blocked") {
      if (plan.reason === "non_tiktok_url" && plan.message) {
        setPlaceholderHint(plan.message);
        logUsage("studio_composer_blocked", { reason: "non_tiktok_url" });
        composerRef.current?.focus();
      }
      return;
    }
    navigate(plan.to);
  };

  const handleComposerChange = (v: string) => {
    setComposerText(v);
    if (placeholderHint) setPlaceholderHint(null);
  };

  const submitStudioComposer = () => {
    const text = composerText.trim();
    if (!text) return;
    const hint = unfilledPasteTemplateHint(text);
    if (hint) {
      setPlaceholderHint(hint);
      logUsage("studio_composer_blocked", { reason: "unfilled_paste_template" });
      composerRef.current?.focus();
      return;
    }
    setPlaceholderHint(null);
    setComposerText("");
    launchChat(text);
  };

  // PR-6 — Day-1 welcome strip. ``useIsFirstRun`` reads
  // ``profile.created_at`` (within 24h) + a per-user localStorage flag.
  const { isFirstRun, dismiss: dismissFirstRun } = useIsFirstRun(profile);

  const composerUrlChip = queryUrlChipState(composerText);

  return (
    <AppLayout active="home" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="STUDIO"
          title="Sảnh Sáng Tạo"
          right={
            <Btn
              variant="ink"
              size="sm"
              className="shrink-0 whitespace-nowrap"
              onClick={() => navigate({ pathname: "/app/answer", search: "" }, { replace: true })}
            >
              <Plus className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
              Phân tích mới
            </Btn>
          }
        />
        {isFirstRun ? (
          <FirstRunWelcomeStrip
            firstName={firstName}
            nicheLabel={nicheLabel}
            onEditNiches={() => navigate("/app/settings")}
            onDismiss={dismissFirstRun}
          />
        ) : null}
        <TickerMarquee viewNicheId={selectedNicheId} />

        <main className="gv-home-wrap mx-auto w-full max-w-[1320px]">
          <div className="gv-fade-up">
            <div className="mb-3.5 flex flex-wrap items-end justify-between gap-4">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="inline-flex items-center rounded-full bg-[color:var(--gv-lime)] px-3 py-1 gv-kicker font-semibold text-[color:var(--gv-ink)]">
                  {liveBadgeLabel}
                </span>
                <DateChip />
              </div>
              {followedNiches.length > 0 ? (
                <NichePicker
                  niches={followedNiches}
                  selectedNicheId={selectedNicheId}
                  onSelectNiche={(id) => {
                    setSelectedNicheId(id);
                    logUsage("home_niche_pick", { niche_id: id });
                  }}
                  onEditNiches={() => navigate("/app/settings")}
                />
              ) : null}
            </div>

            <h1
              ref={greetingRef}
              className="gv-home-greeting gv-tight mt-0 w-full max-w-[880px] leading-[1.08] text-[color:var(--gv-ink)]"
            >
              <span ref={line1Ref} className="gv-home-greeting__line">
                Chào {firstName}. Hôm nay{" "}
                <span
                  className="inline-block rotate-[-1deg] rounded-[10px] px-2.5 text-white"
                  style={{ background: "var(--gv-accent)" }}
                >
                  {nicheLabel}
                </span>
              </span>
              <span ref={line2Ref} className="gv-home-greeting__line">
                {newHookCount > 0 ? (
                  <>
                    có{" "}
                    <span style={{ color: "var(--gv-accent-2-deep, var(--gv-accent-2))" }}>
                      {newHookCount} hook
                    </span>{" "}
                    mới đang lên xu hướng.
                  </>
                ) : (
                  "đang có gì mới."
                )}
              </span>
            </h1>
          </div>

          <div className="gv-fade-up gv-fade-up-delay-1 mt-7 w-full">
            <QueryComposer
              ref={composerRef}
              value={composerText}
              onChange={handleComposerChange}
              onSubmit={submitStudioComposer}
              placeholder={studioComposerPlaceholder(studioPill, nicheLabel)}
              showNicheCaption={false}
              showUrlChip={composerUrlChip.kind === "tiktok"}
              urlInvalidMessage={
                composerUrlChip.kind === "invalid" ? composerUrlChip.message : undefined
              }
              analysisDepth={analysisDepth}
              onAnalysisDepthChange={setAnalysisDepth}
              studioPill={studioPill}
              onStudioPillChange={setStudioPill}
              creditsRemaining={profilePending ? undefined : creditsRemaining}
              channelDeepCreditCost={CHANNEL_SAU_CREDIT_COST}
            />
            {placeholderHint ? (
              <p
                className="mt-2 text-[12px] leading-snug text-[color:var(--gv-warn)]"
                role="alert"
              >
                {placeholderHint}
              </p>
            ) : null}
          </div>

          <div className="gv-fade-up gv-fade-up-delay-2 mt-7 mb-12">
            <HomeSuggestionsToday
                patternScope={patternScope}
                creatorNicheId={profile?.creator_niche_id ?? null}
              />
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
