import { Lock } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import type { LockedSectionTeaser } from "@/lib/videoDeepUpsell";

export function VideoDeepUpsell({
  lockedSections,
  onRequestDeepAnalysis,
}: {
  lockedSections: LockedSectionTeaser[];
  onRequestDeepAnalysis: () => void;
}) {
  return (
    <div className="mt-8 space-y-4" aria-label="Nâng cấp phân tích chuyên sâu">
      {lockedSections.length > 0 ? (
        <section aria-label="Mục khóa trong bản chuyên sâu">
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
      ) : null}

      <div className="sticky bottom-0 z-10 -mx-1 border-t border-[color:var(--gv-rule)] bg-[color:color-mix(in_srgb,var(--gv-canvas)_92%,transparent)] px-1 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur-sm">
        <Btn
          type="button"
          variant="accent"
          size="lg"
          className="w-full"
          onClick={onRequestDeepAnalysis}
        >
          Phân tích chuyên sâu (2 credit)
        </Btn>
      </div>
    </div>
  );
}
