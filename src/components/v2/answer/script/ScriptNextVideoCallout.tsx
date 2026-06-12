import { useId } from "react";
import { ScriptNarrativeProse } from "./ScriptNarrativeProse";

export function ScriptNextVideoCallout({ text }: { text: string }) {
  const trimmed = text.trim();
  const kickerId = useId();
  if (!trimmed) return null;

  return (
    <section
      aria-labelledby={kickerId}
      className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-accent)]/35 bg-[color:var(--gv-accent-soft)] px-4 py-3.5"
    >
      <p
        id={kickerId}
        className="gv-mono m-0 mb-2 text-[11px] font-semibold gv-kicker tracking-[0.12em] text-[color:var(--gv-accent-deep)]"
      >
        Video tiếp theo nên quay
      </p>
      <ScriptNarrativeProse text={trimmed} className="mt-0 space-y-2" />
    </section>
  );
}
