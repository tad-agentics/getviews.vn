import type { ScriptReportPayload } from "@/lib/api-types";
import { scriptVerdictForDisplay } from "@/lib/scriptVerdictProse";
import { ScriptNarrativeProse } from "./ScriptNarrativeProse";

export function ScriptAnswerHeader({
  report,
  hasCorpusStrip = false,
}: {
  report: ScriptReportPayload;
  hasCorpusStrip?: boolean;
}) {
  const narrative = report.narrative_vi;
  const headline = narrative?.headline_vi?.trim() || report.hook;
  const meta = [report.niche_label?.trim(), `${report.duration}s`, report.tone].filter(Boolean);
  const verdict = narrative?.ket_luan_nhanh
    ? scriptVerdictForDisplay(narrative.ket_luan_nhanh, hasCorpusStrip)
    : null;

  return (
    <header className="space-y-3">
      <p className="gv-kicker m-0 text-[color:var(--gv-ink-3)]">
        Kịch bản · {meta.join(" · ")}
      </p>
      <h2
        className="gv-tight m-0 text-[clamp(1.125rem,2.5vi+0.35rem,1.65rem)] font-medium leading-tight text-[color:var(--gv-ink)]"
        style={{ fontFamily: "var(--gv-font-display)", textWrap: "balance" }}
      >
        {headline}
      </h2>
      {verdict ? <ScriptNarrativeProse text={verdict} className="mt-0" /> : null}
      <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink-3)]">
        <span className="font-medium text-[color:var(--gv-ink-2)]">Chủ đề:</span> {report.topic}
      </p>
      <p className="gv-mono m-0 text-[11px] text-[color:var(--gv-ink-3)]">
        Hook xuất hiện sau ~{Math.round(report.hook_delay_ms / 100) / 10}s
      </p>
    </header>
  );
}
