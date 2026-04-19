import { Link } from "react-router";
import { Plus } from "lucide-react";
import type { ScriptEditorShot } from "@/lib/scriptEditorMerge";
import { MiniBarCompare } from "@/components/v2/MiniBarCompare";

export type ScriptReferenceClip = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string;
  label: string;
  duration_sec: number;
};

export type SceneIntelligencePanelProps = {
  shot: ScriptEditorShot;
  shotIndex: number;
  /** Up to 5 overlay strings from ``scene_intelligence.overlay_samples`` or presets. */
  overlaySamples: string[];
  referenceClips: ScriptReferenceClip[];
  /** When set and below 30, shows a thin-corpus banner (plan risk · scene intelligence). */
  sceneSampleSize?: number | null;
  /** Positive integer → anchors the "Trong N video thắng" copy; falls back to generic phrasing. */
  overlayCorpusCount?: number | null;
};

const CLIP_FALLBACK_BG = [
  "bg-[color:var(--gv-avatar-3)]",
  "bg-[color:var(--gv-avatar-4)]",
  "bg-[color:var(--gv-avatar-5)]",
] as const;

export function SceneIntelligencePanel({
  shot,
  shotIndex,
  overlaySamples,
  referenceClips,
  sceneSampleSize = null,
  overlayCorpusCount = null,
}: SceneIntelligencePanelProps) {
  const span = shot.t1 - shot.t0;
  const slow = span > shot.winnerAvg * 1.2;
  const thinCorpus =
    typeof sceneSampleSize === "number" && sceneSampleSize > 0 && sceneSampleSize < 30;

  return (
    <div className="flex flex-col gap-3.5">
      {thinCorpus ? (
        <p className="gv-mono rounded-none border border-[color:var(--gv-rule)] bg-[color:var(--gv-accent-soft)] px-3 py-2 text-[10px] leading-snug text-[color:var(--gv-accent-deep)]">
          Ngách đang thưa ({sceneSampleSize} video / scene) — pacing và overlay là định hướng, không tuyệt đối.
        </p>
      ) : null}
      <div className="rounded-none border border-[color:var(--gv-ink)] bg-[color:var(--gv-ink)] p-4 text-[color:var(--gv-canvas)]">
        <div className="gv-mono gv-uc mb-2 text-[10px] tracking-[0.16em] opacity-60">
          SHOT {String(shotIndex + 1).padStart(2, "0")} · PHÂN TÍCH CẤU TRÚC
        </div>
        <p className="text-pretty text-[18px] font-medium leading-[1.25] tracking-[-0.01em] text-[color:var(--gv-canvas)] [font-family:var(--gv-font-serif)]">
          {shot.tip}
        </p>
      </div>

      <div className="rounded-none border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3.5">
        <div className="gv-mono gv-uc mb-2.5 text-[9.5px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          ĐỘ DÀI SHOT
        </div>
        <div className="mb-2.5 flex items-baseline justify-between gap-2">
          <span className="gv-tight gv-serif text-[28px] font-medium tracking-[-0.02em] text-[color:var(--gv-ink)]">
            {span.toFixed(1)}s
          </span>
          <span
            className={`gv-mono text-[11px] ${slow ? "text-[color:var(--gv-accent)]" : "text-[rgb(0,159,250)]"}`}
          >
            {slow ? `▲ dài hơn ${(span - shot.winnerAvg).toFixed(1)}s` : "✓ đúng nhịp ngách"}
          </span>
        </div>
        <MiniBarCompare yoursSec={span} corpusSec={shot.corpusAvg} winnerSec={shot.winnerAvg} />
        <p className="mt-2.5 text-[11px] leading-[1.5] text-[color:var(--gv-ink-4)]">
          Ngách trung bình <span className="gv-mono text-[color:var(--gv-ink-2)]">{shot.corpusAvg}s</span> · winner{" "}
          <span className="gv-mono text-[rgb(0,159,250)]">{shot.winnerAvg}s</span>
        </p>
      </div>

      <div className="rounded-none border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3.5">
        <div className="gv-mono gv-uc mb-2.5 text-[9.5px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          TEXT OVERLAY · THƯ VIỆN
        </div>
        <p className="mb-2.5 text-xs leading-snug text-[color:var(--gv-ink-3)]">
          {typeof overlayCorpusCount === "number" && overlayCorpusCount > 0
            ? `Trong ${overlayCorpusCount} video thắng, scene loại này dùng:`
            : "Trong các video thắng, scene loại này hay dùng:"}
          <span className="gv-mono mt-1 block text-[13px] font-medium text-[color:var(--gv-ink)]">
            {shot.overlayWinner}
          </span>
        </p>
        {shot.overlay !== "NONE" && overlaySamples.length > 0 ? (
          <div className="flex flex-col gap-1.5">
            {overlaySamples.slice(0, 3).map((o, i) => (
              <button
                key={`${o}-${i}`}
                type="button"
                className="gv-mono flex items-center justify-between rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-[7px] text-left text-[11px] font-medium text-[color:var(--gv-ink-2)] hover:bg-[color:var(--gv-canvas-2)]"
              >
                <span className="min-w-0 truncate">{o}</span>
                <Plus className="h-2.5 w-2.5 shrink-0 opacity-60" strokeWidth={2} aria-hidden />
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="rounded-none border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-3.5">
        <div className="gv-mono gv-uc mb-2.5 text-[9.5px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
          CLIP THAM KHẢO
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {referenceClips.length > 0
            ? referenceClips.map((c, i) => (
                <Link
                  key={c.video_id}
                  to={`/app/video?video_id=${encodeURIComponent(c.video_id)}`}
                  className={`relative flex aspect-[9/13] w-20 shrink-0 flex-col justify-end overflow-hidden rounded p-1.5 text-left text-[color:var(--gv-canvas)] ${
                    !c.thumbnail_url ? CLIP_FALLBACK_BG[i % CLIP_FALLBACK_BG.length] : ""
                  }`}
                  style={
                    c.thumbnail_url
                      ? {
                          backgroundImage: `url(${c.thumbnail_url})`,
                          backgroundSize: "cover",
                          backgroundPosition: "center",
                        }
                      : undefined
                  }
                >
                  <span className="gv-mono text-[9px] opacity-80 drop-shadow">
                    @{c.creator_handle.replace(/^@/, "")}
                  </span>
                  <span className="text-[10px] leading-tight drop-shadow">{c.label}</span>
                  <span className="gv-mono absolute right-1 top-1 rounded bg-[color:color-mix(in_srgb,var(--gv-ink)_58%,transparent)] px-1 text-[9px] text-[color:var(--gv-canvas)]">
                    {c.duration_sec.toFixed(1)}s
                  </span>
                </Link>
              ))
            : [0, 1, 2].map((i) => (
                <div
                  key={`clip-ph-${i}`}
                  className={`flex aspect-[9/13] w-20 shrink-0 flex-col justify-end rounded p-1.5 text-[color:var(--gv-canvas)] ${CLIP_FALLBACK_BG[i % CLIP_FALLBACK_BG.length]}`}
                >
                  <span className="gv-mono text-[9px] opacity-70">—</span>
                  <span className="text-[10px] leading-tight">Sắp có clip</span>
                </div>
              ))}
        </div>
        <p className="mt-2.5 text-[11px] leading-[1.45] text-[color:var(--gv-ink-4)]">
          {referenceClips.length
            ? "Scene cùng mục đích từ video thắng gần đây."
            : "3 scene cùng mục đích từ video thắng tuần này (đang chờ dữ liệu)."}
        </p>
      </div>
    </div>
  );
}
