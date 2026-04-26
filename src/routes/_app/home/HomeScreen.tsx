import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Plus, Sparkles } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { QueryComposer } from "@/components/v2/QueryComposer";
import { TopBar } from "@/components/v2/TopBar";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useNicheRowsForIds } from "@/hooks/useTopNiches";
import { logUsage } from "@/lib/logUsage";
import { normalizeNicheIds } from "@/lib/profileNiches";
import { TickerMarquee } from "./components/TickerMarquee";
import { FirstRunWelcomeStrip } from "./components/FirstRunWelcomeStrip";
import { HomeMyChannelSection } from "./components/HomeMyChannelSection";
import { HomeSuggestionsToday } from "./components/HomeSuggestionsToday";
import { NichePicker } from "./components/NichePicker";
import { QuickActions } from "./components/QuickActions";
import { DateChip } from "./components/DateChip";
import { useIsFirstRun } from "./components/useIsFirstRun";

/**
 * Getviews Studio — Home screen (Phase A · A3.4).
 *
 * Order: ticker → greeting → composer → suggested chips + shortcut pills → <hr>
 * → KÊNH CỦA BẠN → GỢI Ý HÔM NAY (tier 01 gồm kịch bản + 5 video; tier 02–03).
 */

/** TikTok / short-video URL — drives the "URL detected" chip in QueryComposer (C.1.0). */
const URL_IN_TEXT =
  /(?:https?:\/\/)?(?:www\.)?(?:vm\.|vt\.)?(?:tiktok\.com|youtube\.com|youtu\.be)\b/i;

export default function HomeScreen() {
  const navigate = useNavigate();
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const [composerText, setComposerText] = useState("");
  const { data: profile } = useProfile();
  const { data: niches = [] } = useNicheTaxonomy();

  // PR-5 — niche picker: viewing-niche state on Home defaults to the
  // user's primary_niche but can be switched among the niches they
  // follow (``profile.niche_ids``). Only the suggestions stack reads
  // ``selectedNicheId``; HomeMyChannelSection stays pinned to
  // primary_niche because /channel/analyze runs server-side off it.
  const followedNicheIds = useMemo(
    () => normalizeNicheIds(profile?.niche_ids ?? []),
    [profile?.niche_ids],
  );
  const { data: followedNiches = [] } = useNicheRowsForIds(followedNicheIds);
  const defaultNicheId = profile?.primary_niche ?? followedNicheIds[0] ?? null;
  const [selectedNicheId, setSelectedNicheId] = useState<number | null>(defaultNicheId);

  // Resync when the profile's primary niche or follow list changes
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

  const nicheLabel = useMemo(() => {
    const id = selectedNicheId;
    if (!id) return "ngách của bạn";
    return niches.find((n) => n.id === id)?.name ?? "ngách của bạn";
  }, [selectedNicheId, niches]);

  // Capitalised because ``firstName`` now leads the H1 (was preceded by
  // "Chào "); lowercase looks wrong at the start of a sentence.
  const displayName = profile?.display_name?.trim() || "Bạn";
  const firstName = displayName.split(/\s+/).pop() ?? displayName;

  const suggestedPrompts = useMemo(
    () => [
      `Xu hướng đang hot trong ${nicheLabel} tuần này?`,
      `Hook nào đang hiệu quả nhất trong ${nicheLabel}?`,
      "Phân tích kênh @creator — họ đang làm gì hay?",
      `Format nào đang tăng view nhanh nhất ngách ${nicheLabel}?`,
    ],
    [nicheLabel],
  );

  const launchChat = (text: string) => {
    logUsage("studio_composer_submit", { surface: "home", length: text.length });
    navigate(`/app/answer?q=${encodeURIComponent(text)}`);
  };

  const fillComposer = (text: string) => {
    setComposerText(text);
    queueMicrotask(() => composerRef.current?.focus());
  };

  const submitStudioComposer = () => {
    const text = composerText.trim();
    if (!text) return;
    setComposerText("");
    launchChat(text);
  };

  // PR-6 — Day-1 welcome strip. ``useIsFirstRun`` reads
  // ``profile.created_at`` (within 24h) + a per-user localStorage flag.
  const { isFirstRun, dismiss: dismissFirstRun } = useIsFirstRun(profile);

  return (
    <AppLayout active="home" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="STUDIO"
          title="Sảnh Sáng Tạo"
          right={
            <>
              <Btn variant="ink" size="sm" onClick={() => navigate("/app/answer")}>
                <Plus className="h-3.5 w-3.5" strokeWidth={2} />
                Phân tích mới
              </Btn>
            </>
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
        <TickerMarquee />

        <main className="gv-home-wrap mx-auto w-full max-w-[1320px]">
          <div className="gv-fade-up">
            <div className="mb-3.5 flex flex-wrap items-end justify-between gap-4">
              <div className="flex flex-wrap items-center gap-2.5">
                <span
                  className="inline-flex items-center gap-2 rounded-full border-transparent px-3 py-1 gv-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[color:var(--gv-ink)]"
                  style={{ background: "var(--gv-lime)" }}
                >
                  <span
                    className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-ink)]"
                    style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
                  />
                  <span>LIVE · STUDIO</span>
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
              className="gv-tight mt-0 w-full max-w-[880px] text-[clamp(36px,4.6vw,60px)] leading-[1.08] text-[color:var(--gv-ink)]"
              style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.04em" }}
            >
              {firstName}, hôm nay{" "}
              <span
                className="inline-block rotate-[-1deg] rounded-[10px] px-2.5 text-white"
                style={{ background: "var(--gv-accent)" }}
              >
                {nicheLabel}
              </span>{" "}
              đang có gì mới.
            </h1>
          </div>

          <div className="gv-fade-up gv-fade-up-delay-1 mt-7 w-full">
            <QueryComposer
              ref={composerRef}
              value={composerText}
              onChange={setComposerText}
              onSubmit={submitStudioComposer}
              placeholder={`Hỏi về hook, trend, hay kênh trong ngách ${nicheLabel}…`}
              nicheLabel={nicheLabel}
              showUrlChip={URL_IN_TEXT.test(composerText)}
              onPasteVideoClick={() => navigate("/app/video")}
              onPasteHandleClick={() =>
                fillComposer("Soi kênh đối thủ — dán @handle TikTok vào đây:\n")
              }
            />
          </div>

          <div className="gv-fade-up gv-fade-up-delay-2 mt-7 mb-14 w-full max-w-[880px]">
            <div className="mb-3 flex items-center gap-2">
              <span
                className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--gv-ink-4)]"
                aria-hidden
              />
              <p className="gv-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--gv-ink-4)]">
                Bắt đầu nhanh
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <QuickActions
                nicheLabel={nicheLabel}
                onAnswerPrompt={launchChat}
                onPrefillComposer={fillComposer}
              />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {suggestedPrompts.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => fillComposer(p)}
                  className="inline-flex min-h-[44px] max-w-full items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-left text-xs font-normal leading-snug text-[color:var(--gv-ink)] transition-colors hover:border-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)]"
                >
                  <Sparkles className="h-3 w-3 shrink-0 text-[color:var(--gv-accent)]" aria-hidden />
                  <span className="min-w-0">{p}</span>
                </button>
              ))}
            </div>
          </div>

          <hr className="mb-9 mt-0 border-0 border-t border-[color:var(--gv-rule)]" />

          <div className="gv-fade-up gv-fade-up-delay-2 mb-12">
            <HomeMyChannelSection profile={profile} nicheLabel={nicheLabel} />
          </div>

          <hr className="mb-9 mt-0 border-0 border-t border-[color:var(--gv-rule)]" />

          <div className="gv-fade-up gv-fade-up-delay-3 mb-12">
            <HomeSuggestionsToday
              nicheLabel={nicheLabel}
              nicheId={selectedNicheId}
              onSelectPrompt={launchChat}
            />
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
