import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { Plus, Sparkles } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { QueryComposer } from "@/components/v2/QueryComposer";
import { TopBar } from "@/components/v2/TopBar";
import { DataFreshnessPill } from "@/components/v2/DataFreshnessPill";
import { useHomePulse } from "@/hooks/useHomePulse";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useNicheRowsForIds } from "@/hooks/useTopNiches";
import { useTopPatterns } from "@/hooks/useTopPatterns";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { logUsage } from "@/lib/logUsage";
import { profileFirstNicheId, profileFollowedNicheIds } from "@/lib/profileNiches";
import { TickerMarquee } from "./components/TickerMarquee";
import { FirstRunWelcomeStrip } from "./components/FirstRunWelcomeStrip";
import { HomeMyChannelSection } from "./components/HomeMyChannelSection";
import { HomeSuggestionsToday } from "./components/HomeSuggestionsToday";
import { NichePicker } from "./components/NichePicker";
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

  // PR-5 — tối đa 3 ngách trong ``niche_ids``; default chọn = slot [0]. ``selectedNicheId``
  // drives gợi ý, pulse, ticker, kịch bản sáng, patterns. Kênh của bạn dùng cùng
  // default server (id đầu trong hồ sơ) cho /channel/analyze.
  const followedNicheIds = useMemo(
    () => profileFollowedNicheIds(profile),
    [profile],
  );
  const { data: followedNiches = [] } = useNicheRowsForIds(followedNicheIds);
  const defaultNicheId = profileFirstNicheId(profile) ?? followedNicheIds[0] ?? null;
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

  const { data: pulse } = useHomePulse(true, selectedNicheId);

  // D7 — LIVE badge surfaces a relative timestamp ("LIVE · CẬP NHẬT
  // 2 PHÚT TRƯỚC") per design pack ``screens/home.jsx`` line 98.
  // Falls back to "LIVE · STUDIO" when ``pulse.as_of`` isn't loaded
  // yet so the chip renders something during the first paint.
  const liveBadgeLabel = useMemo(() => {
    if (!pulse?.as_of) return "LIVE · STUDIO";
    const rel = formatRelativeSinceVi(new Date(), new Date(pulse.as_of));
    if (rel === "—") return "LIVE · STUDIO";
    return `LIVE · CẬP NHẬT ${rel.toUpperCase()}`;
  }, [pulse?.as_of]);

  const nicheLabel = useMemo(() => {
    const id = selectedNicheId;
    if (!id) return "ngách của bạn";
    return niches.find((n) => n.id === id)?.name ?? "ngách của bạn";
  }, [selectedNicheId, niches]);

  // PR-cleanup-E — greeting + composer signals.
  // ``newHookCount``: count of hot patterns whose previous-week instance
  // count was 0 (true "mới" rather than "đang lên"). Same query
  // HooksTable already fires (limit=6, dedupes via React Query cache).
  const { data: topPatterns = [] } = useTopPatterns(selectedNicheId);
  const newHookCount = useMemo(
    () => topPatterns.filter((p) => p.weekly_instance_count_prev === 0).length,
    [topPatterns],
  );

  // Corpus count for the composer chip — pulled from
  // ``niche_intelligence.sample_size`` via ``useNicheRowsForIds``.
  // Hidden when 0 (empty niche / first-day account) so we don't claim
  // a corpus that doesn't exist.
  const currentNicheCount = useMemo(() => {
    if (!selectedNicheId) return undefined;
    const found = followedNiches.find((n) => n.id === selectedNicheId);
    return found && found.hot > 0 ? found.hot : undefined;
  }, [followedNiches, selectedNicheId]);

  // Capitalised because ``firstName`` now leads the H1 (was preceded by
  // "Chào "); lowercase looks wrong at the start of a sentence.
  const displayName = profile?.display_name?.trim() || "Bạn";
  const firstName = displayName.split(/\s+/).pop() ?? displayName;

  // Bắt đầu nhanh — mỗi thẻ gắn với một intent trong ``detectIntent`` /
  // ``planAnswerEntry`` (Studio → /app/answer hoặc redirect kênh), tránh
  // placeholder URL/@ vì không classify được. Giữ ngách trong câu hỏi bằng
  // ``nicheLabel``.
  const suggestedPrompts = useMemo(
    () => [
      `Xu hướng và chủ đề nào đang nổi trong ngách ${nicheLabel} tuần này?`,
      `Hướng nội dung và format nào đang chạy tốt nhất trong ngách ${nicheLabel}?`,
      `Trong ngách ${nicheLabel}, ngách con nào đáng khai thác hoặc mở rộng thêm?`,
      `Nên đăng TikTok khung giờ nào trong tuần để tối ưu reach?`,
      `Viết brief sản xuất nội dung tuần này cho ngách ${nicheLabel}.`,
      `Video của mình flop — phân tích nguyên nhân và nên chỉnh gì?`,
      `Soi kênh của mình — tổng quan hook, format và gợi ý cải thiện.`,
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
              <DataFreshnessPill asOfIso={pulse?.as_of} />
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
        <TickerMarquee viewNicheId={selectedNicheId} />

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
                  <span>{liveBadgeLabel}</span>
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
              Chào {firstName}. Hôm nay{" "}
              <span
                className="inline-block rotate-[-1deg] rounded-[10px] px-2.5 text-white"
                style={{ background: "var(--gv-accent)" }}
              >
                {nicheLabel}
              </span>{" "}
              {newHookCount > 0 ? (
                <>
                  có{" "}
                  <span style={{ color: "var(--gv-accent-2-deep, var(--gv-accent-2))" }}>
                    {newHookCount} hook
                  </span>{" "}
                  mới đang nổ.
                </>
              ) : (
                "đang có gì mới."
              )}
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
              corpusCount={currentNicheCount}
              showUrlChip={URL_IN_TEXT.test(composerText)}
              onPasteVideoClick={() =>
                fillComposer("Tại sao video này nổ/flop? Dán link TikTok vào đây:\n")
              }
              onPasteHandleClick={() =>
                fillComposer("Soi kênh đối thủ — dán @handle TikTok vào đây:\n")
              }
            />
          </div>

          {/* PR-cleanup-A — "BẮT ĐẦU NHANH" prompt-shortcut chips only.
           * Design pack QuickStartChips (home.jsx:404-426) — composer-fill
           * chips with no navigation grid; the earlier QuickActions component
           * was deleted because the design pivoted to a single chip row. */}
          <div className="gv-fade-up gv-fade-up-delay-2 mt-7 mb-14 w-full">
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
            <HomeSuggestionsToday nicheId={selectedNicheId} />
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
