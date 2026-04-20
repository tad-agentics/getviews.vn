/**
 * Phase C.1.3 — dispatch answer turn body by `turn.kind` + §J `payload.kind`.
 * Stubs: non-primary turn kinds until C.3 / C.4 / C.8 wire dedicated renderers.
 */
import type { AnswerTurnRow, ReportV1 } from "@/lib/api-types";
import { PatternBody } from "@/components/v2/answer/pattern/PatternBody";
import { AnswerBlock } from "@/components/v2/answer/AnswerBlock";

function TurnDivider({ turn }: { turn: Pick<AnswerTurnRow, "turn_index" | "kind" | "query"> }) {
  const extra = turn.kind !== "primary" ? ` · ${turn.kind}` : "";
  return (
    <header className="mb-3 space-y-1">
      <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        Lượt {turn.turn_index + 1}
        {extra}
      </p>
      <p className="text-xs leading-snug text-[color:var(--gv-ink-3)]">{turn.query}</p>
    </header>
  );
}

function ReportPayloadBody({ payload }: { payload: ReportV1 }) {
  switch (payload.kind) {
    case "pattern":
      return (
        <AnswerBlock kicker="Pattern">
          <PatternBody report={payload.report} />
        </AnswerBlock>
      );
    case "ideas":
      return (
        <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
            Ideas
          </p>
          <p className="mt-4 text-sm text-[color:var(--gv-ink-2)]">{payload.report.lead}</p>
        </div>
      );
    case "timing": {
      const tw = payload.report.top_window as Record<string, unknown>;
      const label = [tw.day, tw.hours].filter(Boolean).join(" · ");
      return (
        <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
            Timing
          </p>
          <p className="mt-4 text-sm text-[color:var(--gv-ink-2)]">{label || "Khung giờ gợi ý"}</p>
        </div>
      );
    }
    case "generic": {
      const paras = (payload.report.narrative as { paragraphs?: string[] } | undefined)?.paragraphs;
      const text =
        Array.isArray(paras) && paras.length > 0
          ? paras.join("\n\n")
          : "Báo cáo tổng quát (generic).";
      return (
        <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
          <p className="font-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent)]">
            Tổng quát
          </p>
          <p className="mt-4 whitespace-pre-wrap text-sm text-[color:var(--gv-ink-2)]">{text}</p>
        </div>
      );
    }
  }
}

export function ContinuationTurn({ turn }: { turn: AnswerTurnRow }) {
  return (
    <article className="min-w-0">
      <TurnDivider turn={turn} />
      <ReportPayloadBody payload={turn.payload} />
    </article>
  );
}
