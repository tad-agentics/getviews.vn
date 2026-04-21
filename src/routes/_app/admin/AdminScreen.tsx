/**
 * Phase D.6 — /app/admin operator dashboard.
 *
 * Editorial layout mirrors `artifacts/uiux-reference/screens/home.jsx`:
 * sticky TopBar, 1320px main wrap, SectionHeader with kicker dot + tight
 * 28px title for each panel, `<hr>` rules between sections, and
 * `gv-fade-up` staggered entries. The four panels (CorpusHealth,
 * EnsembleCredits, Logs, Triggers) handle their own data + visual
 * density; this file is purely the routing + section rhythm.
 *
 * Gate: the SPA checks `useIsAdmin()` and bounces non-admins to /app.
 * The server-side `require_admin` dep on every /admin/* endpoint is the
 * authoritative boundary — this screen only decides what the SPA
 * bothers to render.
 */
import { useEffect } from "react";
import { useNavigate } from "react-router";
import { AppLayout } from "@/components/AppLayout";
import { SectionHeader } from "@/components/v2/SectionHeader";
import { TopBar } from "@/components/v2/TopBar";
import { useIsAdmin } from "@/hooks/useIsAdmin";
import { ActionLogPanel } from "./ActionLogPanel";
import { CorpusHealthPanel } from "./CorpusHealthPanel";
import { EnsembleCreditsPanel } from "./EnsembleCreditsPanel";
import { LogsPanel } from "./LogsPanel";
import { TriggersPanel } from "./TriggersPanel";

export default function AdminScreen() {
  const { isAdmin, isLoading } = useIsAdmin();
  const navigate = useNavigate();

  useEffect(() => {
    // Bounce non-admins to Studio. The server's require_admin dep will
    // also 403 any /admin/* fetch; routing away keeps the URL honest and
    // prevents flashes of panel chrome before the first query fails.
    if (!isLoading && !isAdmin) navigate("/app", { replace: true });
  }, [isAdmin, isLoading, navigate]);

  if (isLoading) {
    return (
      <AppLayout active="admin">
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-[var(--gv-radius-lg)] bg-[color:var(--gv-canvas-2)]"
        />
      </AppLayout>
    );
  }
  if (!isAdmin) {
    // Keep the redirect-effect tick quiet — render the empty shell so the
    // layout doesn't reflow between "loading" and "bounce".
    return <AppLayout active="admin">{null}</AppLayout>;
  }

  return (
    <AppLayout active="admin">
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar kicker="ADMIN · OPS CONSOLE" title="Sức khỏe hệ thống" />

        <main className="gv-home-wrap mx-auto w-full max-w-[1320px]">
          <section className="gv-fade-up">
            <SectionHeader
              kicker="CORPUS · INGEST + CLAIM TIERS"
              title="Corpus health"
              caption="Lượng video 7d / 30d / 90d theo niche và tier claim hiện tại."
            />
            <CorpusHealthPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-1">
            <SectionHeader
              kicker="ENSEMBLEDATA · USED UNITS"
              title="Credit runway"
              caption="Units đã dùng mỗi UTC-day và projection 30 ngày."
            />
            <EnsembleCreditsPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-2">
            <SectionHeader
              kicker="CLOUD RUN · STDOUT TAIL"
              title="Logs"
              caption="Lọc theo severity và cửa sổ thời gian; click để mở rộng payload."
              kickerTone="muted"
            />
            <LogsPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-3">
            <SectionHeader
              kicker="MANUAL RUN · CRON JOBS"
              title="Triggers"
              caption="Chạy tay các pipeline định kỳ. Mỗi job có confirm trước khi fire."
            />
            <TriggersPanel />
          </section>

          <hr className="my-9 border-0 border-t border-[color:var(--gv-rule)]" />

          <section className="gv-fade-up gv-fade-up-delay-3">
            <SectionHeader
              kicker="AUDIT · WHO RAN WHAT"
              title="Action log"
              caption="Lịch sử các trigger gần đây kèm status + duration."
              kickerTone="muted"
            />
            <ActionLogPanel />
          </section>
        </main>
      </div>
    </AppLayout>
  );
}
