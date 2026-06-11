/**
 * Phase C — 6-shot script report inside answer sessions (Studio).
 * Wave 2 — narrative-first: headline → sections → shot rail.
 * F7 — scene intelligence panel when nightly ``scene_intelligence`` matches shot type.
 */
import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Video } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import { SceneIntelligencePanel } from "@/components/v2/SceneIntelligencePanel";
import { ShotReferenceStrip } from "@/components/v2/ShotReferenceStrip";
import { useSceneIntelligence } from "@/hooks/useSceneIntelligence";
import type {
  ScriptFormatProof,
  ScriptReportPayload,
  ScriptVoLineData,
} from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";
import { scriptEditorFallbacks } from "@/lib/scriptEditorFallbacks";
import {
  mergeSceneIntelIntoShots,
  referenceClipsFromEditorShot,
  reportShotsToEditorShots,
  sceneRowForShot,
} from "@/lib/scriptEditorMerge";
import { ScriptActionsBar } from "./ScriptActionsBar";
import { ScriptNarrativeSections } from "./ScriptNarrativeSections";

function formatVoStamp(t: ScriptVoLineData["t"], fallback: number): string {
  if (typeof t === "number" && Number.isFinite(t)) {
    return `${t.toFixed(1)}s`;
  }
  if (typeof t === "string" && t.includes(":")) {
    return t;
  }
  if (typeof t === "string" && t.trim()) {
    return t.trim();
  }
  return `${fallback.toFixed(1)}s`;
}

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
  /** Session or profile niche — drives free ``GET /script/scene-intelligence``. */
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
  const showScenePanel = Boolean(sceneRow && activeEditorShot);

  const narrative = report.narrative_vi;
  const headline = narrative?.headline_vi?.trim() || report.hook;
  const sections = useMemo(
    () => narrative?.diagnosis_vi?.sections ?? [],
    [narrative?.diagnosis_vi?.sections],
  );

  const pills = [report.niche_label?.trim(), `${report.duration}s`, report.tone].filter(
    Boolean,
  ) as string[];

  return (
    <div className="space-y-6 text-sm text-[color:var(--gv-ink-2)]">
      <header className="space-y-3">
        <p className="gv-kicker text-[color:var(--gv-ink-3)]">
          KỊCH BẢN · {report.tone} · {report.duration} giây
        </p>
        <p
          className="gv-tight m-0 text-[clamp(1.125rem,2.5vi+0.35rem,1.65rem)] font-medium leading-tight text-[color:var(--gv-ink)]"
          style={{ fontFamily: "var(--gv-font-display)", textWrap: "balance" }}
        >
          {headline}
        </p>
        {narrative?.ket_luan_nhanh ? (
          <p className="m-0 text-[14px] leading-relaxed text-[color:var(--gv-ink-2)]">
            {narrative.ket_luan_nhanh}
          </p>
        ) : null}
        {pills.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {pills.map((p) => (
              <span
                key={p}
                className="gv-mono rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[11px] text-[color:var(--gv-ink-3)]"
              >
                {p}
              </span>
            ))}
          </div>
        ) : null}
        <p className="m-0 text-sm leading-relaxed text-[color:var(--gv-ink-3)]">
          <span className="font-medium text-[color:var(--gv-ink-2)]">Chủ đề:</span> {report.topic}
        </p>
        <p className="gv-mono m-0 text-[11px] text-[color:var(--gv-ink-3)]">
          Hook xuất hiện sau ~{Math.round(report.hook_delay_ms / 100) / 10}s
        </p>
      </header>

      {sections.length > 0 ? (
        <ScriptNarrativeSections sections={sections} shots={shots} />
      ) : null}

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

      {shot ? (
        <section className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-4">
          <p className="gv-mono mb-3 text-[11px] font-semibold gv-kicker tracking-[0.12em] text-[color:var(--gv-ink-3)]">
            6 cảnh · chi tiết từng shot
          </p>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <p className="gv-mono m-0 text-[11px] font-semibold gv-kicker tracking-wide text-[color:var(--gv-accent)]">
              Cảnh {safeIdx + 1} / {shots.length}
            </p>
            <span className="gv-mono rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[11px] text-[color:var(--gv-ink-3)]">
              {shot.t0 ?? 0}s – {shot.t1 ?? 0}s
            </span>
          </div>

          <dl className="m-0 space-y-3">
            <div>
              <dt className="gv-mono mb-0.5 flex items-center gap-1 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
                <Video className="h-3 w-3" strokeWidth={2} aria-hidden />
                Máy quay
              </dt>
              <dd className="m-0 text-sm leading-snug text-[color:var(--gv-ink)]">{shot.cam}</dd>
            </div>
            <div>
              <dt className="gv-mono mb-0.5 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
                Hình ảnh
              </dt>
              <dd className="m-0 text-sm leading-snug">{shot.viz}</dd>
            </div>
            <div>
              <dt className="gv-mono mb-0.5 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
                Giọng / nhân vật
              </dt>
              <dd className="m-0 text-sm leading-snug">{shot.voice}</dd>
            </div>
            <div>
              <dt className="gv-mono mb-0.5 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
                Chữ trên màn hình
              </dt>
              <dd className="m-0 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-1.5 text-[12px] font-medium">
                {shot.overlay}
              </dd>
            </div>
            {shot.reason_vi ? (
              <div>
                <dt className="gv-mono mb-0.5 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
                  Vì sao cảnh này
                </dt>
                <dd className="m-0 text-[12px] leading-snug text-[color:var(--gv-ink-3)]">
                  {shot.reason_vi}
                </dd>
              </div>
            ) : null}
          </dl>

          {shot.vo && shot.vo.length > 0 ? (
            <div className="mt-5 border-t border-[color:var(--gv-rule)] pt-4">
              <p className="gv-mono mb-2 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
                Lời thoại
              </p>
              <ul className="m-0 list-none space-y-2 p-0">
                {shot.vo.map((line, i) => (
                  <li
                    key={`${safeIdx}-${i}-${line.text.slice(0, 12)}`}
                    className="flex flex-wrap gap-x-2 gap-y-1 text-sm leading-snug"
                  >
                    <span className="gv-mono shrink-0 text-[11px] text-[color:var(--gv-ink-4)]">
                      {formatVoStamp(line.t, Number(shot.t0 ?? 0) + i * 0.5)}
                    </span>
                    <span className="text-[color:var(--gv-ink)]">“{line.text}”</span>
                    {line.cue ? (
                      <span className="gv-mono rounded border border-dashed border-[color:var(--gv-rule)] px-1.5 py-0.5 text-[11px] text-[color:var(--gv-ink-3)]">
                        {line.cue}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {activeEditorShot && activeEditorShot.references.length > 0 && !showScenePanel ? (
            <div className="-mx-4 mt-5">
              <ShotReferenceStrip refs={activeEditorShot.references} density="block" />
            </div>
          ) : null}

          {showScenePanel && activeEditorShot && sceneRow ? (
            <div className="mt-5 border-t border-[color:var(--gv-rule)] pt-4">
              <SceneIntelligencePanel
                shot={activeEditorShot}
                shotIndex={safeIdx}
                overlaySamples={sceneRow.overlay_samples ?? []}
                referenceClips={referenceClipsFromEditorShot(activeEditorShot).map((clip) => ({
                  video_id: clip.video_id,
                  thumbnail_url: clip.thumbnail_url,
                  creator_handle: clip.handle,
                  label: clip.label,
                  duration_sec: clip.duration_sec,
                }))}
                sceneSampleSize={sceneRow.sample_size}
                overlayCorpusCount={sceneRow.sample_size}
              />
            </div>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-[color:var(--gv-rule)] pt-4">
            <Btn
              variant="ghost"
              size="sm"
              type="button"
              className="min-h-[44px] gap-1"
              disabled={safeIdx <= 0}
              onClick={() => setIdx((v) => Math.max(0, v - 1))}
            >
              <ChevronLeft className="h-4 w-4" strokeWidth={2} aria-hidden />
              Cảnh trước
            </Btn>
            <div className="flex gap-1">
              {shots.map((_, i) => (
                <button
                  // eslint-disable-next-line react/no-array-index-key -- fixed 6 shots
                  key={i}
                  type="button"
                  aria-label={`Cảnh ${i + 1}`}
                  aria-current={i === safeIdx ? "step" : undefined}
                  className={
                    "h-2 w-2 rounded-full " +
                    (i === safeIdx
                      ? "bg-[color:var(--gv-ink)]"
                      : "bg-[color:var(--gv-rule)]")
                  }
                  onClick={() => setIdx(i)}
                />
              ))}
            </div>
            <Btn
              variant="ghost"
              size="sm"
              type="button"
              className="min-h-[44px] gap-1"
              disabled={safeIdx >= shots.length - 1}
              onClick={() => setIdx((v) => Math.min(shots.length - 1, v + 1))}
            >
              Cảnh tiếp
              <ChevronRight className="h-4 w-4" strokeWidth={2} aria-hidden />
            </Btn>
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
