import type { ShotReference } from "@/lib/api-types";
import { formatViews } from "@/lib/formatters";

/**
 * Wave 2.5 Phase B PR #7 — per-shot reference-card strip.
 * Polished 2026-06-01 (S2 of design-pack rollout) to match
 * ``screens/script.jsx:1053-1098``: views chip + description as the
 * on-card label.
 *
 * Rendered under each shot in ``ScriptShotRow`` (studio editor) and
 * ``ShotBlock`` (shoot mode). Shows up to 3 real creator scenes that
 * matched the shot descriptor via ``pick_shot_references``. Each card:
 *
 *   • thumbnail    — prefers the per-scene ``frame_url`` (R2-hosted
 *                    JPG of the exact moment inside [start_s, end_s]);
 *                    falls back to the full video ``thumbnail_url``;
 *                    then to a gradient tile so the layout stays
 *                    stable even with no media.
 *   • creator chip — ``@handle`` overlaid bottom-left.
 *   • timecode     — ``start_s``/end_s shown top-right when present;
 *                    helps the creator jump to the exact scene inside
 *                    TikTok.
 *   • shot label   — ``description`` (12-24 word Gemini gloss) is the
 *                    primary on-card label — what the ref shot LOOKS
 *                    like, not why it matched. Falls back to the
 *                    factual ``match_label`` ("Cùng ngách, hook, khung
 *                    hình") on legacy rows missing ``description``.
 *   • views chip   — accent-blue ``"256K view"`` pill below the label.
 *                    Hidden when ``views`` is null (legacy / pre-backfill).
 *
 * Click opens the TikTok URL in a new tab (``target="_blank"``,
 * ``rel="noopener noreferrer"``). When no ``tiktok_url``, the card
 * renders as a non-interactive ``<div>`` — we don't invent URLs.
 *
 * Empty + null-safe: returns ``null`` when ``refs`` is empty, so the
 * parent row stays compact rather than reserving space for a
 * "sắp có clip" placeholder (we already have that treatment inside
 * SceneIntelligencePanel for the aggregate CLIP THAM KHẢO card — no
 * need to repeat it per shot).
 */

const CARD_FALLBACK_BG = [
  "bg-[color:var(--gv-avatar-3)]",
  "bg-[color:var(--gv-avatar-4)]",
  "bg-[color:var(--gv-avatar-5)]",
] as const;

export type ShotReferenceStripProps = {
  refs: ShotReference[] | undefined | null;
  /**
   * Visual density hint. ``row`` (default) embeds inside the studio
   * grid; ``block`` is used by the shoot-mode block which has full
   * width and can afford a slightly larger card.
   */
  density?: "row" | "block";
};

function formatTimecode(start: number | null, end: number | null): string | null {
  if (start === null || start === undefined) return null;
  if (end === null || end === undefined) return `${Math.round(start)}s`;
  // The scene may be long; keep it compact ("12–34s").
  return `${Math.round(start)}–${Math.round(end)}s`;
}

function ReferenceCard({
  ref,
  idx,
  density,
}: {
  ref: ShotReference;
  idx: number;
  density: "row" | "block";
}) {
  const bgImage = ref.frame_url ?? ref.thumbnail_url;
  const fallback = CARD_FALLBACK_BG[idx % CARD_FALLBACK_BG.length];
  const handle = (ref.creator_handle ?? "").replace(/^@/, "");
  const timecode = formatTimecode(ref.start_s, ref.end_s);
  // Block mode uses a slightly larger card so the meta below the thumb
  // has room to breathe inside the full-width shoot-mode layout.
  const widthClass = density === "block" ? "w-24 min-[700px]:w-28" : "w-20";

  // Description (Gemini's 12-24 word visual gloss) is the design's primary
  // on-card label — describes what the shot LOOKS like. ``match_label``
  // ("Cùng ngách, hook, khung hình") is a factual fallback for legacy
  // rows ingested before the description-extraction prompt landed.
  const label = ref.description?.trim() || ref.match_label || null;

  const media = (
    <div
      className={`relative flex aspect-[9/13] ${widthClass} shrink-0 flex-col justify-end overflow-hidden rounded p-1.5 text-left text-[color:var(--gv-canvas)] ${
        !bgImage ? fallback : ""
      }`}
      style={
        bgImage
          ? {
              backgroundImage: `url(${bgImage})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }
          : undefined
      }
    >
      {/* Subtle bottom gradient so the creator handle stays legible over
          arbitrary thumbnail colors. */}
      {bgImage ? (
        <div
          className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 rounded-b"
          style={{
            background:
              "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.55) 100%)",
          }}
        />
      ) : null}
      {timecode ? (
        <span className="gv-mono absolute right-1 top-1 rounded bg-[color:color-mix(in_srgb,var(--gv-ink)_58%,transparent)] px-1 text-[9px] text-[color:var(--gv-canvas)]">
          {timecode}
        </span>
      ) : null}
      {handle ? (
        <span className="gv-mono relative text-[9px] opacity-90 drop-shadow">
          @{handle}
        </span>
      ) : null}
    </div>
  );

  // Two-line description / fallback chip + accent views pill.
  const meta = (
    <div className="mt-1 flex flex-col gap-0.5">
      {label ? (
        <span
          className="block text-[10px] leading-[1.3] text-[color:var(--gv-ink-2)] line-clamp-2"
          title={label}
        >
          {label}
        </span>
      ) : null}
      {ref.views != null ? (
        <span
          className="gv-mono text-[10px] font-semibold text-[color:var(--gv-pos-deep)]"
          aria-label={`${ref.views} view`}
        >
          {formatViews(ref.views)} view
        </span>
      ) : null}
    </div>
  );

  if (ref.tiktok_url) {
    return (
      <a
        href={ref.tiktok_url}
        target="_blank"
        rel="noopener noreferrer"
        className={`${widthClass} shrink-0`}
        onClick={(e) => {
          // Don't bubble the shot-card's onClick selection handler.
          e.stopPropagation();
        }}
      >
        {media}
        {meta}
      </a>
    );
  }

  return (
    <div className={`${widthClass} shrink-0`}>
      {media}
      {meta}
    </div>
  );
}

export function ShotReferenceStrip({ refs, density = "row" }: ShotReferenceStripProps) {
  if (!refs || refs.length === 0) return null;
  return (
    <div className="border-t border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2.5">
      <div className="gv-mono gv-uc mb-2 text-[9px] tracking-[0.16em] text-[color:var(--gv-ink-4)]">
        ✻ {refs.length} SHOT THAM KHẢO TỪ VIDEO VIRAL · CÙNG MỤC ĐÍCH
      </div>
      <div className="flex gap-2 overflow-x-auto pb-0.5">
        {refs.map((r, i) => (
          <ReferenceCard
            key={`${r.video_id}-${r.scene_index}`}
            ref={r}
            idx={i}
            density={density}
          />
        ))}
      </div>
    </div>
  );
}
