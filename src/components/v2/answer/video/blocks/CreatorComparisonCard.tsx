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
