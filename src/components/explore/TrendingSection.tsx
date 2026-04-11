import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { SignalBadge } from "@/components/chat/SignalBadge";
import { getVideoMeta, type VideoMeta } from "@/lib/services/corpus-service";
import { useTrendingCards, type TrendingCardRow } from "@/hooks/useTrendingCards";

const PLACEHOLDER_THUMB = "/placeholder.svg";

interface Props {
  nicheId: number | null;
}

function signalBarColor(signal: string): string {
  const s = signal.toLowerCase();
  if (s === "rising") return "var(--purple)";
  if (s === "early") return "#F59E0B";
  if (s === "declining") return "#EF4444";
  return "var(--border)";
}

function TrendingCardSkeleton() {
  return (
    <div
      className="min-w-[240px] max-w-[260px] flex-shrink-0 snap-start overflow-hidden rounded-[12px] border border-[var(--border)] bg-[var(--surface)] animate-pulse"
      aria-hidden
    >
      <div className="h-[3px] bg-[var(--border)]" />
      <div className="p-3 space-y-2">
        <div className="h-4 w-3/4 rounded bg-[var(--surface-alt)]" />
        <div className="h-3 w-full rounded bg-[var(--surface-alt)]" />
        <div className="h-3 w-5/6 rounded bg-[var(--surface-alt)]" />
        <div className="flex justify-end pt-1">
          <div className="h-5 w-16 rounded-full bg-[var(--surface-alt)]" />
        </div>
      </div>
    </div>
  );
}

function OverlappingThumbs({
  thumbs,
}: {
  thumbs: (VideoMeta | null | undefined)[];
}) {
  const valid = thumbs.filter((t): t is VideoMeta => t != null && Boolean(t.thumbnail_url));
  if (valid.length === 0) return null;

  return (
    <div className="mt-2 flex items-center pl-1">
      {valid.slice(0, 3).map((m, idx) => (
        <div
          key={`${m.video_id}-${idx}`}
          className="h-5 w-5 flex-shrink-0 overflow-hidden rounded-full border border-[var(--border)] bg-[var(--surface-alt)]"
          style={{ marginLeft: idx === 0 ? 0 : -4, zIndex: 3 - idx }}
        >
          <img src={m.thumbnail_url ?? PLACEHOLDER_THUMB} alt="" className="h-full w-full object-cover" onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_THUMB; }} />
        </div>
      ))}
    </div>
  );
}

function TrendingCardItem({
  card,
  metaById,
  index,
}: {
  card: TrendingCardRow;
  metaById: Record<string, VideoMeta | null | undefined>;
  index: number;
}) {
  const ids = (card.video_ids ?? []).slice(0, 3);
  const thumbs = ids.map((id) => metaById[id]);

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
      className="min-w-[240px] max-w-[260px] flex-shrink-0 snap-start overflow-hidden rounded-[12px] border border-[var(--border)] bg-[var(--surface)]"
    >
      <div className="h-[3px] w-full" style={{ background: signalBarColor(card.signal) }} />
      <div className="p-3">
        <div className="flex items-start gap-2">
          <h3 className="min-w-0 flex-1 text-sm font-semibold leading-snug text-[var(--ink)] line-clamp-2">{card.title}</h3>
          <div className="flex-shrink-0 pt-0.5">
            <SignalBadge signal={card.signal} size="sm" />
          </div>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-[var(--ink-soft)] line-clamp-3">{card.description}</p>
        {card.corpus_cite ? (
          <p className="mt-2 font-mono text-[10px] text-[var(--faint)]">{card.corpus_cite}</p>
        ) : null}
        {ids.length > 0 ? <OverlappingThumbs thumbs={thumbs} /> : null}
      </div>
    </motion.article>
  );
}

export function TrendingSection({ nicheId }: Props) {
  const { data: cards = [], isPending } = useTrendingCards(nicheId);

  const videoIdsAll = useMemo(() => {
    const ids = new Set<string>();
    for (const c of cards) {
      for (const id of c.video_ids ?? []) {
        if (id) ids.add(id);
      }
    }
    return [...ids];
  }, [cards]);

  const videoMetaQueryKey = useMemo(() => [...videoIdsAll].sort().join("|"), [videoIdsAll]);

  const { data: metaById = {} } = useQuery({
    queryKey: ["trending_video_meta", nicheId, videoMetaQueryKey],
    queryFn: async () => {
      const entries = await Promise.all(
        videoIdsAll.map(async (id) => {
          const meta = await getVideoMeta(id);
          return [id, meta] as const;
        }),
      );
      return Object.fromEntries(entries) as Record<string, VideoMeta | null>;
    },
    enabled: nicheId != null && videoIdsAll.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  const showSkeleton = nicheId === null || isPending;

  return (
    <div className="mb-4">
      <h2 className="mb-3 text-sm font-bold text-[var(--ink)]">Xu hướng tuần này</h2>

      {showSkeleton ? (
        <div
          className="-mx-5 flex gap-3 overflow-x-auto px-5 pb-2 [scrollbar-width:none] lg:-mx-7 lg:px-7 [&::-webkit-scrollbar]:hidden"
          style={{ scrollSnapType: "x mandatory" }}
        >
          <TrendingCardSkeleton />
          <TrendingCardSkeleton />
          <TrendingCardSkeleton />
        </div>
      ) : cards.length === 0 ? (
        <p className="text-sm text-[var(--faint)]">Dữ liệu tuần này đang được cập nhật...</p>
      ) : (
        <div
          className="-mx-5 flex gap-3 overflow-x-auto px-5 pb-2 [scrollbar-width:none] lg:-mx-7 lg:px-7 [&::-webkit-scrollbar]:hidden"
          style={{ scrollSnapType: "x mandatory" }}
        >
          {cards.map((card, i) => (
            <TrendingCardItem key={card.id} card={card} metaById={metaById} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
