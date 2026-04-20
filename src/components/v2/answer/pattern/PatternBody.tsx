/**
 * Pattern report body — locked render order (Phase C.2.3).
 */
import type { PatternReportPayload } from "@/lib/api-types";
import { ConfidenceStrip } from "./ConfidenceStrip";
import { WhatStalledRow } from "./WhatStalledRow";

export function PatternBody({ report }: { report: PatternReportPayload }) {
  const ws = report.what_stalled;
  const reason = report.confidence.what_stalled_reason;

  return (
    <div className="space-y-6 text-sm text-[color:var(--gv-ink-2)]">
      <ConfidenceStrip data={report.confidence} />

      <section>
        <p className="gv-mono mb-2 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          Tóm tắt
        </p>
        <p className="gv-serif text-lg leading-snug text-[color:var(--gv-ink)]">{report.tldr.thesis}</p>
      </section>

      <section>
        <p className="gv-mono mb-2 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          What stalled
        </p>
        {ws.length === 0 ? (
          <WhatStalledRow empty reason={reason} />
        ) : (
          <ul className="space-y-2">
            {ws.map((h) => (
              <li
                key={h.rank + h.pattern}
                className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2"
              >
                <span className="font-mono text-[10px] text-[color:var(--gv-accent)]">#{h.rank}</span>{" "}
                {h.pattern}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
