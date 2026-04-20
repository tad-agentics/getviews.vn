/**
 * Phase C.3.2 — Ideas LeadParagraph.
 * Kicker `BRIEF` + title + 2–3 sentence serif body.
 */

export function LeadParagraph({ title, body }: { title: string; body: string }) {
  return (
    <section>
      <p className="gv-mono mb-2 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        Brief
      </p>
      <h3 className="gv-serif mb-3 text-[22px] leading-snug text-[color:var(--gv-ink)]">
        {title}
      </h3>
      <p className="gv-serif max-w-[720px] text-[18px] leading-relaxed text-[color:var(--gv-ink-2)]">
        {body}
      </p>
    </section>
  );
}
