/**
 * Phase C.6 — Diagnostic report body (URL-less flop diagnosis).
 *
 * Serves the ``own_flop_no_url`` intent. Reference design is Claude
 * Chat's Report 4 (VIDEO DIAGNOSIS) but scoped down: no numeric score
 * because we don't have the video itself — a 4-level verdict enum per
 * fixed category instead.
 *
 * Render order:
 *   ConfidenceStrip → HumilityBanner (thin) → Framing → CategoryList
 *                   → PrescriptionCards (if any) → PasteLinkCTA
 *
 * Per the PRD: ``ScoreRing`` / per-section numeric score are
 * intentionally NOT ported — that accuracy is not honest here.
 */

import { useNavigate } from "react-router";
import { useState } from "react";

import type {
  DiagnosticCategoryData,
  DiagnosticPrescriptionData,
  DiagnosticReportPayload,
  DiagnosticVerdictData,
} from "@/lib/api-types";

import { ConfidenceStrip } from "../pattern/ConfidenceStrip";
import { HumilityBanner } from "../pattern/HumilityBanner";

// ── Verdict badge ───────────────────────────────────────────────────────────

const VERDICT_LABEL_VN: Record<DiagnosticVerdictData, string> = {
  likely_issue: "Nhiều khả năng lỗi",
  possible_issue: "Có thể có lỗi",
  unclear: "Chưa đủ thông tin",
  probably_fine: "Có vẻ ổn",
};

function VerdictBadge({ verdict }: { verdict: DiagnosticVerdictData }) {
  // Token-driven tones — no hex here. Uses the 4 ink/accent/pos/warn
  // scales already defined in ``src/app.css``:
  //   likely_issue   → accent (red, urgent)
  //   possible_issue → warn (amber, worth checking)
  //   unclear        → neutral canvas+ink (no judgement)
  //   probably_fine  → pos (blue, safe)
  const toneClass = {
    likely_issue:
      "border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]",
    possible_issue:
      "border-[color:var(--gv-warn)] bg-[color:var(--gv-warn-soft)] text-[color:var(--gv-warn)]",
    unclear:
      "border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-3)]",
    probably_fine:
      "border-[color:var(--gv-pos)] bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]",
  }[verdict];

  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 gv-mono text-[10px] uppercase tracking-wide ${toneClass}`}
      data-verdict={verdict}
    >
      {VERDICT_LABEL_VN[verdict]}
    </span>
  );
}

// ── Category card ───────────────────────────────────────────────────────────

function CategoryCard({
  category,
  rank,
}: {
  category: DiagnosticCategoryData;
  rank: number;
}) {
  return (
    <li className="flex flex-col rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
      <header className="flex flex-wrap items-center gap-2">
        <span className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          #{rank}
        </span>
        <VerdictBadge verdict={category.verdict} />
      </header>
      <p className="gv-serif mt-2 text-[16px] text-[color:var(--gv-ink)]">
        {category.name}
      </p>
      <p className="mt-2 text-sm leading-snug text-[color:var(--gv-ink-2)]">
        {category.finding}
      </p>
      {category.fix_preview ? (
        <p className="mt-3 rounded border-l-2 border-[color:var(--gv-accent)] bg-[color:var(--gv-canvas-2)] px-3 py-2 text-sm leading-snug text-[color:var(--gv-ink-2)]">
          {category.fix_preview}
        </p>
      ) : null}
    </li>
  );
}

// ── Prescription card ──────────────────────────────────────────────────────

const EFFORT_LABEL_VN: Record<DiagnosticPrescriptionData["effort"], string> = {
  low: "15 phút",
  medium: "30 phút",
  high: "1 giờ",
};

function PrescriptionCard({ p }: { p: DiagnosticPrescriptionData }) {
  return (
    <li className="flex flex-col rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
      <header className="flex flex-wrap items-center gap-2">
        <span className="rounded border border-[color:var(--gv-accent)] bg-[color:var(--gv-accent-soft)] px-2 py-0.5 gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent-deep)]">
          {p.priority}
        </span>
        <span className="ml-auto gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          {EFFORT_LABEL_VN[p.effort]}
        </span>
      </header>
      <p className="gv-serif mt-2 text-[16px] text-[color:var(--gv-ink)]">
        {p.action}
      </p>
      <p className="mt-2 rounded bg-[color:var(--gv-canvas-2)] px-3 py-2 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
        {p.impact}
      </p>
    </li>
  );
}

// ── Paste-link CTA (the "get exact diagnosis" upsell) ──────────────────────

function PasteLinkCTA({
  cta,
}: {
  cta: DiagnosticReportPayload["paste_link_cta"];
}) {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => navigate(cta.route)}
      className="w-full rounded-lg border-2 border-[color:var(--gv-accent)] bg-[color:var(--gv-paper)] p-4 text-left transition-colors hover:bg-[color:var(--gv-accent-soft)]"
    >
      <p className="gv-mono text-[10px] uppercase tracking-wide text-[color:var(--gv-accent-deep)]">
        Chẩn đoán chính xác
      </p>
      <p className="gv-serif mt-1 text-[18px] leading-snug text-[color:var(--gv-ink)]">
        {cta.title}
      </p>
    </button>
  );
}

// ── Main body ──────────────────────────────────────────────────────────────

export function DiagnosticBody({ report }: { report: DiagnosticReportPayload }) {
  const thin = report.confidence.sample_size < 80;
  const [humilityOpen, setHumilityOpen] = useState(true);

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
          Chẩn đoán URL-less
        </p>
        <h3 className="gv-serif mb-2 text-[20px] leading-tight text-[color:var(--gv-ink)]">
          5 hạng mục — không có link video
        </h3>
        <p className="text-[15px] leading-snug text-[color:var(--gv-ink-2)]">
          {report.framing}
        </p>
      </section>

      <section>
        <p className="gv-mono mb-3 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
          Hạng mục ({report.categories.length})
        </p>
        <ul className="grid grid-cols-1 gap-3 min-[900px]:grid-cols-2">
          {report.categories.map((category, i) => (
            <CategoryCard
              key={category.name}
              category={category}
              rank={i + 1}
            />
          ))}
        </ul>
      </section>

      {report.prescriptions.length > 0 ? (
        <section>
          <p className="gv-mono mb-1 text-[10px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
            Ưu tiên sửa
          </p>
          <h3 className="gv-serif mb-3 text-[18px] text-[color:var(--gv-ink)]">
            Thử theo thứ tự này
          </h3>
          <ul className="grid grid-cols-1 gap-3 min-[900px]:grid-cols-3">
            {report.prescriptions.map((p) => (
              <PrescriptionCard key={`${p.priority}-${p.action}`} p={p} />
            ))}
          </ul>
        </section>
      ) : null}

      <PasteLinkCTA cta={report.paste_link_cta} />
    </div>
  );
}
