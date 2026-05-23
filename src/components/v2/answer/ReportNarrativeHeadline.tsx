import { reportHeadlineVi, type ReportHeadlineSource } from "@/lib/reportNarrativeHeadline";

/** Serif headline block — parity with video ``narrative_vi.headline_vi`` (W5-2). */
export function ReportNarrativeHeadline({
  source,
  kicker,
}: {
  source: ReportHeadlineSource;
  kicker?: string;
}) {
  const headline = reportHeadlineVi(source);
  if (!headline) return null;
  return (
    <section className="gv-fade-up">
      {kicker ? (
        <p className="gv-mono mb-2 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
          {kicker}
        </p>
      ) : null}
      <h3 className="gv-serif text-[22px] leading-snug text-[color:var(--gv-ink)]">{headline}</h3>
    </section>
  );
}
