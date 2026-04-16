import { useEffect, useState } from "react";

const CORPUS_DISPLAY = "46.000";

export function StreamingStatusText({
  phase,
  isVideoIntent,
  isConversational,
}: {
  phase: "idle" | "streaming" | "done" | "error";
  isVideoIntent: boolean;
  isConversational?: boolean;
}) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (phase !== "streaming") return;
    if (!isVideoIntent) return;
    const t = setInterval(() => setIdx((i) => (i + 1) % 3), 2000);
    return () => clearInterval(t);
  }, [phase, isVideoIntent]);

  if (phase !== "streaming") return null;

  if (isConversational) {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-[var(--muted)]">
        Đang suy nghĩ
        <span className="animate-pulse">...</span>
      </span>
    );
  }

  if (!isVideoIntent) {
    return <p className="text-sm text-[var(--muted)]">Đang phân tích...</p>;
  }

  const lines = [
    "Đang tải video...",
    "Đang xem video của bạn...",
    `Đang so sánh với ${CORPUS_DISPLAY} video trong niche...`,
  ];
  return <p className="text-sm text-[var(--muted)]">{lines[idx]}</p>;
}
