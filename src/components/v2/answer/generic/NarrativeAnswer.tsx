/**
 * Phase C.5.2 — NarrativeAnswer (plan §2.4 section 3).
 *
 * Kicker `TRẢ LỜI` + 1–2 serif paragraphs. Copy comes from the backend
 * `narrative.paragraphs[]` (Gemini bounded + 320-char cap per paragraph,
 * enforced server-side by `cap_paragraphs`). Renders blank safely when
 * the array is empty — OffTaxonomyBanner still ships on its own.
 */

import type { GenericReportPayload } from "@/lib/api-types";

export function NarrativeAnswer({
  data,
}: {
  data: GenericReportPayload["narrative"];
}) {
  const paragraphs = (data as { paragraphs?: string[] } | undefined)?.paragraphs ?? [];
  if (paragraphs.length === 0) return null;
  return (
    <section className="rounded border border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] px-[22px] py-5">
      <p className="gv-mono mb-2 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        Trả lời
      </p>
      <div className="flex flex-col gap-3">
        {paragraphs.map((p, i) => (
          <p
            key={i}
            className="gv-serif max-w-[680px] text-[20px] leading-[1.45] text-[color:var(--gv-ink)] tracking-tight"
          >
            {p}
          </p>
        ))}
      </div>
    </section>
  );
}
