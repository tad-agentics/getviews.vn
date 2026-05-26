/**
 * Pattern report body — locked render order (Phase C.2.3).
 * Thin sample (&lt;30): first finding only, no WhatStalled, 3 evidence tiles, humility UX.
 */
import type { ReactNode } from "react";
import type { OutlierStory, PatternABPair, PatternReportPayload, SumStatData } from "@/lib/api-types";
import { EvidenceGrid } from "./EvidenceGrid";
import { HookFindingCard } from "./HookFindingCard";
import { PatternActionCards } from "./PatternActionCards";
import { PatternCellGrid } from "./PatternCellGrid";
import { WhatStalledCard } from "./WhatStalledCard";
import { WhatStalledRow } from "./WhatStalledRow";
import { WoWDiffBand } from "./WoWDiffBand";
import { tiktokVideoHref, wowDiffHasContent } from "./patternFormat";
import { PatternSubreports } from "../multi/PatternSubreport";
import { NicheInsightCard } from "../ideas/NicheInsightCard";
import { formatViews } from "@/lib/formatters";
import { patternLabelsForSessionIntent } from "../sessionIntentLabels";

function sumToneClass(tone: SumStatData["tone"]): string {
  if (tone === "up") return "text-[color:var(--gv-pos)]";
  if (tone === "down") return "text-[color:var(--gv-neg)]";
  return "text-[color:var(--gv-ink-3)]";
}

function OutlierStoryBanner({ story }: { story: OutlierStory }) {
  return (
    <div className="mb-6 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-3.5">
      <p className="gv-mono mb-1 text-[11px] gv-kicker tracking-widest text-[color:var(--gv-ink-3)]">
        Đỉnh cao tuần này
      </p>
      <p className="text-[17px] leading-snug text-[color:var(--gv-ink)]">
        <span className="font-semibold">{story.creator_handle}</span> đạt{" "}
        <span className="font-mono font-bold text-[color:var(--gv-accent)]">
          {formatViews(story.views)} lượt xem
        </span>{" "}
        — gấp{" "}
        <span className="font-mono font-bold">
          {story.breakout_ratio.toLocaleString("vi-VN")}×
        </span>{" "}
        mức trung bình creator · hook <span className="font-semibold">{story.hook_type}</span>
        {story.days_ago != null && story.days_ago <= 7 && (
          <span className="text-[color:var(--gv-ink-3)]">
            {" "}
            · {story.days_ago === 0 ? "hôm nay" : `${story.days_ago} ngày trước`}
          </span>
        )}
      </p>
    </div>
  );
}

function AbPairSide({ href, children }: { href: string | null; children: ReactNode }) {
  const cls = "block p-4 no-underline";
  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>
        {children}
      </a>
    );
  }
  return <div className={cls}>{children}</div>;
}

function ABPairStrip({ pair }: { pair: PatternABPair }) {
  const fmt = (v: number) =>
    v >= 1_000_000
      ? `${(v / 1_000_000).toFixed(1)}M`
      : v >= 1_000
        ? `${Math.round(v / 1_000)}K`
        : v.toLocaleString("vi-VN");

  return (
    <div className="mb-6 overflow-hidden rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      <div className="border-b border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-2.5">
        <span className="gv-kickerst text-[color:var(--gv-ink-4)]">
          A/B cùng creator · {pair.creator_handle}
        </span>
        <span className="gv-mono ml-2 text-[11px] text-[color:var(--gv-ink-3)]">{pair.hook_contrast}</span>
      </div>
      <div className="grid grid-cols-2 divide-x divide-[color:var(--gv-rule)]">
        <AbPairSide
          href={tiktokVideoHref({
            video_id: pair.hit.video_id,
            creator_handle: pair.creator_handle,
            tiktok_url: pair.hit.tiktok_url,
          })}
        >
          <p className="gv-mono mb-1 text-[11px] gv-kicker text-[color:var(--gv-pos)]">Hook thắng</p>
          <p className="gv-mono text-[22px] font-bold leading-none text-[color:var(--gv-ink)]">
            {fmt(pair.hit.views)}
          </p>
          <p className="mt-1 text-[11px] text-[color:var(--gv-ink-3)]">{pair.hit.hook_type}</p>
        </AbPairSide>
        <AbPairSide
          href={tiktokVideoHref({
            video_id: pair.flop.video_id,
            creator_handle: pair.creator_handle,
            tiktok_url: pair.flop.tiktok_url,
          })}
        >
          <p className="gv-mono mb-1 text-[11px] gv-kicker text-[color:var(--gv-ink-3)]">Hook thua</p>
          <p className="gv-mono text-[22px] font-bold leading-none text-[color:var(--gv-ink-3)]">
            {fmt(pair.flop.views)}
          </p>
          <p className="mt-1 text-[11px] text-[color:var(--gv-ink-3)]">{pair.flop.hook_type}</p>
        </AbPairSide>
      </div>
      <div className="border-t border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-2">
        <p className="text-[12px] text-[color:var(--gv-ink-2)]">
          Hook thắng vượt hook thua{" "}
          <span className="font-mono font-bold text-[color:var(--gv-ink)]">{pair.delta}×</span> — cùng creator,
          cùng mảng nội dung, khác hook.
        </p>
      </div>
    </div>
  );
}

function CrossPatternSynthesis({ items }: { items: string[] }) {
  const visible = items.map((s) => s.trim()).filter(Boolean);
  if (!visible.length) return null;
  return (
    <div className="mt-8 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-4">
      <p className="gv-mono mb-3 text-[11px] gv-kicker tracking-widest text-[color:var(--gv-ink-3)]">
        Tóm lại tuần này
      </p>
      <ul className="space-y-2.5">
        {visible.map((theme, i) => (
          <li
            key={`${i}-${theme.slice(0, 24)}`}
            className="flex items-start gap-2.5 text-sm leading-snug text-[color:var(--gv-ink-2)]"
          >
            <span
              className="mt-0.5 shrink-0 gv-kicker text-[color:var(--gv-accent)]"
              aria-hidden
            >
              →
            </span>
            <span>{theme}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PatternBody({
  report,
  sessionIntentType,
}: {
  report: PatternReportPayload;
  /** Phiên trả lời — định hướng copy khi cùng `format: pattern`. */
  sessionIntentType?: string;
}) {
  const thin = report.confidence.sample_size < 30;

  const labels = patternLabelsForSessionIntent(sessionIntentType);

  const findings = thin ? report.findings.slice(0, 1) : report.findings;
  const evidence = thin ? report.evidence_videos.slice(0, 3) : report.evidence_videos;
  const wow = report.wow_diff;
  const showWow = wowDiffHasContent(wow);
  const n = report.confidence.sample_size;
  const crossThemes = report.cross_pattern_synthesis ?? [];
  const showCrossSynthesis = crossThemes.some((s) => String(s).trim() !== "");

  return (
    <div className="space-y-8 text-sm text-[color:var(--gv-ink-2)]">
      {(report.outlier_story || report.ab_pair) && (
        <section className="gv-fade-up" style={{ animationDelay: "60ms" }}>
          {report.outlier_story ? <OutlierStoryBanner story={report.outlier_story} /> : null}
          {report.ab_pair ? <ABPairStrip pair={report.ab_pair} /> : null}
        </section>
      )}

      {showWow && wow ? <WoWDiffBand data={wow} /> : null}

      {/* S5/A1 — answer block stagger (per design pack ``screens/answer.jsx``
          lines 287-289). Each section fades up on mount with a cascading
          animation-delay so the report unfolds rather than dropping in
          all at once. ``gv-fade-up`` is defined in ``src/app.css`` and
          respects ``prefers-reduced-motion``. */}
      <section className="gv-fade-up" style={{ animationDelay: "0ms" }}>
        <p className="gv-mono mb-2 text-[11px] tracking-wide text-[color:var(--gv-danger)]">
          {labels.tldrKicker}
        </p>
        <h3 className="gv-serif mb-1 text-[22px] leading-snug text-[color:var(--gv-ink)]">
          {labels.tldrTitle}
        </h3>
        <p className="mt-2 text-[17px] leading-relaxed text-[color:var(--gv-ink-2)]">{report.tldr.thesis}</p>
        {report.tldr.callouts && report.tldr.callouts.length > 0 ? (
          <div className="mt-6 grid grid-cols-1 gap-4 border-y border-[color:var(--gv-ink)] py-6 sm:grid-cols-3">
            {report.tldr.callouts.map((c) => (
              <div key={c.label} className="text-center">
                <p className="gv-kicker text-[color:var(--gv-ink-3)]">{c.label}</p>
                <p className="gv-serif mt-1 text-[22px] text-[color:var(--gv-ink)]">{c.value}</p>
                <p className={`gv-mono mt-1 text-[11px] ${sumToneClass(c.tone)}`}>
                  {c.tone === "up" ? "↑ " : c.tone === "down" ? "↓ " : ""}
                  {c.trend}
                </p>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      {findings.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "180ms" }}>
          <p className="gv-mono mb-1 text-[11px] tracking-wide text-[color:var(--gv-danger)]">
            {labels.findingsKicker}
          </p>
          <h3 className="gv-serif mb-4 text-[17px] text-[color:var(--gv-ink)]">{labels.findingsTitle}</h3>
          <div className="flex flex-col gap-4">
            {findings.map((row) => (
              <HookFindingCard
                key={`${row.rank}-${row.pattern}`}
                row={row}
                evidenceVideos={evidence}
              />
            ))}
          </div>
        </section>
      ) : null}

      {!thin ? (
        <section className="gv-fade-up" style={{ animationDelay: "240ms" }}>
          <p className="gv-mono mb-1 text-[11px] tracking-wide text-[color:var(--gv-danger)]">
            {labels.stalledKicker}
          </p>
          <h3 className="gv-serif mb-4 text-[17px] text-[color:var(--gv-ink)]">{labels.stalledTitle}</h3>
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
        <section className="gv-fade-up" style={{ animationDelay: "300ms" }}>
          <p className="gv-mono mb-1 text-[11px] tracking-wide text-[color:var(--gv-ink-3)]">
            {labels.evidenceKicker}
          </p>
          <h3 className="gv-serif mb-4 text-[17px] text-[color:var(--gv-ink)]">
            {labels.evidenceTitleForCount(evidence.length)}
          </h3>
          <EvidenceGrid items={evidence} />
        </section>
      ) : null}

      {showCrossSynthesis ? (
        <section className="gv-fade-up" style={{ animationDelay: "330ms" }}>
          <CrossPatternSynthesis items={crossThemes} />
        </section>
      ) : null}

      {report.patterns.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "360ms" }}>
          <p className="gv-mono mb-1 text-[11px] tracking-wide text-[color:var(--gv-ink-3)]">
            {labels.patternsKicker}
          </p>
          <h3 className="gv-serif mb-4 text-[17px] text-[color:var(--gv-ink)]">
            {labels.patternsTitleForSample(n)}
          </h3>
          <PatternCellGrid cells={report.patterns} />
        </section>
      ) : null}

      <PatternSubreports report={report} />

      <section className="gv-fade-up" style={{ animationDelay: "390ms" }}>
        <NicheInsightCard insight={report.niche_insight} />
      </section>

      {report.actions.length > 0 ? (
        <section className="gv-fade-up" style={{ animationDelay: "420ms" }}>
          <p className="gv-mono mb-1 text-[11px] tracking-wide text-[color:var(--gv-ink-3)]">
            {labels.actionsKicker}
          </p>
          <h3 className="gv-serif mb-4 text-[17px] text-[color:var(--gv-ink)]">{labels.actionsTitle}</h3>
          <PatternActionCards actions={report.actions} />
        </section>
      ) : null}
    </div>
  );
}
