import type { CreatorComparison } from "@/lib/api-types";
import { CreatorComparisonEmbed } from "@/components/diagnosis/CreatorComparisonEmbed";

/** Standalone block when `channel_pattern` v6 section did not emit. */
export function CreatorComparisonCard({ data }: { data: CreatorComparison }) {
  return (
    <div className="mb-6" aria-label="So sánh trong kênh">
      <h3 className="text-base font-bold leading-snug text-[color:var(--foreground)]">
        Video này so với kênh bạn
      </h3>
      <CreatorComparisonEmbed data={data} />
    </div>
  );
}
