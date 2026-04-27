/**
 * S5 — FormattedVO renders a single VO line, splitting on ``*stress*``
 * markers so the wrapped span gets a tinted accent-soft background +
 * bold weight (per design pack ``screens/script.jsx`` lines 1234-1250).
 *
 * The marker syntax is the simplest thing that survives JSON: anything
 * between two single asterisks. Markers may NOT cross line boundaries —
 * per VO line, parse independently. Empty markers (``**``) are dropped
 * silently rather than rendered as an empty span.
 */

const MARKER_RE = /(\*[^*\n]+\*)/g;

export function FormattedVO({ text }: { text: string }) {
  if (!text) return null;
  const parts = text.split(MARKER_RE);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("*") && part.endsWith("*") && part.length >= 3) {
          return (
            <strong
              key={i}
              className="font-bold rounded-[2px] px-[2px] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-ink)]"
            >
              {part.slice(1, -1)}
            </strong>
          );
        }
        // Stray asterisks (e.g. unmatched) render literally.
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
