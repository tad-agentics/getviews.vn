import { AppLayout } from "@/components/AppLayout";
import { TopBar } from "@/components/v2/TopBar";
import { useProfile } from "@/hooks/useProfile";
import { ChannelStudioPanel } from "./components/ChannelStudioPanel";

/**
 * `/app/channel` — full-page channel intelligence (F4/F5).
 * Entry: composer pill **Khám Kênh** or `planAnswerEntry` channel intents.
 */
export default function ChannelScreen() {
  const { data: profile } = useProfile();
  const tiktokHandle = (profile as { tiktok_handle?: string | null } | null)?.tiktok_handle ?? null;

  return (
    <AppLayout active="home" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar kicker="SOI KÊNH" title="Phân tích kênh TikTok" />
        <main className="gv-home-wrap mx-auto w-full max-w-[880px] px-4 pb-16 pt-2 sm:px-6">
          <ChannelStudioPanel defaultHandle={tiktokHandle} />
        </main>
      </div>
    </AppLayout>
  );
}
