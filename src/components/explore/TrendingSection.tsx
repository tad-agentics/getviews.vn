import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { SignalBadge } from "@/components/chat/SignalBadge";
import { getVideoMeta, type VideoMeta } from "@/lib/services/corpus-service";
import { useTrendingCards, type TrendingCardRow } from "@/hooks/useTrendingCards";
import { VideoPlayerModal, type ExploreGridVideo } from "@/components/explore/VideoPlayerModal";
import { formatViews, formatDate } from "@/lib/formatters";

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

function metaToExploreVideo(meta: VideoMeta): ExploreGridVideo {
  return {
    id: meta.video_id,
    views: meta.views ? formatViews(meta.views) : "—",
    time: meta.indexed_at ? formatDate(meta.indexed_at) : "—",
    img: meta.thumbnail_url ?? PLACEHOLDER_THUMB,
    text: meta.hook_phrase ?? "",
    handle: meta.creator_handle ? `@${meta.creator_handle}` : "@—",
    caption: meta.hook_phrase || (meta.creator_handle ? `Video @${meta.creator_handle}` : "Video"),
    likes: meta.likes != null ? formatViews(meta.likes) : "—",
    comments: meta.comments != null ? formatViews(meta.comments) : "—",
    shares: meta.shares != null ? formatViews(meta.shares) : "—",
    videoUrl: meta.video_url ?? "",
    tiktok_url: meta.tiktok_url,
  };
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

function OverlappingThumbs({ thumbs }: { thumbs: (VideoMeta | null | undefined)[] }) {
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
          <img
            src={m.thumbnail_url ?? PLACEHOLDER_THUMB}
            alt=""
            className="h-full w-full object-cover"
            onError={(e) => {
              e.currentTarget.onerror = null;
              e.currentTarget.src = PLACEHOLDER_THUMB;
            }}
          />
        </div>
      ))}
    </div>
  );
}

function TrendingCardItem({
  card,
  metaById,
  index,
  onClick,
}: {
  card: TrendingCardRow;
  metaById: Record<string, VideoMeta | null | undefined>;
  index: number;
  onClick: () => void;
}) {
  const ids = (card.video_ids ?? []).slice(0, 3);
  const thumbs = ids.map((id) => metaById[id]);

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onClick();
      }}
      className="min-w-[240px] max-w-[260px] flex-shrink-0 snap-start overflow-hidden rounded-[12px] border border-[var(--border)] bg-[var(--surface)] cursor-pointer hover:border-[var(--purple)] hover:shadow-sm transition-all duration-[150ms]"
    >
      <div className="h-[3px] w-full" style={{ background: signalBarColor(card.signal) }} />
      <div className="p-3">
        <div className="flex items-start gap-2">
          <h3 className="min-w-0 flex-1 text-sm font-semibold leading-snug text-[var(--ink)] line-clamp-2">
            {card.title}
          </h3>
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
  const [openCard, setOpenCard] = useState<TrendingCardRow | null>(null);

  // Eager: only the first 3 IDs per card — for thumbnail circles on mount
  const thumbIdsAll = useMemo(() => {
    const ids = new Set<string>();
    for (const c of cards) {
      for (const id of (c.video_ids ?? []).slice(0, 3)) {
        if (id) ids.add(id);
      }
    }
    return [...ids];
  }, [cards]);

  const thumbQueryKey = useMemo(() => [...thumbIdsAll].sort().join("|"), [thumbIdsAll]);

  const { data: metaById = {} } = useQuery({
    queryKey: ["trending_thumb_meta", nicheId, thumbQueryKey],
    queryFn: async () => {
      const entries = await Promise.all(
        thumbIdsAll.map(async (id) => {
          const meta = await getVideoMeta(id);
          return [id, meta] as const;
        }),
      );
      return Object.fromEntries(entries) as Record<string, VideoMeta | null>;
    },
    enabled: nicheId != null && thumbIdsAll.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  // Lazy: fetch all video IDs for the clicked card, only when openCard changes
  const openCardVideoIds = useMemo(
    () => (openCard?.video_ids ?? []).filter(Boolean) as string[],
    [openCard],
  );

  const { data: openCardMeta = {} } = useQuery({
    queryKey: ["trending_modal_meta", openCard?.id ?? "none"],
    queryFn: async () => {
      const entries = await Promise.all(
        openCardVideoIds.map(async (id) => {
          const meta = await getVideoMeta(id);
          return [id, meta] as const;
        }),
      );
      return Object.fromEntries(entries) as Record<string, VideoMeta | null>;
    },
    enabled: openCardVideoIds.length > 0,
    staleTime: 5 * 60 * 1000,
  });

  const modalVideos = useMemo<ExploreGridVideo[]>(() => {
    if (!openCard) return [];
    return (openCard.video_ids ?? [])
      .map((id) => openCardMeta[id])
      .filter((m): m is VideoMeta => m != null && Boolean(m.video_url))
      .map(metaToExploreVideo);
  }, [openCard, metaById]);

  const showSkeleton = nicheId === null || isPending;

  return (
    <>
      {openCard && modalVideos.length > 0 ? (
        <VideoPlayerModal
          video={modalVideos[0]}
          allVideos={modalVideos}
          onClose={() => setOpenCard(null)}
        />
      ) : null}

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
              <TrendingCardItem
                key={card.id}
                card={card}
                metaById={metaById}
                index={i}
                onClick={() => setOpenCard(card)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
