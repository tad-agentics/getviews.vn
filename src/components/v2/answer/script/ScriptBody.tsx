/**
 * Phase C — 6-shot script report inside answer sessions (Studio).
 * Wave 2 — narrative-first: headline → sections → shot rail.
 * F7 — scene intelligence panel when nightly ``scene_intelligence`` matches shot type.
 */
import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Video } from "lucide-react";

import { DiagnosisSectionRenderer } from "@/components/diagnosis/DiagnosisSectionRenderer";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { Btn } from "@/components/v2/Btn";
import { SceneIntelligencePanel } from "@/components/v2/SceneIntelligencePanel";
import { useSceneIntelligence } from "@/hooks/useSceneIntelligence";
import type {
  DiagnosisSectionVi,
  ScriptReportPayload,
  ScriptShotCardData,
  ScriptShotReferenceData,
  ScriptVoLineData,
} from "@/lib/api-types";
import { scriptEditorFallbacks } from "@/lib/scriptEditorFallbacks";
import {
  mergeSceneIntelIntoShots,
  referenceClipsFromEditorShot,
  reportShotsToEditorShots,
  sceneRowForShot,
} from "@/lib/scriptEditorMerge";
import { ScriptActionsBar } from "./ScriptActionsBar";

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

function tiktokHref(ref: ScriptShotReferenceData): string | null {
  const id = ref.video_id;
  if (!id) return null;
  const h = (ref.creator_handle ?? "").replace(/^@/, "").trim();
  if (h) return `https://www.tiktok.com/@${h}/video/${id}`;
  return `https://www.tiktok.com/video/${id}`;
}

function breakoutLabel(ref: ScriptShotReferenceData, shot: ScriptShotCardData): string | null {
  if (typeof ref.breakout_multiplier === "number" && Number.isFinite(ref.breakout_multiplier)) {
    return `${ref.breakout_multiplier.toFixed(1)}×`;
  }
  const w = ref.winner_avg ?? shot.winner_avg;
  const c = ref.corpus_avg ?? shot.corpus_avg;
  if (
    typeof w === "number" &&
    typeof c === "number" &&
    Number.isFinite(w) &&
    Number.isFinite(c) &&
    c > 0
  ) {
    return `${(w / c).toFixed(1)}×`;
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
    () => (narrative?.diagnosis_vi?.sections ?? []) as DiagnosisSectionVi[],
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
        <section className="space-y-2 border-t border-[color:var(--gv-rule)] pt-5">
          {sections.map((section) => (
            <DiagnosisSectionRenderer
              key={String(section.section_id)}
              section={section}
              referenceVideos={[]}
            />
          ))}
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

          {shot.references && shot.references.length > 0 && !showScenePanel ? (
            <div className="mt-5 border-t border-[color:var(--gv-rule)] pt-4">
              <p className="gv-mono mb-2 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">
                Thư viện tham khảo
              </p>
              <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
                {shot.references.map((ref, ri) => {
                  const href = tiktokHref(ref);
                  const bx = breakoutLabel(ref, shot);
                  const inner = (
                    <>
                      <VideoThumbnail
                        thumbnailUrl={ref.thumbnail_url}
                        className="aspect-[9/12] w-full rounded-[3px] object-cover"
                      />
                      {bx ? (
                        <span className="gv-mono absolute left-1 top-1 rounded bg-[color:var(--gv-ink)] px-1 py-0.5 text-[11px] text-[color:var(--gv-canvas)]">
                          {bx}
                        </span>
                      ) : null}
                    </>
                  );
                  return (
                    <li key={`${ref.video_id ?? ri}`} className="w-[68px] shrink-0">
                      {href ? (
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="relative block w-full"
                        >
                          {inner}
                        </a>
                      ) : (
                        <div className="relative">{inner}</div>
                      )}
                    </li>
                  );
                })}
              </ul>
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
