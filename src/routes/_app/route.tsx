import { lazy, Suspense } from "react";

const ChatScreen = lazy(() => import("./ChatScreen"));

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
