import type { CreatorComparison } from "@/lib/api-types";
import { CreatorComparisonEmbed } from "@/components/diagnosis/CreatorComparisonEmbed";

/** Standalone block when `channel_pattern` v6 section did not emit. */
export function CreatorComparisonCard({
  data,
  introProse,
}: {
  data: CreatorComparison;
  introProse?: string;
}) {
  // Runtime payloads can miss hit/flop (thin channel sample) even though the
  // type marks them required — a heading + boilerplate with no comparison
  // cells is worse than nothing (live audit 2026-06-12).
  if (!data?.hit || !data?.flop) return null;
  const intro = introProse?.trim();
  return (
    <div className="mb-6" aria-label="So sánh trong kênh">
      <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">
        Video này so với kênh bạn
      </h3>
      {intro ? (
        <p className="mb-3 mt-2 max-w-[680px] text-[17px] leading-relaxed text-[color:var(--foreground)]">
          {intro}
        </p>
      ) : null}
      <CreatorComparisonEmbed data={data} />
    </div>
  );
}
