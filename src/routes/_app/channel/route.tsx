import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Phân tích kênh");

const ChannelScreen = lazy(() => import("./ChannelScreen"));

/**
 * `/app/channel` — Phase B · B.3.3 kênh đối thủ. Query: `?handle=` (TikTok,
 * có hoặc không @), optional `force_refresh=true`.
 */
export default function AppChannelRoute() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[color:var(--gv-canvas-2)]"
        />
      }
    >
      <ChannelScreen />
    </Suspense>
  );
}
