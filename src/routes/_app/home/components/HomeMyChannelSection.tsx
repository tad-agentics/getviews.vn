import { memo, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router";

import { SectionHeader } from "@/components/v2/SectionHeader";
import { useProfile } from "@/hooks/useProfile";
import { ChannelStudioPanel } from "@/routes/_app/channel/components/ChannelStudioPanel";
import { ChannelBridgeRibbon } from "./ChannelBridgeRibbon";
import { scrollToSuggestionsTier } from "./scrollToTier";

/**
 * Studio Home — channel intelligence block (§6 / F4–F5).
 *
 * Embeds Nhanh + Sâu channel analysis on `/app` instead of a separate tab.
 * Deep-link: ``/app?handle=creator&depth=sau``.
 */
export const HomeMyChannelSection = memo(function HomeMyChannelSection() {
  const { data: profile } = useProfile();
  const [searchParams] = useSearchParams();
  const [showBridge, setShowBridge] = useState(false);

  const tiktokHandle = (profile as { tiktok_handle?: string | null } | null)?.tiktok_handle ?? null;
  const activeHandle = searchParams.get("handle") ?? tiktokHandle;

  const scrollToChannel = useCallback(() => {
    if (typeof document === "undefined") return;
    document.querySelector("[data-section='channel']")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, []);

  // Deep-link with ?handle= — scroll channel block (unless scrollTier takes priority).
  useEffect(() => {
    const handle = searchParams.get("handle");
    const scrollTier = searchParams.get("scrollTier");
    if (!handle || scrollTier) return;
    const id = window.requestAnimationFrame(scrollToChannel);
    return () => window.cancelAnimationFrame(id);
  }, [searchParams, scrollToChannel]);

  const handleScrollToSuggestions = useCallback(() => {
    scrollToSuggestionsTier("01");
  }, []);

  return (
    <section
      className="mb-14 scroll-mt-20"
      data-section="channel"
      aria-labelledby="home-channel-heading"
    >
      <SectionHeader
        kicker="SOI KÊNH"
        title="Kênh TikTok"
        titleId="home-channel-heading"
        caption={
          activeHandle
            ? "Nhanh đọc corpus; Sâu chạy memo SSE với score card, peers và channel findings V5 §2."
            : "Dán @handle hoặc gắn TikTok trong Cài đặt — phân tích ngay trên Studio, không cần tab riêng."
        }
        className="!mb-6"
      />

      <div className="overflow-hidden rounded-[18px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
        <div className="px-5 py-6 sm:px-7">
          <ChannelStudioPanel
            defaultHandle={tiktokHandle}
            onBridgeEligible={() => setShowBridge(true)}
          />
        </div>
        {showBridge ? (
          <ChannelBridgeRibbon onScrollToSuggestions={handleScrollToSuggestions} />
        ) : null}
      </div>
    </section>
  );
});
