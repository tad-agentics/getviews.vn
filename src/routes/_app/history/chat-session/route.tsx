import { lazy, Suspense } from "react";
import type { MetaFunction } from "react-router";
import { pageMeta } from "@/lib/pageTitle";

export const meta: MetaFunction = () => pageMeta("Phiên trò chuyện");

const ChatSessionReadScreen = lazy(() => import("../ChatSessionReadScreen"));

/** Read-only legacy chat transcript (`/app/history/chat/:sessionId`). */
export default function HistoryChatSessionRoute() {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          aria-label="Đang tải"
          className="min-h-[40vh] flex-1 animate-pulse rounded-lg bg-[var(--surface-alt)]"
        />
      }
    >
      <ChatSessionReadScreen />
    </Suspense>
  );
}
