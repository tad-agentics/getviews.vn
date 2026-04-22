/**
 * Phase C.5 — Lifecycle report body.
 *
 * Serves ``format_lifecycle_optimize`` / ``fatigue`` / ``subniche_breakdown``
 * intents (QA audit 2026-04-22). ``mode`` discriminator drives:
 *   - header kicker + copy (format: "Chu trình format"; hook_fatigue: "Hook
 *     fatigue"; subniche: "Ngách con")
 *   - which supplementary cell field shows (retention_pct in format mode,
 *     instance_count in subniche mode, neither in hook_fatigue).
 *
 * Render order mirrors Timing/Pattern so visual rhythm is consistent:
 *   ConfidenceStrip → HumilityBanner (thin) → SubjectLine → CellGrid
 *                   → RefreshMoves (optional) → ActionCards
 *
 * Refresh moves never render when the list is empty — the Pydantic
 * invariant on the backend guarantees non-empty only when at least one
 * cell is declining/plateau, but double-check here defensively.
 */

import { useState } from "react";

import type {
  LifecycleCellData,
  LifecycleModeData,
  LifecycleReportPayload,
  LifecycleStageData,
  RefreshMoveData,
} from "@/lib/api-types";
import { ConfidenceStrip } from "../pattern/ConfidenceStrip";
import { HumilityBanner } from "../pattern/HumilityBanner";
import { TimingActionCards } from "../timing/TimingActionCards";

// ── Mode header copy ────────────────────────────────────────────────────────

const MODE_HEADERS: Record<
  LifecycleModeData,
  { kicker: string; title: string }
> = {
  format: {
    kicker: "Chu trình format",
    title: "Format nào đang lên, format nào đang chững",
  },
  hook_fatigue: {
    kicker: "Hook fatigue",
    title: "Hook này còn dùng được không",
  },
  subniche: {
    kicker: "Ngách con",
    title: "Ngách con đang lên trong ngách lớn",
  },
};

// ── Stage pill styling ──────────────────────────────────────────────────────

const STAGE_PILL_VN: Record<LifecycleStageData, string> = {
  rising: "Đang lên",
  peak: "Đỉnh",
  plateau: "Chững",
  declining: "Giảm",
};

function StagePill({ stage }: { stage: LifecycleStageData }) {
  // Token-driven — no hex here. Reuses the tone tokens already in use by
  // pattern/timing variance chips (``--gv-pos-*``, ``--gv-accent-*``,
  // ``--gv-warn-*``). No ``--gv-warn-deep`` in the palette, so declining
  // uses ``--gv-warn`` directly for text.
  const toneClass = {
    rising: "border-[color:var(--gv-pos)] bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]",
    peak: "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]",
    plateau: "border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]",
    declining: "border-[color:var(--gv-warn)] bg-[color:var(--gv-warn-soft)] text-[color:var(--gv-warn)]",
  }[stage];
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 gv-mono text-[10px] uppercase tracking-wide ${toneClass}`}
    >
      {STAGE_PILL_VN[stage]}
    </span>
  );
}

// ── Cell card ───────────────────────────────────────────────────────────────

function LifecycleCellCard({
  cell,
  mode,
  rank,
}: {
  cell: LifecycleCellData;
  mode: LifecycleModeData;
  rank: number;
}) {
  const delta = cell.reach_delta_pct;
  const sign = delta >= 0 ? "+" : "";
  const deltaClass =
    delta > 0
      ? "text-[color:var(--gv-pos-deep)]"
      : delta < 0
        ? "text-[color:var(--gv-warn)]"
        : "text-[color:var(--gv-ink-3)]";

  // Supplementary row: retention_pct for format mode, instance_count for
  // subniche mode. Never render the row when the field is null.
  let suppLine: string | null = null;
  if (mode === "format" && cell.retention_pct != null) {
    suppLine = `Retention ${Math.round(cell.retention_pct)}%`;
  } else if (mode === "subniche" && cell.instance_count != null) {
    suppLine = `${cell.instance_count.toLocaleString("vi-VN")} creator đang làm`;
  }

  return (
    <li className="flex flex-col rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
      <header className="flex flex-wrap items-center gap-2">
        <span className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          #{rank}
        </span>
        <StagePill stage={cell.stage} />
        <span className={`ml-auto gv-mono text-[12px] font-medium ${deltaClass}`}>
          {sign}
          {Math.round(delta)}%
        </span>
      </header>
      <p className="gv-serif mt-2 text-[16px] text-[color:var(--gv-ink)]">
        {cell.name}
      </p>
      <div className="mt-2 flex flex-wrap gap-3 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
        <span>Health {cell.health_score}/100</span>
        {suppLine ? <span>·</span> : null}
        {suppLine ? <span>{suppLine}</span> : null}
      </div>
      <p className="mt-3 text-sm leading-snug text-[color:var(--gv-ink-2)]">
        {cell.insight}
      </p>
    </li>
  );
}

// ── Refresh moves list ─────────────────────────────────────────────────────

const EFFORT_LABEL_VN: Record<RefreshMoveData["effort"], string> = {
  low: "Công sức thấp",
  medium: "Công sức vừa",
  high: "Công sức cao",
};

function RefreshMovesList({ moves }: { moves: RefreshMoveData[] }) {
  if (moves.length === 0) return null;
  return (
    <section>
      <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        Refresh
      </p>
      <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
        Cách làm mới cell đang yếu
      </h3>
      <ul className="space-y-2">
        {moves.map((m) => (
          <li
            key={m.title}
            className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4"
          >
            <header className="flex flex-wrap items-center justify-between gap-2">
              <p className="gv-serif text-[15px] text-[color:var(--gv-ink)]">
                {m.title}
              </p>
              <span className="rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-0.5 gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-3)]">
                {EFFORT_LABEL_VN[m.effort]}
              </span>
            </header>
            <p className="mt-2 text-sm leading-snug text-[color:var(--gv-ink-2)]">
              {m.detail}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ── Main body ──────────────────────────────────────────────────────────────

export function LifecycleBody({ report }: { report: LifecycleReportPayload }) {
  const thin = report.confidence.sample_size < 80;
  const [humilityOpen, setHumilityOpen] = useState(true);
  const header = MODE_HEADERS[report.mode];

  return (
    <div className="space-y-8 text-sm text-[color:var(--gv-ink-2)]">
      <ConfidenceStrip
        data={report.confidence}
        thinSample={thin}
        humilityVisible={humilityOpen}
        onHumilityToggle={() => setHumilityOpen((v) => !v)}
      />

      {thin && humilityOpen ? <HumilityBanner /> : null}

      <section>
        <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          {header.kicker}
        </p>
        <h3 className="gv-serif mb-2 text-[20px] leading-tight text-[color:var(--gv-ink)]">
          {header.title}
        </h3>
        <p className="text-[15px] leading-snug text-[color:var(--gv-ink-2)]">
          {report.subject_line}
        </p>
      </section>

      <section>
        <p className="gv-mono mb-3 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          Xếp hạng ({report.cells.length})
        </p>
        <ul className="grid grid-cols-1 gap-3 min-[900px]:grid-cols-2">
          {report.cells.map((cell, i) => (
            <LifecycleCellCard
              key={`${cell.stage}-${cell.name}`}
              cell={cell}
              mode={report.mode}
              rank={i + 1}
            />
          ))}
        </ul>
      </section>

      <RefreshMovesList moves={report.refresh_moves} />

      {report.actions.length > 0 ? (
        <section>
          <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
            Bước tiếp theo
          </p>
          <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
            Biến chu trình thành hành động
          </h3>
          <TimingActionCards actions={report.actions} />
        </section>
      ) : null}
    </div>
  );
}
