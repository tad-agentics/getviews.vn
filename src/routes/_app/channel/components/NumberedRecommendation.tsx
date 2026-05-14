/**
 * NumberedRecommendation — renders a single numbered recommendation item.
 * Bold lead sentence + paragraph body, following the copy-rules pattern
 * of "state the fix → explain the why".
 */

import type { ChannelRecommendation } from "@/lib/api-types";

interface NumberedRecommendationProps {
  recommendation: ChannelRecommendation;
}

export function NumberedRecommendation({ recommendation }: NumberedRecommendationProps) {
  return (
    <div className="flex gap-3 items-start py-3 border-b border-[color:var(--border)] last:border-0">
      {/* Index badge */}
      <span
        className={
          "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center " +
          "text-[11px] font-bold font-mono bg-[color:var(--primary)] " +
          "text-[color:var(--primary-foreground)]"
        }
        aria-hidden
      >
        {recommendation.index}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[color:var(--foreground)] leading-snug">
          {recommendation.title}
        </p>
        {recommendation.body && (
          <p className="text-sm text-[color:var(--muted)] mt-1 leading-relaxed">
            {recommendation.body}
          </p>
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

  return (
    <div className="mt-2">
      {recommendations.map((rec) => (
        <NumberedRecommendation key={rec.index} recommendation={rec} />
      ))}
    </div>
  );
}
