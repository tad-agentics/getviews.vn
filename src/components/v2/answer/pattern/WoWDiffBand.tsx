import type { WoWDiffData } from "@/lib/api-types";
import { summarizeWoWDiff } from "./patternFormat";

export function WoWDiffBand({ data }: { data: WoWDiffData }) {
  const line = summarizeWoWDiff(data);
  if (!line) return null;
  return (
    <div
      className="mt-4 rounded-[6px] border border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] px-[14px] py-[10px] text-[13px] leading-snug text-[color:var(--gv-accent-deep)]"
      data-testid="wow-diff-band"
    >
      <span aria-hidden>🆕 </span>
      {line}
    </div>
  );
}
