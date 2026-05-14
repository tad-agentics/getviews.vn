/**
 * ProvenanceLine — a small attribution line below the narrative.
 * Shows data source, scrape time, and whether the result is cached.
 */

interface ProvenanceLineProps {
  provenance: string;
  cacheHit?: boolean;
}

export function ProvenanceLine({ provenance, cacheHit }: ProvenanceLineProps) {
  return (
    <p className="text-[10px] text-[color:var(--muted)] mt-4 mb-2 italic">
      {provenance}
      {cacheHit && (
        <span className="ml-2 not-italic font-medium text-[color:var(--muted)] opacity-70">
          · Từ cache
        </span>
      )}
    </p>
  );
}
