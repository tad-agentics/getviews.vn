import { useMemo } from "react";
import { useNavigate } from "react-router";
import { Paperclip, Film, Eye, Mic } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Composer } from "@/components/v2/Composer";
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
 * Layout (top → bottom):
 *   1. Full-bleed ticker marquee
 *   2. Greeting row — LIVE chip · date chip · NichePicker
 *   3. Greeting h1 with rotated accent pill around niche name
 *   4. Composer (neo-brutalist) with left chip row (paperclip / link /
 *      handle / video-count / mic)
 *   5. Morning ritual — 3 ready-to-shoot scripts
 *   6. 2-col grid: QuickActions (2×3) + PulseCard
 *   7. HooksTable (6-col) — full width
 *   8. BreakoutGrid (3 tiles)
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

export default function HomeScreen() {
  const navigate = useNavigate();
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

  const launchChat = (text: string) => {
    navigate("/app/chat", { state: { initialPrompt: text } });
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
      <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 text-xs text-[color:var(--gv-ink-2)]">
        <Film className="h-3.5 w-3.5" strokeWidth={1.7} />
        Dán link video
      </span>
      <span className="hidden items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 text-xs text-[color:var(--gv-ink-2)] sm:inline-flex">
        <Eye className="h-3.5 w-3.5" strokeWidth={1.7} />
        Dán @handle
      </span>
      {videosInNiche != null ? (
        <span className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
          {formatCount(videosInNiche)}+ video
        </span>
      ) : null}
      <button
        type="button"
        title="Đọc vào"
        className="hidden h-8 w-8 items-center justify-center rounded-full text-[color:var(--gv-ink-4)] hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink-2)] sm:inline-flex"
      >
        <Mic className="h-4 w-4" strokeWidth={1.7} />
      </button>
    </>
  );

  return (
    <AppLayout active="home" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)]">
        <TickerMarquee />

        <main className="gv-home-wrap mx-auto w-full max-w-[1320px] px-4 py-8 md:px-6 md:py-10">
          {/* Greeting chip row: LIVE · date · NichePicker */}
          <div className="flex flex-wrap items-center gap-3">
            <span
              className="inline-flex items-center gap-2 rounded-full border-transparent px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.12em] text-[color:var(--gv-ink)]"
              style={{ background: "var(--gv-lime)" }}
            >
              <span
                className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-ink)]"
                style={{ animation: "pulse 1.6s ease-in-out infinite" }}
              />
              Live · Cập nhật {asOfRelative}
            </span>
            <DateChip />
            <div className="ml-auto">
              <NichePicker />
            </div>
          </div>

          {/* Greeting h1 — rotated accent pill, blue hook count */}
          <h1
            className="gv-tight mt-6 max-w-[24ch] text-[clamp(30px,4.6vw,60px)] leading-[1.02] text-[color:var(--gv-ink)]"
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
                <span className="text-[color:var(--gv-pos)]">
                  {greetingHookCount} hook mới
                </span>{" "}
                đang nổ
              </>
            ) : (
              <>đang có gì mới</>
            )}
            .
          </h1>

          {/* Composer with chip row */}
          <div className="mt-7 max-w-[860px]">
            <Composer
              placeholder={`Hỏi về hook, trend, hay kênh trong ngách ${nicheLabel}…`}
              onSubmit={launchChat}
              leftChips={composerChips}
            />
          </div>

          <div className="mt-12 space-y-12">
            {/* Morning Ritual */}
            <HomeMorningRitual nicheLabel={nicheLabel} onSelectPrompt={launchChat} />

            {/* 2-col: QuickActions + PulseCard */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
              <QuickActions />
              <PulseCard />
            </div>

            {/* Full-width HooksTable */}
            <HooksTable nicheId={profile?.primary_niche ?? null} />

            {/* Breakouts */}
            <BreakoutGrid nicheId={profile?.primary_niche ?? null} />
          </div>
        </main>
      </div>
    </AppLayout>
  );
}
