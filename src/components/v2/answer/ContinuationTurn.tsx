/**
 * Phase C.1.3 — dispatch answer turn body by `turn.kind` + §J `payload.kind`.
 * Stubs: non-primary turn kinds until C.3 / C.4 / C.8 wire dedicated renderers.
 */
import type { AnswerTurnRow, ReportV1 } from "@/lib/api-types";
import { PatternBody } from "@/components/v2/answer/pattern/PatternBody";
import { IdeasBody } from "@/components/v2/answer/ideas/IdeasBody";
import { TimingBody } from "@/components/v2/answer/timing/TimingBody";
import { GenericBody } from "@/components/v2/answer/generic/GenericBody";
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
        <AnswerBlock kicker="Ideas">
          <IdeasBody report={payload.report} />
        </AnswerBlock>
      );
    case "timing":
      return (
        <AnswerBlock kicker="Timing">
          <TimingBody report={payload.report} />
        </AnswerBlock>
      );
    case "generic":
      return (
        <AnswerBlock kicker="Tổng quát">
          <GenericBody report={payload.report} />
        </AnswerBlock>
      );
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
