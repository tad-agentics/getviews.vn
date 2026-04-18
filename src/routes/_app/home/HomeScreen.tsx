import { useMemo, useRef } from "react";
import { useNavigate } from "react-router";
import { Paperclip, Film, Eye, Mic, Bookmark, Plus, Sparkles } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { Composer } from "@/components/v2/Composer";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { TopBar } from "@/components/v2/TopBar";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useHomePulse } from "@/hooks/useHomePulse";
import { TickerMarquee } from "./components/TickerMarquee";
import { PulseCard } from "./components/PulseCard";
import { HooksTable } from "./components/HooksTable";
import { BreakoutGrid } from "./components/BreakoutGrid";
import { HomeMorningRitual } from "./components/HomeMorningRitual";
import { QuickActions } from "./components/QuickActions";
import { DateChip } from "./components/DateChip";
import { NichePicker } from "./components/NichePicker";

/**
 * Getviews Studio — Home screen (Phase A · A3.4).
 *
 * Matches UIUX reference order: ticker → greeting → composer → suggested
 * chips → <hr> → morning ritual → <hr> → quick actions + pulse → hooks → breakouts.
 */

function relativeVi(now: Date, since: Date | null): string {
  if (!since) return "—";
  const mins = Math.floor((now.getTime() - since.getTime()) / 60000);
  if (mins < 2) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
}

function formatCount(n: number): string {
  return n.toLocaleString("vi-VN");
}

const CHIP_BTN =
  "inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 text-xs text-[color:var(--gv-ink-2)] transition-colors hover:bg-[color:var(--gv-canvas-2)]";

export default function HomeScreen() {
  const navigate = useNavigate();
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const { data: profile } = useProfile();
  const { data: niches = [] } = useNicheTaxonomy();
  const { data: pulse } = useHomePulse();

  const nicheLabel = useMemo(() => {
    const id = profile?.primary_niche ?? null;
    if (!id) return "ngách của bạn";
    return niches.find((n) => n.id === id)?.name ?? "ngách của bạn";
  }, [profile?.primary_niche, niches]);

  const greetingHookCount = pulse?.new_hooks_this_week ?? null;
  const videosInNiche = pulse?.videos_this_week ?? null;

  const displayName = profile?.display_name?.trim() || "bạn";
  const firstName = displayName.split(/\s+/).pop() ?? displayName;

  const asOf = useMemo(() => {
    if (!pulse?.as_of) return null;
    const d = new Date(pulse.as_of);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [pulse?.as_of]);
  const asOfRelative = useMemo(() => relativeVi(new Date(), asOf), [asOf]);

  const suggestedPrompts = useMemo(
    () => [
      `Xu hướng đang hot trong ${nicheLabel} tuần này?`,
      `Hook nào đang hiệu quả nhất trong ${nicheLabel}?`,
      `Format nào đang tăng view nhanh nhất ngách ${nicheLabel}?`,
      "Gợi ý chủ đề video cho tuần tới dựa trên trend hiện tại.",
    ],
    [nicheLabel],
  );

  const launchChat = (text: string) => {
    navigate("/app/chat", { state: { initialPrompt: text } });
  };

  const fillComposer = (text: string) => {
    const el = composerRef.current;
    if (!el) return;
    el.value = text;
    el.focus();
  };

  const composerChips = (
    <>
      <button
        type="button"
        title="Đính kèm link / file"
        className="inline-flex h-8 w-8 items-center justify-center rounded-full text-[color:var(--gv-ink-4)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink-2)]"
      >
        <Paperclip className="h-4 w-4" strokeWidth={1.7} />
      </button>
      <button
        type="button"
        className={CHIP_BTN}
        onClick={() =>
          fillComposer("Dán link video TikTok bạn muốn soi (dán link vào tin nhắn):\n")
        }
      >
        <Film className="h-3.5 w-3.5" strokeWidth={1.7} />
        Dán link video
      </button>
      <button
        type="button"
        className={`${CHIP_BTN} hidden sm:inline-flex`}
        onClick={() =>
          fillComposer("Soi kênh đối thủ — dán @handle TikTok vào đây:\n")
        }
      >
        <Eye className="h-3.5 w-3.5" strokeWidth={1.7} />
        Dán @handle
      </button>
      {videosInNiche != null ? (
        <span className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
          {formatCount(videosInNiche)}+ video
        </span>
      ) : null}
    </>
  );

  const composerToolbarEnd = (
    <button
      type="button"
      title="Đọc vào"
      className="hidden h-8 w-8 items-center justify-center rounded-full text-[color:var(--gv-ink-4)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink-2)] sm:inline-flex"
    >
      <Mic className="h-4 w-4" strokeWidth={1.7} />
    </button>
  );

  return (
    <AppLayout active="home" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="STUDIO"
          title="Sảnh Sáng Tạo"
          right={
            <>
              <span className="hide-narrow hidden items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)] md:inline-flex">
                <span
                  className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]"
                  style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
                />
                Dữ liệu cập nhật {asOfRelative}
              </span>
              <Btn variant="ghost" size="sm" className="hidden sm:inline-flex">
                <Bookmark className="h-3.5 w-3.5" strokeWidth={1.7} />
                Đã Lưu
              </Btn>
              <Btn variant="ink" size="sm" onClick={() => navigate("/app/chat")}>
                <Plus className="h-3.5 w-3.5" strokeWidth={2} />
                Phân tích mới
              </Btn>
            </>
          }
        />
        <TickerMarquee />

        <main className="gv-home-wrap mx-auto w-full max-w-[1320px]">
          <div className="gv-fade-up">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="flex flex-wrap items-center gap-2.5">
                <span
                  className="inline-flex items-center gap-2 rounded-full border-transparent px-3 py-1 gv-mono text-[11px] font-semibold uppercase tracking-[0.12em] text-[color:var(--gv-ink)]"
                  style={{ background: "var(--gv-lime)" }}
                >
                  <span
                    className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-ink)]"
                    style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
                  />
                  <span>
                    LIVE · CẬP NHẬT{" "}
                    <span className="normal-case font-medium tracking-[0.08em]">{asOfRelative}</span>
                  </span>
                </span>
                <DateChip />
              </div>
              <div className="min-w-0 shrink-0">
                <NichePicker />
              </div>
            </div>

            <h1
              className="gv-tight mt-6 max-w-[880px] text-[clamp(36px,4.6vw,60px)] leading-[1.02] text-[color:var(--gv-ink)]"
              style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.04em" }}
            >
              Chào {firstName}. Hôm nay{" "}
              <span
                className="inline-block rotate-[-1deg] rounded-[10px] px-2.5 text-white"
                style={{ background: "var(--gv-accent)" }}
              >
                {nicheLabel}
              </span>{" "}
              {greetingHookCount != null && greetingHookCount > 0 ? (
                <>
                  có{" "}
                  <span className="font-semibold text-[color:var(--gv-pos)]">
                    {greetingHookCount} hook mới
                  </span>{" "}
                  đang nổ
                </>
              ) : (
                <>đang có gì mới</>
              )}
              .
            </h1>
          </div>

          <div className="gv-fade-up gv-fade-up-delay-1 mt-7 max-w-[860px]">
            <Composer
              ref={composerRef}
              layout="studio"
              toolbarEnd={composerToolbarEnd}
              placeholder={`Hỏi về hook, trend, hay kênh trong ngách ${nicheLabel}…`}
              onSubmit={launchChat}
              leftChips={composerChips}
            />
          </div>

          <div className="gv-fade-up gv-fade-up-delay-2 mt-6 flex max-w-[860px] flex-wrap gap-2">
            {suggestedPrompts.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => fillComposer(p)}
                className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-left text-[13px] leading-snug text-[color:var(--gv-ink)] transition-colors hover:border-[color:var(--gv-ink)]"
              >
                <Sparkles className="h-3 w-3 shrink-0 text-[color:var(--gv-accent)]" aria-hidden />
                <span className="min-w-0">{p}</span>
              </button>
            ))}
          </div>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)] md:my-10" />

          <div className="gv-fade-up gv-fade-up-delay-3">
            <HomeMorningRitual nicheLabel={nicheLabel} onSelectPrompt={launchChat} />
          </div>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)] md:my-10" />

          <div className="gv-fade-up gv-fade-up-delay-3 grid grid-cols-1 gap-6 min-[901px]:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
            <QuickActions />
            <div>
              <SectionHeader
                kicker="NHỊP TUẦN"
                title="Pulse"
                caption="Tín hiệu sống trong ngách của bạn."
              />
              <div className="mt-4">
                <PulseCard omitKicker />
              </div>
            </div>
          </div>

          <div className="mt-12">
            <HooksTable nicheId={profile?.primary_niche ?? null} />
          </div>

          <div className="mt-12">
            <BreakoutGrid nicheId={profile?.primary_niche ?? null} />
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
