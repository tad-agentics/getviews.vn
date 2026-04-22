/**
 * Phase C.1.3 — dispatch answer turn body by `turn.kind` + §J `payload.kind`.
 * Stubs: non-primary turn kinds until C.3 / C.4 / C.8 wire dedicated renderers.
 */
import type { AnswerTurnRow, ReportV1 } from "@/lib/api-types";
import { PatternBody } from "@/components/v2/answer/pattern/PatternBody";
import { IdeasBody } from "@/components/v2/answer/ideas/IdeasBody";
import { TimingBody } from "@/components/v2/answer/timing/TimingBody";
import { LifecycleBody } from "@/components/v2/answer/lifecycle/LifecycleBody";
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
    case "lifecycle":
      return (
        <AnswerBlock kicker="Lifecycle">
          <LifecycleBody report={payload.report} />
        </AnswerBlock>
      );
    case "generic":
      return (
        <AnswerBlock kicker="Tổng quát">
          <GenericBody report={payload.report} />
        </AnswerBlock>
      );
    default:
      // D-era diagnostic: surface the payload shape instead of rendering
      // nothing. Previously unknown `kind` values (or missing `kind`)
      // produced a silent blank turn — which made "no report produced"
      // indistinguishable from stream failure. Now the envelope shows.
      return <UnknownPayloadSurface payload={payload} />;
  }
}

function UnknownPayloadSurface({ payload }: { payload: unknown }) {
  if (typeof console !== "undefined") {
    console.error("[answer/turn] unknown payload.kind", payload);
  }
  let body = "";
  try {
    body = JSON.stringify(payload, null, 2).slice(0, 800);
  } catch {
    body = String(payload).slice(0, 800);
  }
  return (
    <AnswerBlock kicker="Báo cáo lỗi định dạng">
      <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
        <p className="gv-serif text-[16px] leading-snug text-[color:var(--gv-ink)]">
          Phiên đã được lưu nhưng định dạng báo cáo không nhận diện được.
        </p>
        <p className="mt-2 gv-mono text-[11px] leading-relaxed text-[color:var(--gv-ink-3)]">
          Thử làm mới hoặc mở phiên mới. Nếu tiếp diễn, gửi đoạn bên dưới cho
          team để chẩn đoán nhanh hơn.
        </p>
        <pre className="mt-3 max-h-64 overflow-auto rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-3 gv-mono text-[10px] text-[color:var(--gv-ink-3)]">
          {body}
        </pre>
      </div>
    </AnswerBlock>
  );
}

export function ContinuationTurn({ turn }: { turn: AnswerTurnRow }) {
  return (
    <article className="min-w-0">
      <TurnDivider turn={turn} />
      <ReportPayloadBody payload={turn.payload} />
    </article>
  );
}
