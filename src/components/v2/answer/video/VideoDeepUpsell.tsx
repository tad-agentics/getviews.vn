import { Lock } from "lucide-react";

import type { LockedSectionTeaser } from "@/lib/videoDeepUpsell";

/** §4.11.3 — locked-section teasers only; deep upgrade CTA lives in IntentCtaRail (W5-1). */
export function VideoDeepUpsell({ lockedSections }: { lockedSections: LockedSectionTeaser[] }) {
  if (lockedSections.length === 0) return null;

  return (
    <section className="mt-8" aria-label="Mục khóa trong bản chuyên sâu">
      <p className="gv-mono mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-ink-4)]">
        Còn thêm trong bản chuyên sâu
      </p>
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {lockedSections.map((sec) => (
          <li key={sec.section_id}>
            <span className="inline-flex min-h-[44px] items-center gap-1.5 rounded-full border border-dashed border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-3 py-2 text-[13px] text-[color:var(--gv-ink-3)]">
              <Lock className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} aria-hidden />
              {sec.title_vi}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
