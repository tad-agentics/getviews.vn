/**
 * Phase C — 6-shot script report inside answer sessions (Studio).
 * Narrative IA (2026-06): verdict header → corpus evidence → next video → shot rail.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

import { useSceneIntelligence } from "@/hooks/useSceneIntelligence";
import type { ScriptFormatProof, ScriptReportPayload } from "@/lib/api-types";
import { allScriptCorpusTiles } from "@/lib/scriptCorpusEvidence";
import { scriptEditorFallbacks } from "@/lib/scriptEditorFallbacks";
import {
  mergeSceneIntelIntoShots,
  reportShotsToEditorShots,
  sceneRowForShot,
} from "@/lib/scriptEditorMerge";
import { scriptNextVideoText } from "@/lib/scriptNarrativeRefs";
import { formatViews } from "@/lib/formatters";

import { ScriptActionsBar } from "./ScriptActionsBar";
import { ScriptAnswerHeader } from "./ScriptAnswerHeader";
import { ScriptAnswerShotDetail } from "./ScriptAnswerShotDetail";
import { ScriptAnswerShotRail } from "./ScriptAnswerShotRail";
import { ScriptCorpusEvidenceStrip } from "./ScriptCorpusEvidenceStrip";
import { ScriptNextVideoCallout } from "./ScriptNextVideoCallout";
import { ScriptShotNavigator } from "./ScriptShotNavigator";

function formatProofLine(proof: ScriptFormatProof): string | null {
  if (proof.kind === "hook_line" && proof.phrase) {
    const handle = proof.handle ? ` — @${proof.handle}` : "";
    const views = typeof proof.views === "number" ? ` (${formatViews(proof.views)} view)` : "";
    return `“${proof.phrase}”${handle}${views}`;
  }
  if (proof.kind === "hook_stat" && (proof.label_vi || proof.hook_type)) {
    const label = proof.label_vi || proof.hook_type;
    const views =
      typeof proof.avg_views === "number" ? ` — TB ${formatViews(proof.avg_views)} view` : "";
    const n = typeof proof.sample_size === "number" ? ` (${proof.sample_size} video)` : "";
    return `${label}${views}${n}`;
  }
  return null;
}

export function ScriptBody({
  report,
  sessionId = null,
  nicheId = null,
  onOpenShoot,
}: {
  report: ScriptReportPayload;
  sessionId?: string | null;
  nicheId?: number | null;
  onOpenShoot?: (draftId: string) => void;
}) {
  const shots = report.shots ?? [];
  const [idx, setIdx] = useState(0);
  const [savedDraftId, setSavedDraftId] = useState<string | null>(null);
  const safeIdx = Math.min(Math.max(0, idx), Math.max(0, shots.length - 1));
  const shot = shots[safeIdx];

  const { data: sceneIntel } = useSceneIntelligence(nicheId);

  const editorShots = useMemo(() => {
    const fallbacks = scriptEditorFallbacks(report.duration);
    const mapped = reportShotsToEditorShots(shots, fallbacks);
    return mergeSceneIntelIntoShots(mapped, sceneIntel?.scenes);
  }, [shots, report.duration, sceneIntel?.scenes]);

  const activeEditorShot = editorShots[safeIdx];
  const sceneRow = activeEditorShot
    ? sceneRowForShot(sceneIntel?.scenes, activeEditorShot.intelSceneType)
    : undefined;

  const sections = useMemo(
    () => report.narrative_vi?.diagnosis_vi?.sections ?? [],
    [report.narrative_vi?.diagnosis_vi?.sections],
  );
  const corpusTiles = useMemo(() => allScriptCorpusTiles(shots), [shots]);
  const nextVideoText = useMemo(() => scriptNextVideoText(sections), [sections]);

  const goPrev = useCallback(() => setIdx((v) => Math.max(0, v - 1)), []);
  const goNext = useCallback(
    () => setIdx((v) => Math.min(shots.length - 1, v + 1)),
    [shots.length],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      }
      if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goPrev, goNext]);

  return (
    <div className="space-y-6 text-sm text-[color:var(--gv-ink-2)]">
      <ScriptAnswerHeader report={report} hasCorpusStrip={corpusTiles.length > 0} />

      {corpusTiles.length > 0 ? <ScriptCorpusEvidenceStrip tiles={corpusTiles} /> : null}

      {report.format_rationale?.text_vi ? (
        <section className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4">
          <p className="gv-mono mb-2 text-[11px] font-semibold gv-kicker tracking-[0.12em] text-[color:var(--gv-ink-3)]">
            Vì sao cấu trúc này
          </p>
          <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink)]">
            {report.format_rationale.text_vi}
          </p>
          {report.format_rationale.proofs?.length ? (
            <ul className="m-0 mt-2 list-none space-y-1 p-0">
              {report.format_rationale.proofs.map((proof, i) => {
                const line = formatProofLine(proof);
                if (!line) return null;
                return (
                  <li
                    key={`${proof.kind}-${proof.hook_type ?? proof.phrase ?? i}`}
                    className="text-[12px] leading-snug text-[color:var(--gv-ink-3)]"
                  >
                    {line}
                  </li>
                );
              })}
            </ul>
          ) : null}
        </section>
      ) : null}

      {nextVideoText ? <ScriptNextVideoCallout text={nextVideoText} /> : null}

      {shot && activeEditorShot ? (
        <section
          aria-labelledby="script-shot-panel-title"
          className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4"
        >
          <div className="mb-4 space-y-3">
            <div className="space-y-1">
              <h3
                id="script-shot-panel-title"
                className="gv-mono m-0 text-[11px] font-semibold gv-kicker tracking-[0.12em] text-[color:var(--gv-ink-3)]"
              >
                {shots.length} cảnh · hướng dẫn quay
              </h3>
              <p className="m-0 text-[13px] leading-snug text-[color:var(--gv-ink-3)]">
                Chọn từng cảnh để xem lời thoại, góc máy và clip tham chiếu — dùng ← → trên bàn phím.
              </p>
            </div>
            <ScriptShotNavigator
              index={safeIdx}
              total={shots.length}
              onPrev={goPrev}
              onNext={goNext}
            />
            <ScriptAnswerShotRail shots={shots} activeIndex={safeIdx} onSelect={setIdx} />
          </div>

          <ScriptAnswerShotDetail
            shot={shot}
            shotIndex={safeIdx}
            shotCount={shots.length}
            editorShot={activeEditorShot}
            sceneRow={sceneRow}
            suppressPerShotRefs={corpusTiles.length > 0}
            hideSceneReferenceClips={corpusTiles.length > 0}
          />

          <div className="mt-6 border-t border-[color:var(--gv-rule)] pt-4">
            <ScriptShotNavigator
              index={safeIdx}
              total={shots.length}
              onPrev={goPrev}
              onNext={goNext}
            />
          </div>
        </section>
      ) : null}

      <ScriptActionsBar
        report={report}
        sessionId={sessionId}
        savedDraftId={savedDraftId}
        onDraftSaved={setSavedDraftId}
        onShoot={(id) => onOpenShoot?.(id)}
      />
    </div>
  );
}
