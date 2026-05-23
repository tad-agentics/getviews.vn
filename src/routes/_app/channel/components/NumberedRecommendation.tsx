/**
 * NumberedRecommendation — hero / regular / anti (ngừng làm) groups.
 */

import type { ChannelRecommendation } from "@/lib/api-types";

interface NumberedRecommendationProps {
  recommendation: ChannelRecommendation;
  /** Visual variant for hero row */
  variant?: "hero" | "default" | "anti";
}

export function NumberedRecommendation({
  recommendation,
  variant = "default",
}: NumberedRecommendationProps) {
  const isAnti = variant === "anti";
  const isHero = variant === "hero";

  return (
    <div
      className={
        "flex gap-3 items-start py-3 border-b border-[color:var(--border)] last:border-0 " +
        (isAnti ? "bg-[color-mix(in_srgb,var(--gv-neg)_4%,transparent)] rounded-lg px-2 -mx-2" : "")
      }
    >
      <span
        className={
          "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center " +
          "text-[11px] font-bold font-mono " +
          (isAnti
            ? "bg-[color:var(--gv-neg-deep)] text-white"
            : isHero
              ? "bg-[color:var(--gv-accent-deep)] text-white"
              : "bg-[color:var(--primary)] text-[color:var(--primary-foreground)]")
        }
        aria-hidden
      >
        {isAnti ? "✕" : recommendation.index}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[color:var(--foreground)] leading-snug">
          {isHero ? (
            <>
              <span className="mr-2 rounded bg-[color:var(--gv-accent)]/20 px-1.5 py-0.5 text-[11px] font-bold gv-kicker tracking-wide text-[color:var(--gv-accent-deep)]">
                Ưu tiên
              </span>
              {recommendation.title}
            </>
          ) : (
            recommendation.title
          )}
        </p>
        {recommendation.body && (
          <p className="text-sm text-[color:var(--muted)] mt-1 leading-relaxed">{recommendation.body}</p>
        )}
      </div>
    </div>
  );
}

interface RecommendationListProps {
  recommendations: ChannelRecommendation[];
}

export function RecommendationList({ recommendations }: RecommendationListProps) {
  if (!recommendations || recommendations.length === 0) return null;

  const sorted = [...recommendations].sort((a, b) => {
    const ak = a.kind ?? (a.index === 1 ? "hero" : a.index === 99 ? "anti" : "regular");
    const bk = b.kind ?? (b.index === 1 ? "hero" : b.index === 99 ? "anti" : "regular");
    if (ak === "anti" && bk !== "anti") return 1;
    if (bk === "anti" && ak !== "anti") return -1;
    return a.index - b.index;
  });

  const hero = sorted.filter((r) => (r.kind ?? (r.index === 1 ? "hero" : "regular")) === "hero");
  const regular = sorted.filter((r) => {
    const k = r.kind ?? (r.index === 1 ? "hero" : r.index === 99 ? "anti" : "regular");
    return k === "regular";
  });
  const anti = sorted.filter((r) => (r.kind ?? (r.index === 99 ? "anti" : "regular")) === "anti");

  return (
    <div className="mt-2">
      {hero.map((rec) => (
        <NumberedRecommendation key={rec.index} recommendation={rec} variant="hero" />
      ))}
      {regular.map((rec) => (
        <NumberedRecommendation key={rec.index} recommendation={rec} variant="default" />
      ))}
      {anti.length > 0 ? (
        <>
          <p className="mt-4 mb-1 text-[11px] font-semibold gv-kicker tracking-[0.12em] text-[color:var(--gv-neg-deep)]">
            Ngừng làm
          </p>
          {anti.map((rec) => (
            <NumberedRecommendation key={rec.index} recommendation={rec} variant="anti" />
          ))}
        </>
      ) : null}
    </div>
  );
}
