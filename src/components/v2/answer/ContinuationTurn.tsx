/**
 * Phase C.1.3 — dispatch answer turn body by `turn.kind` + §J `payload.kind`.
 * A1 (2026-06-03) — TurnDivider polished per design pack
 * ``screens/thread-turns.jsx`` lines 9-66: accent kicker + serif H2
 * question + per-turn MiniResearch ladder + accent rail node.
 */
import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import type { AnswerTurnRow, ReportV1 } from "@/lib/api-types";
import { PatternBody } from "@/components/v2/answer/pattern/PatternBody";
import { IdeasBody } from "@/components/v2/answer/ideas/IdeasBody";
import { TimingBody } from "@/components/v2/answer/timing/TimingBody";
import { LifecycleBody } from "@/components/v2/answer/lifecycle/LifecycleBody";
import { DiagnosticBody } from "@/components/v2/answer/diagnostic/DiagnosticBody";
import { GenericBody } from "@/components/v2/answer/generic/GenericBody";
import { AnswerBlock } from "@/components/v2/answer/AnswerBlock";
import {
  ideasAnswerBlockKicker,
  patternAnswerBlockKicker,
  timingAnswerBlockKicker,
} from "@/components/v2/answer/sessionIntentLabels";

// Map ``AnswerTurnRow.kind`` → accent kicker copy. Continuation turns
// only — primary turn renders a different header (QueryHeader at the
// page level).
const TURN_KIND_LABEL: Record<string, string> = {
  pattern: "ĐÀO SÂU",
  ideas: "Ý TƯỞNG",
  timing: "THỜI ĐIỂM",
  lifecycle: "VÒNG ĐỜI",
  diagnostic: "CHẨN ĐOÁN",
  generic: "ĐÀO SÂU",
};

function TurnMiniResearch() {
  // Two-step "Dùng lại nguồn → Trả lời" ladder runs on first turn mount.
  // Pure visual flair — by the time we render, the payload is already
  // available; the ladder communicates "we re-used the same sources +
  // produced this answer" rather than masking real latency. Settles to
  // a green completion pill within ~1.1s.
  const [stage, setStage] = useState(0);
  useEffect(() => {
    if (stage >= 2) return;
    const t = window.setTimeout(() => setStage((s) => s + 1), [500, 600][stage]);
    return () => window.clearTimeout(t);
  }, [stage]);
  const done = stage >= 2;
  return (
    <div className="mt-3 flex flex-wrap items-center gap-3">
      <ResearchDot label="Dùng lại nguồn" done={stage >= 1} active={stage === 0} />
      <ResearchDot label="Trả lời" done={stage >= 2} active={stage === 1} />
      {done ? (
        <span className="gv-mono inline-flex items-center gap-1 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[10px] text-[color:var(--gv-ink-3)]">
          <Check className="h-3 w-3 text-[color:var(--gv-pos)]" strokeWidth={2.5} aria-hidden />
          cùng phiên
        </span>
      ) : null}
    </div>
  );
}

function ResearchDot({ label, done, active }: { label: string; done: boolean; active: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={
          "inline-flex h-3 w-3 items-center justify-center rounded-full border " +
          (done
            ? "border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
            : active
              ? "border-[color:var(--gv-rule)] bg-[color:var(--gv-accent-soft)]"
              : "border-[color:var(--gv-rule)] bg-transparent")
        }
        aria-hidden
      >
        {done ? <Check className="h-2 w-2" strokeWidth={3} /> : null}
      </span>
      <span
        className={
          "gv-mono text-[11px] " +
          (done
            ? "text-[color:var(--gv-ink)]"
            : active
              ? "text-[color:var(--gv-ink-2)]"
              : "text-[color:var(--gv-ink-4)]")
        }
      >
        {label}
      </span>
    </span>
  );
}

function TurnDivider({ turn }: { turn: Pick<AnswerTurnRow, "turn_index" | "kind" | "query"> }) {
  const label = TURN_KIND_LABEL[turn.kind] ?? "ĐÀO SÂU";
  return (
    <header className="relative mb-4 mt-10 pt-6">
      {/* A1 — accent rail node (per design pack ``thread-turns.jsx`` lines
          17-23). The TimelineRail outer wraps children in ``pl-6`` (24px)
          and draws its line at ``left-[7px]`` — so a dot at
          ``-left-[17px]`` from the TurnDivider sits exactly on the line.
          Hidden on narrow viewports (rail itself collapses there too via
          TimelineRail's no-rail layout). */}
      <span
        aria-hidden
        className="absolute -left-[17px] top-7 hidden h-2.5 w-2.5 -translate-x-1/2 rounded-full border-2 border-[color:var(--gv-canvas)] bg-[color:var(--gv-accent)] shadow-[0_0_0_1px_var(--gv-ink)] lg:block"
      />
      <div className="mb-2.5 flex items-center gap-3">
        <p className="gv-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--gv-accent)]">
          {label} · LƯỢT {String(turn.turn_index + 1).padStart(2, "0")}
        </p>
        <span className="h-px flex-1 bg-[color:var(--gv-rule)]" aria-hidden />
      </div>
      <h2
        className="gv-tight m-0 text-[clamp(20px,2.4vw,28px)] font-medium leading-tight tracking-[-0.02em] text-[color:var(--gv-ink)]"
        style={{ fontFamily: "var(--gv-font-display)", textWrap: "balance" }}
      >
        {turn.query}
      </h2>
      <TurnMiniResearch />
    </header>
  );
}

function ReportPayloadBody({
  payload,
  sessionIntentType,
}: {
  payload: ReportV1;
  /** Intent phiên (câu đầu) — tinh chỉnh kickers/copy khi trùng `format`. */
  sessionIntentType?: string;
}) {
  // Kicker strings intentionally Vietnamese — matches CLAUDE.md's
  // "primary language for user-facing copy: Vietnamese. No English
  // strings in UI." rule. 2026-05-07 sweep: Pattern/Ideas/Timing/
  // Lifecycle were English holdovers from the pre-VN-first era;
  // unified here for consistency with the already-VN Chẩn đoán +
  // Tổng quát kickers.
  switch (payload.kind) {
    case "pattern":
      return (
        <AnswerBlock kicker={patternAnswerBlockKicker(sessionIntentType)} bare>
          <PatternBody report={payload.report} sessionIntentType={sessionIntentType} />
        </AnswerBlock>
      );
    case "ideas":
      return (
        <AnswerBlock kicker={ideasAnswerBlockKicker(sessionIntentType)}>
          <IdeasBody report={payload.report} sessionIntentType={sessionIntentType} />
        </AnswerBlock>
      );
    case "timing":
      return (
        <AnswerBlock kicker={timingAnswerBlockKicker(sessionIntentType)}>
          <TimingBody report={payload.report} sessionIntentType={sessionIntentType} />
        </AnswerBlock>
      );
    case "lifecycle":
      return (
        <AnswerBlock kicker="Vòng đời">
          <LifecycleBody report={payload.report} />
        </AnswerBlock>
      );
    case "diagnostic":
      return (
        <AnswerBlock kicker="Chẩn đoán">
          <DiagnosticBody report={payload.report} />
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

export function ContinuationTurn({
  turn,
  sessionIntentType,
}: {
  turn: AnswerTurnRow;
  sessionIntentType?: string;
}) {
  return (
    <article className="min-w-0">
      <TurnDivider turn={turn} />
      <ReportPayloadBody payload={turn.payload} sessionIntentType={sessionIntentType} />
    </article>
  );
}
