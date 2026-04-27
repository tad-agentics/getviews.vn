import { ArrowRight, Play } from "lucide-react";
import { useIdeaReferences } from "@/hooks/useIdeaReferences";
import { formatViews } from "@/lib/formatters";
import type { ScriptIdeaReference } from "@/lib/api-types";

/**
 * IdeaRefStrip — top of ScriptDetail, above the storyboard.
 * Per design pack ``screens/script.jsx`` lines 1284-1360.
 *
 * Renders 5 viral videos in the user's niche that share the chosen
 * idea's hook_type — proof-points the creator can study for cadence,
 * overlay, and pacing reference. Each card shows: thumbnail (9:13) +
 * match% chip + duration chip + creator + shot label + views.
 *
 * Cards are external links (open the source TikTok URL in a new tab).
 * Empty + null-safe: returns ``null`` when the BE returns no references
 * (e.g. niche has zero corpus videos yet) — the storyboard below stays
 * useful on its own.
 *
 * Mobile: drops to 3 cards via the responsive grid + a CSS rule that
 * hides the 4th + 5th tiles below the 720px breakpoint.
 */

const CARD_FALLBACK_BG = [
  "bg-[color:var(--gv-avatar-3)]",
  "bg-[color:var(--gv-avatar-4)]",
  "bg-[color:var(--gv-avatar-5)]",
] as const;

export type IdeaRefStripProps = {
  nicheId: number | null;
  hookType: string | null;
  /** Optional VN display word for the strip headline ("so sánh giá ×N"). */
  ideaAngle?: string | null;
};

export function IdeaRefStrip({
  nicheId,
  hookType,
  ideaAngle,
}: IdeaRefStripProps) {
  const { data, isPending } = useIdeaReferences(nicheId, hookType, 5);
  const refs = data?.references ?? [];

  // Hide the strip entirely while pending (avoids a flicker) AND when the
  // BE returns nothing — the storyboard below stands on its own.
  if (isPending || refs.length === 0) return null;

  const angleWord = ideaAngle?.trim() || "này";

  return (
    <section className="mb-7 rounded-[8px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-4 py-4">
      <div className="mb-3 flex items-baseline gap-2.5 flex-wrap">
        <span className="gv-mono text-[9.5px] font-bold uppercase tracking-[0.14em] bg-[color:var(--gv-pos-deep)] text-white px-1.5 py-0.5 rounded-[3px]">
          ✻ THAM KHẢO
        </span>
        <h3
          className="gv-tight text-[18px] font-medium leading-tight text-[color:var(--gv-ink)] m-0"
          style={{ fontFamily: "var(--gv-font-display)", letterSpacing: "-0.01em" }}
        >
          {refs.length} video viral cùng angle &ldquo;{angleWord}&rdquo;
        </h3>
        <span className="text-[12px] text-[color:var(--gv-ink-3)]">
          Cắt khúc từ video thắng — xem cách họ xử lý angle giống bạn
        </span>
      </div>

      <div
        className="idea-ref-grid grid gap-2"
        style={{ gridTemplateColumns: `repeat(${refs.length}, minmax(0, 1fr))` }}
      >
        {refs.map((r, i) => (
          <RefCard key={`${r.video_id}-${i}`} ref_={r} idx={i} />
        ))}
      </div>

      <style>{`
        @media (max-width: 720px) {
          .idea-ref-grid { grid-template-columns: repeat(3, minmax(0, 1fr)) !important; }
          .idea-ref-grid > a:nth-child(n+4),
          .idea-ref-grid > div:nth-child(n+4) { display: none; }
        }
      `}</style>
    </section>
  );
}

function RefCard({ ref_, idx }: { ref_: ScriptIdeaReference; idx: number }) {
  const fallback = CARD_FALLBACK_BG[idx % CARD_FALLBACK_BG.length];
  const handle = (ref_.creator_handle ?? "").replace(/^@/, "");
  const bgImage = ref_.thumbnail_url;
  const dur = ref_.duration_sec != null ? `${ref_.duration_sec}s` : null;

  const inner = (
    <>
      <div
        className={`relative aspect-[9/13] overflow-hidden rounded ${
          bgImage ? "" : fallback
        } flex items-center justify-center text-[color:color-mix(in_srgb,var(--gv-canvas)_70%,transparent)]`}
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
        <Play className="h-5 w-5" aria-hidden="true" />
        {/* Match% badge — top-left */}
        <span
          className="gv-mono absolute left-1.5 top-1.5 rounded bg-[color:color-mix(in_srgb,var(--gv-ink)_70%,transparent)] px-1.5 py-0.5 text-[9px] font-bold text-[color:var(--gv-canvas)]"
          aria-label={`${ref_.match_pct} percent match`}
        >
          {ref_.match_pct}%
        </span>
        {/* Duration — bottom-right */}
        {dur ? (
          <span className="gv-mono absolute right-1.5 bottom-1.5 rounded bg-[color:color-mix(in_srgb,var(--gv-ink)_60%,transparent)] px-1.5 py-0.5 text-[9px] text-[color:var(--gv-canvas)]">
            {dur}
          </span>
        ) : null}
      </div>
      <div className="mt-1.5 flex flex-col gap-0.5 min-w-0">
        {handle ? (
          <span className="gv-mono text-[10px] font-semibold text-[color:var(--gv-ink-4)] truncate">
            @{handle}
          </span>
        ) : null}
        {ref_.shot_label ? (
          <span className="text-[11.5px] leading-tight text-[color:var(--gv-ink)] line-clamp-2">
            {ref_.shot_label}
          </span>
        ) : null}
        <span className="gv-mono text-[10px] font-bold text-[color:var(--gv-pos-deep)]">
          {formatViews(ref_.views)} view
        </span>
      </div>
    </>
  );

  if (ref_.tiktok_url) {
    return (
      <a
        href={ref_.tiktok_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex flex-col gap-0 text-left transition-opacity hover:opacity-90"
      >
        {inner}
      </a>
    );
  }
  return <div className="flex flex-col gap-0 text-left">{inner}</div>;
}

/** Compact link kept for parity with the design's "Xem chi tiết →" pill. */
export function IdeaRefSeeAllLink({ href }: { href: string }) {
  return (
    <a
      href={href}
      className="inline-flex items-center gap-1 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-2.5 py-1 text-[11px] font-medium text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:text-[color:var(--gv-ink)]"
    >
      Xem chi tiết
      <ArrowRight className="h-3 w-3" aria-hidden />
    </a>
  );
}
