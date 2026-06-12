import { Video } from "lucide-react";

import { DiagnosisReferenceVideoCards } from "@/components/diagnosis/DiagnosisReferenceVideoCards";
import { CueChip } from "@/components/v2/CueChip";
import { FormattedVO } from "@/components/v2/FormattedVO";
import { MiniBarCompare } from "@/components/v2/MiniBarCompare";
import { SceneIntelligencePanel } from "@/components/v2/SceneIntelligencePanel";
import { ShotTypeVisual } from "@/components/v2/ShotTypeVisual";
import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";
import { referenceClipsFromEditorShot } from "@/lib/scriptEditorMerge";
import type { SceneIntelligenceRow, ScriptShotCardData, ScriptVoLineData } from "@/lib/api-types";
import { overlayStyleVi } from "@/lib/constants/enum-labels-vi";
import { scriptRefToDiagnosisTile } from "@/lib/scriptNarrativeRefs";
import { shotHasCorpusPacing } from "@/lib/scriptVerdictProse";

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

export function ScriptAnswerShotDetail({
  shot,
  shotIndex,
  shotCount,
  editorShot,
  sceneRow,
  suppressPerShotRefs = false,
  hideSceneReferenceClips = false,
}: {
  shot: ScriptShotCardData;
  shotIndex: number;
  shotCount: number;
  editorShot: ScriptEditorShot;
  sceneRow?: SceneIntelligenceRow;
  /** When global corpus strip is shown, skip duplicate per-shot reference tiles. */
  suppressPerShotRefs?: boolean;
  hideSceneReferenceClips?: boolean;
}) {
  const showScenePanel = Boolean(sceneRow);
  const span = (shot.t1 ?? 0) - (shot.t0 ?? 0);
  const hasVo = Boolean(shot.vo && shot.vo.length > 0);
  const showPacing = shotHasCorpusPacing(shot, sceneRow);
  const slow = showPacing && span > editorShot.winnerAvg * 1.2;
  const overlayLabel = overlayStyleVi(shot.overlay, shot.overlay ?? "");
  const refTiles = (shot.references ?? [])
    .map(scriptRefToDiagnosisTile)
    .filter((t): t is NonNullable<ReturnType<typeof scriptRefToDiagnosisTile>> => t != null);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start gap-3">
        <ShotTypeVisual intelSceneType={editorShot.intelSceneType} cam={shot.cam ?? ""} />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="gv-mono m-0 text-[11px] font-semibold gv-kicker tracking-wide text-[color:var(--gv-accent)]">
              Cảnh {shotIndex + 1} / {shotCount}
            </p>
            <span className="gv-mono rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[11px] text-[color:var(--gv-ink-3)]">
              {shot.t0 ?? 0}s – {shot.t1 ?? 0}s
            </span>
            {showPacing ? (
              <span
                className={`gv-mono inline-flex items-center gap-[5px] rounded-[3px] px-[7px] py-0.5 text-[11px] font-medium ${
                  slow
                    ? "bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent-deep)]"
                    : "bg-[rgba(0,159,250,0.12)] text-[rgb(0,159,250)]"
                }`}
              >
                {slow ? "✕" : "✓"} {span.toFixed(1)}s · mảng {editorShot.winnerAvg}s
              </span>
            ) : null}
          </div>
          {showPacing ? (
            <MiniBarCompare
              yoursSec={span}
              corpusSec={editorShot.corpusAvg}
              winnerSec={editorShot.winnerAvg}
            />
          ) : null}
        </div>
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
          <dd className="m-0 text-sm leading-snug text-[color:var(--gv-ink-2)]">{shot.viz}</dd>
        </div>
        {!hasVo && shot.voice ? (
          <div>
            <dt className="gv-mono mb-0.5 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
              Giọng / nhân vật
            </dt>
            <dd className="m-0 text-sm leading-snug text-[color:var(--gv-ink-2)]">{shot.voice}</dd>
          </div>
        ) : null}
        <div>
          <dt className="gv-mono mb-0.5 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-4)]">
            Chữ trên màn hình
          </dt>
          <dd className="m-0 rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-2 py-1.5 text-[12px] font-medium text-[color:var(--gv-ink)]">
            {overlayLabel}
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

      {hasVo ? (
        <div className="border-t border-[color:var(--gv-rule)] pt-4">
          <p className="gv-mono mb-2 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
            Lời thoại
          </p>
          <ul className="m-0 list-none space-y-2 p-0">
            {shot.vo!.map((line, i) => (
              <li
                key={`${shotIndex}-${i}-${line.text.slice(0, 12)}`}
                className="flex flex-wrap gap-x-2 gap-y-1 text-sm leading-snug"
              >
                <span className="gv-mono shrink-0 text-[11px] text-[color:var(--gv-ink-4)]">
                  {formatVoStamp(line.t, Number(shot.t0 ?? 0) + i * 0.5)}
                </span>
                <span className="text-[color:var(--gv-ink)]">
                  <FormattedVO text={line.text} />
                  {line.cue ? <CueChip text={line.cue} /> : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {showScenePanel && sceneRow ? (
        <div className="border-t border-[color:var(--gv-rule)] pt-4">
          <SceneIntelligencePanel
            shot={editorShot}
            shotIndex={shotIndex}
            overlaySamples={sceneRow.overlay_samples ?? []}
            referenceClips={referenceClipsFromEditorShot(editorShot).map((clip) => ({
              video_id: clip.video_id,
              thumbnail_url: clip.thumbnail_url,
              creator_handle: clip.handle,
              label: clip.label,
              duration_sec: clip.duration_sec,
            }))}
            sceneSampleSize={sceneRow.sample_size}
            overlayCorpusCount={sceneRow.sample_size}
            hideReferenceClips={hideSceneReferenceClips}
          />
        </div>
      ) : !suppressPerShotRefs && refTiles.length > 0 ? (
        <DiagnosisReferenceVideoCards tiles={refTiles} embedded showLabel={false} />
      ) : null}
    </div>
  );
}
