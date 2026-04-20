/**
 * Phase C.3.2 — IdeaBlock.
 *
 * Layout (plan §C.3 design spec, re-scoped from `answer.jsx` primitives):
 *   60px | 1fr | 220px grid, 22/24 padding, border + paper bg.
 *   Left: serif rank.
 *   Middle: title + tag/confidence row + angle + why_works + hook callout +
 *           slides accordion + prerequisites chips.
 *   Right: metric block + style chip + 2 evidence thumbnails.
 *
 * Variant mode (`payload.variant === "hook_variants"`) is rendered identically
 * by this component — the upstream report builder collapses `slides[]` to 2–3
 * bullets and emphasises the hook callout via copy, so no branching here.
 */

import { useState } from "react";
import { useNavigate } from "react-router";

import type { IdeaBlockPayloadData } from "@/lib/api-types";
import { styleLabelVi, tagLabelVi } from "./ideasFormat";

type SlideRow = { step?: number | string; body?: string } & Record<string, unknown>;

function SlideAccordion({ slides }: { slides: SlideRow[] }) {
  const [open, setOpen] = useState(false);
  const count = slides.length;
  return (
    <div className="mt-[10px] rounded-md border border-[color:var(--gv-rule)]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-[14px] py-[10px] text-left text-[12px] text-[color:var(--gv-ink-3)]"
      >
        <span>Slide-by-slide ({count} slide)</span>
        <span aria-hidden>{open ? "▾" : "▸"}</span>
      </button>
      {open ? (
        <ol className="border-t border-[color:var(--gv-rule)]">
          {slides.map((s, i) => {
            const step = s.step ?? i + 1;
            const body = s.body ?? "";
            return (
              <li
                key={`${step}-${i}`}
                className="grid grid-cols-[28px_1fr] gap-3 border-t border-[color:var(--gv-rule-2)] px-[14px] py-[10px] first:border-t-0 text-[13px] leading-[1.5] text-[color:var(--gv-ink-2)]"
              >
                <span className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
                  {String(step).padStart(2, "0")}
                </span>
                <span>{body}</span>
              </li>
            );
          })}
        </ol>
      ) : null}
    </div>
  );
}

function MetricBlock({ metric }: { metric: IdeaBlockPayloadData["metric"] }) {
  const label = (metric?.label as string | undefined) ?? "Retention";
  const value = (metric?.value as string | undefined) ?? "—";
  const range = (metric?.range as string | undefined) ?? "";
  return (
    <div>
      <p className="gv-mono text-[9px] uppercase tracking-wide text-[color:var(--gv-ink-4)]">
        {label}
      </p>
      <p className="gv-serif text-[28px] leading-none text-[color:var(--gv-ink)]">{value}</p>
      {range ? (
        <p className="gv-mono mt-1 text-[11px] text-[color:var(--gv-ink-4)]">{range}</p>
      ) : null}
    </div>
  );
}

/**
 * Thumbnail tile — token-only background (no hardcoded hex). Users tap into
 * `/app/video?video_id=…` to see the real thumbnail; the tile here is a
 * neutral placeholder with a mono rank chip.
 */
function EvidenceThumbs({ ids }: { ids: string[] }) {
  const navigate = useNavigate();
  if (ids.length === 0) return null;
  return (
    <div className="mt-3 flex flex-col gap-2">
      {ids.map((vid, i) => (
        <button
          key={vid}
          type="button"
          onClick={() => navigate(`/app/video?video_id=${encodeURIComponent(vid)}`)}
          className="relative aspect-[9/12] w-full overflow-hidden rounded border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] text-left"
          aria-label={`Xem video tham khảo ${vid}`}
        >
          <span className="gv-mono absolute bottom-1 left-1 rounded bg-[color:var(--gv-paper)] px-1 text-[10px] text-[color:var(--gv-ink-3)]">
            #{i + 1}
          </span>
        </button>
      ))}
    </div>
  );
}

export function IdeaBlock({ block }: { block: IdeaBlockPayloadData }) {
  const confSample = (block.confidence?.sample_size as number | undefined) ?? 0;
  const confCreators = (block.confidence?.creators as number | undefined) ?? 0;
  const slides = (block.slides ?? []) as SlideRow[];
  return (
    <article className="grid grid-cols-1 gap-5 border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5 min-[900px]:grid-cols-[60px_minmax(0,1fr)_220px]">
      <div className="gv-serif text-[40px] leading-none text-[color:var(--gv-ink-3)]">
        {String(block.id || "01").padStart(2, "0")}
      </div>

      <div className="min-w-0">
        <h4 className="gv-serif text-[22px] font-medium leading-[1.25] tracking-tight text-[color:var(--gv-ink)]">
          {block.title}
        </h4>

        <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-[color:var(--gv-ink-4)]">
          <span className="gv-mono rounded border border-[color:var(--gv-rule)] px-2 py-0.5 text-[10px] text-[color:var(--gv-ink-2)]">
            {tagLabelVi(block.tag)}
          </span>
          {confSample > 0 ? (
            <span className="gv-mono">
              N={confSample} · {confCreators} creator
            </span>
          ) : null}
        </div>

        <p className="mt-2 text-[14px] leading-[1.55] text-[color:var(--gv-ink-2)]">
          {block.angle}
        </p>

        <p className="mt-2 text-[13px] leading-[1.5] text-[color:var(--gv-ink-3)]">
          {block.why_works}
          {block.evidence_video_ids.length > 0 ? (
            <sup className="gv-mono ml-1 text-[10px] font-medium text-[color:var(--gv-accent)]">
              [{block.evidence_video_ids.map((_, idx) => idx + 1).join("][")}]
            </sup>
          ) : null}
        </p>

        <p className="mt-3 rounded bg-[color:var(--gv-ink)] px-[14px] py-[10px] gv-mono text-[14px] font-medium text-[color:var(--gv-canvas)]">
          {block.hook}
        </p>

        {slides.length > 0 ? <SlideAccordion slides={slides} /> : null}

        {block.prerequisites.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {block.prerequisites.map((p) => (
              <span
                key={p}
                className="gv-mono rounded bg-[color:var(--gv-canvas-2)] px-2 py-0.5 text-[10px] text-[color:var(--gv-ink-3)]"
              >
                {p}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div>
        <MetricBlock metric={block.metric} />
        <p className="gv-mono mt-3 inline-flex rounded-sm border border-[color:var(--gv-accent)] px-2 py-0.5 text-[11px] text-[color:var(--gv-accent-deep)]">
          {styleLabelVi(block.style)}
        </p>
        <EvidenceThumbs ids={block.evidence_video_ids} />
      </div>
    </article>
  );
}
