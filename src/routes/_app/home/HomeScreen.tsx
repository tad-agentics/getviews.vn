import { useMemo } from "react";
import { useNavigate } from "react-router";
import { AppLayout } from "@/components/AppLayout";
import { Composer } from "@/components/v2/Composer";
import { Kicker } from "@/components/v2/Kicker";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useHomePulse } from "@/hooks/useHomePulse";
import { TickerMarquee } from "./components/TickerMarquee";
import { PulseCard } from "./components/PulseCard";
import { HooksTable } from "./components/HooksTable";
import { BreakoutGrid } from "./components/BreakoutGrid";
import { HomeMorningRitual } from "./components/HomeMorningRitual";

/**
 * Getviews Studio — Home screen (Phase A · A3.2).
 *
 * Layout (top → bottom):
 *   1. Full-bleed ticker marquee
 *   2. Live-data chip + niche pill + greeting h1
 *   3. Neo-brutalist composer (routes submission into existing chat)
 *   4. Morning ritual — 3 ready-to-shoot scripts
 *   5. 2-col grid: ink-filled PulseCard + HooksTable
 *   6. BreakoutGrid (3 tiles)
 *
 * Lives alongside the existing /app (chat) route during A3.2. A3.3 swaps
 * the default and moves chat to /app/chat.
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

  // The greeting's "X hook mới đang nổ" number — only render a concrete
  // count when the pulse endpoint returned something we can claim.
  const greetingHookCount = pulse?.new_hooks_this_week ?? null;

  const displayName = profile?.display_name?.trim() || "bạn";
  const firstName = displayName.split(/\s+/).pop() ?? displayName;

  const asOf = useMemo(() => {
    if (!pulse?.as_of) return null;
    const d = new Date(pulse.as_of);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [pulse?.as_of]);
  const asOfRelative = useMemo(
    () => relativeVi(new Date(), asOf),
    [asOf],
  );

  /** Chat launcher — prefill ChatScreen textarea via navigation state. */
  const launchChat = (text: string) => {
    navigate("/app/chat", { state: { initialPrompt: text } });
  };

  return (
    <AppLayout active="home" enableMobileSidebar>
    <div className="min-h-full w-full bg-[color:var(--gv-canvas)]">
      <TickerMarquee />

      <main className="mx-auto w-full max-w-[1280px] px-4 py-8 md:px-6 md:py-10">
        {/* Live-data + niche pill row */}
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full bg-[color:var(--gv-paper)] px-3 py-1 text-[11px] uppercase tracking-wider text-[color:var(--gv-ink-3)] border border-[color:var(--gv-rule)]">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]" />
            Dữ liệu cập nhật {asOfRelative}
          </span>
          <Kicker>STUDIO · CREATOR</Kicker>
        </div>

        {/* Greeting h1 */}
        <h1
          className="gv-tight mt-4 max-w-[24ch] text-[clamp(32px,5vw,56px)] leading-[1.05] text-[color:var(--gv-ink)]"
          style={{ fontFamily: "var(--gv-font-display)" }}
        >
          Chào {firstName}. Hôm nay{" "}
          <span
            className="inline-block rotate-[-1deg] rounded-[10px] bg-[color:var(--gv-accent-soft)] px-2 py-0.5 text-[color:var(--gv-accent-deep)]"
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

        {/* Composer */}
        <div className="mt-6 max-w-[720px]">
          <Composer
            placeholder="Hỏi mình bất kỳ điều gì về ngách của bạn…"
            onSubmit={launchChat}
          />
        </div>

        <div className="mt-10 space-y-10">
          {/* Morning Ritual */}
          <HomeMorningRitual nicheLabel={nicheLabel} onSelectPrompt={launchChat} />

          {/* 2-col grid: PulseCard + HooksTable */}
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(280px,380px)_1fr]">
            <PulseCard />
            <HooksTable nicheId={profile?.primary_niche ?? null} />
          </div>

          {/* Breakouts */}
          <BreakoutGrid nicheId={profile?.primary_niche ?? null} />
        </div>
      </main>
    </div>
    </AppLayout>
  );
}
