/**
 * Pattern report body — locked render order (Phase C.2.3).
 * Thin sample (&lt;30): first finding only, no WhatStalled, 3 evidence tiles, humility UX.
 */
import { useState } from "react";
import type { PatternReportPayload, SumStatData } from "@/lib/api-types";
import { ConfidenceStrip } from "./ConfidenceStrip";
import { EvidenceGrid } from "./EvidenceGrid";
import { HookFindingCard } from "./HookFindingCard";
import { HumilityBanner } from "./HumilityBanner";
import { PatternActionCards } from "./PatternActionCards";
import { PatternCellGrid } from "./PatternCellGrid";
import { WhatStalledCard } from "./WhatStalledCard";
import { WhatStalledRow } from "./WhatStalledRow";
import { WoWDiffBand } from "./WoWDiffBand";
import { wowDiffHasContent } from "./patternFormat";
import { PatternSubreports } from "../multi/PatternSubreport";

function sumToneClass(tone: SumStatData["tone"]): string {
  if (tone === "up") return "text-[color:var(--gv-pos)]";
  if (tone === "down") return "text-[color:var(--gv-neg)]";
  return "text-[color:var(--gv-ink-3)]";
}

export function PatternBody({ report }: { report: PatternReportPayload }) {
  const thin = report.confidence.sample_size < 30;
  const [humilityOpen, setHumilityOpen] = useState(true);

  const findings = thin ? report.findings.slice(0, 1) : report.findings;
  const evidence = thin ? report.evidence_videos.slice(0, 3) : report.evidence_videos;
  const wow = report.wow_diff;
  const showWow = wowDiffHasContent(wow);
  const n = report.confidence.sample_size;

  return (
    <div className="space-y-8 text-sm text-[color:var(--gv-ink-2)]">
      <ConfidenceStrip
        data={report.confidence}
        thinSample={thin}
        humilityVisible={humilityOpen}
        onHumilityToggle={() => setHumilityOpen((v) => !v)}
      />

      {thin && humilityOpen ? <HumilityBanner /> : null}

      {showWow && wow ? <WoWDiffBand data={wow} /> : null}

      <section>
        <p className="gv-mono mb-2 text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">Tóm tắt</p>
        <h3 className="gv-serif mb-1 text-[22px] leading-snug text-[color:var(--gv-ink)]">Điều bạn nên biết</h3>
        <p className="gv-serif text-[22px] leading-snug text-[color:var(--gv-ink)]">{report.tldr.thesis}</p>
        {report.tldr.callouts && report.tldr.callouts.length > 0 ? (
          <div className="mt-6 grid grid-cols-1 gap-4 border-y border-[color:var(--gv-ink)] py-6 min-[560px]:grid-cols-3">
            {report.tldr.callouts.map((c) => (
              <div key={c.label} className="text-center">
                <p className="gv-mono text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">{c.label}</p>
                <p className="gv-serif mt-1 text-[22px] text-[color:var(--gv-ink)]">{c.value}</p>
                <p className={`gv-mono mt-1 text-[11px] ${sumToneClass(c.tone)}`}>{c.trend}</p>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      {findings.length > 0 ? (
        <section>
          <p className="gv-mono mb-1 text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">Bằng chứng · 3 hook</p>
          <h3 className="gv-serif mb-4 text-[18px] text-[color:var(--gv-ink)]">
            Pattern đang thắng, xếp theo retention
          </h3>
          <div className="flex flex-col gap-4">
            {findings.map((row) => (
              <HookFindingCard key={`${row.rank}-${row.pattern}`} row={row} />
            ))}
          </div>
        </section>
      ) : null}

      {!thin ? (
        <section>
          <p className="gv-mono mb-1 text-[10px] tracking-wide text-[color:var(--gv-danger)]">Đã thử nhưng rơi</p>
          <h3 className="gv-serif mb-4 text-[18px] text-[color:var(--gv-ink)]">Pattern không còn hiệu quả</h3>
          {report.what_stalled.length === 0 ? (
            <WhatStalledRow empty reason={report.confidence.what_stalled_reason} />
          ) : (
            <div className="flex flex-col gap-4">
              {report.what_stalled.map((row) => (
                <WhatStalledCard key={`${row.rank}-${row.pattern}`} row={row} />
              ))}
            </div>
          )}
        </section>
      ) : null}

      {evidence.length > 0 ? (
        <section>
          <p className="gv-mono mb-1 text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">Video mẫu</p>
          <h3 className="gv-serif mb-4 text-[18px] text-[color:var(--gv-ink)]">
            {evidence.length} video dùng pattern này đang lên
          </h3>
          <EvidenceGrid items={evidence} />
        </section>
      ) : null}

      {report.patterns.length > 0 ? (
        <section>
          <p className="gv-mono mb-1 text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">Patterns</p>
          <h3 className="gv-serif mb-4 text-[18px] text-[color:var(--gv-ink)]">
            Điểm chung của {n} video thắng
          </h3>
          <PatternCellGrid cells={report.patterns} />
        </section>
      ) : null}

      <PatternSubreports report={report} />

      {report.actions.length > 0 ? (
        <section>
          <p className="gv-mono mb-1 text-[10px] tracking-wide text-[color:var(--gv-ink-4)]">Bước tiếp theo</p>
          <h3 className="gv-serif mb-4 text-[18px] text-[color:var(--gv-ink)]">Biến insight thành video</h3>
          <PatternActionCards actions={report.actions} />
        </section>
      ) : null}
    </div>
  );
}
