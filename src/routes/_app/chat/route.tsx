import { lazy, Suspense } from "react";

const ChatScreen = lazy(() => import("../ChatScreen"));

/**
 * `/app/chat` — the chat workspace. Previously lived at `/app`; moved
 * here in Phase A · A3.3 when HomeScreen took over the studio entry.
 * `/app?session=X` is redirected to `/app/chat?session=X` by the index
 * route so bookmarks continue to work.
 */
export default function AppChatRoute() {
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
      <ChatScreen />
    </Suspense>
  );
}
