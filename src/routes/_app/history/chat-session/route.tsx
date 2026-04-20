import { lazy, Suspense } from "react";

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
