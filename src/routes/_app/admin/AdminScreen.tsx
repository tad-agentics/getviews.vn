/**
 * Phase D.6 — /app/admin operator dashboard shell.
 *
 * Mounts four panels (corpus health / ensemble credits / cloud-run logs /
 * manual triggers) behind a client-side `is_admin` gate. Each panel ships
 * in its own commit; this file is the routing + layout spine they hang
 * off. Server-side `require_admin` on every data endpoint is the real
 * authorization boundary — this screen only decides what the SPA bothers
 * to render.
 */
import { useEffect } from "react";
import { useNavigate } from "react-router";
import { AppLayout } from "@/components/AppLayout";
import { useIsAdmin } from "@/hooks/useIsAdmin";
import { CorpusHealthPanel } from "./CorpusHealthPanel";
import { EnsembleCreditsPanel } from "./EnsembleCreditsPanel";
import { LogsPanel } from "./LogsPanel";
import { TriggersPanel } from "./TriggersPanel";

function AdminPanelCard({
  title,
  subtitle,
  children,
  fullWidth,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  fullWidth?: boolean;
}) {
  return (
    <section
      className={`flex flex-col gap-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 ${
        fullWidth ? "md:col-span-2" : ""
      }`}
    >
      <header>
        <h2 className="gv-serif text-[18px] leading-snug text-[color:var(--gv-ink)]">
          {title}
        </h2>
        {subtitle ? (
          <p className="mt-1 gv-mono text-[11px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
            {subtitle}
          </p>
        ) : null}
      </header>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export default function AdminScreen() {
  const { isAdmin, isLoading } = useIsAdmin();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect non-admins back to Studio. The server will also reject any
    // /admin/* fetch with 403, but bouncing the route keeps the URL tidy
    // and prevents render of the shell to someone who shouldn't see it.
    if (!isLoading && !isAdmin) navigate("/app", { replace: true });
  }, [isAdmin, isLoading, navigate]);

  if (isLoading) {
    return (
      <AppLayout>
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
        />
      </AppLayout>
    );
  }

  if (!isAdmin) {
    // Render a safe no-op frame while the redirect effect fires; prevents
    // a flash of real admin content between the profile resolving and the
    // navigate() landing.
    return <AppLayout>{null}</AppLayout>;
  }

  return (
    <AppLayout>
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-6 px-4 py-6 md:px-8">
        <header className="flex flex-col gap-1">
          <p className="gv-mono text-[11px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
            Admin · Operator dashboard
          </p>
          <h1 className="gv-serif text-[28px] leading-tight text-[color:var(--gv-ink)]">
            Sức khỏe hệ thống
          </h1>
          <p className="text-[13px] text-[color:var(--gv-ink-3)]">
            Theo dõi Corpus, EnsembleData credits, Cloud Run logs và chạy thủ công các job định kỳ.
          </p>
        </header>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <AdminPanelCard title="Corpus health" subtitle="per-niche ingest + claim tiers" fullWidth>
            <CorpusHealthPanel />
          </AdminPanelCard>

          <AdminPanelCard title="EnsembleData credits" subtitle="used units theo ngày" fullWidth>
            <EnsembleCreditsPanel />
          </AdminPanelCard>

          <AdminPanelCard title="Cloud Run logs" subtitle="stdout tail theo filter" fullWidth>
            <LogsPanel />
          </AdminPanelCard>

          <AdminPanelCard title="Manual triggers" subtitle="chạy pipeline thủ công">
            <TriggersPanel />
          </AdminPanelCard>
        </div>
      </div>
    </AppLayout>
  );
}
