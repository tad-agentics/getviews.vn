import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { Loader2, Volume2, VolumeX, X } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Button } from "@/components/ui/Button";
import { corpusKeys, useVideoCorpus, type VideoCorpusFilters } from "@/hooks/useVideoCorpus";
import { useVideoDetail } from "@/hooks/useVideoDetail";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { getRelatedVideos } from "@/lib/data/corpus";
import { formatDate, formatViews } from "@/lib/formatters";

type CorpusRow = {
  id: string;
  tiktok_url: string | null;
  video_url: string | null;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number | null;
  engagement_rate: number | null;
  niche_id: number | null;
  indexed_at: string | null;
};

type SortKey = NonNullable<VideoCorpusFilters["sortBy"]>;

function formatViewsDisplay(n: number | null | undefined): string {
  if (n == null || n === 0) return "—";
  return formatViews(n);
}

function erPercent(rate: number | null | undefined): string {
  if (rate == null || Number.isNaN(rate)) return "—";
  return `${(rate * 100).toFixed(1)}%`;
}

const PLACEHOLDER_THUMB = "/placeholder.svg";

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "indexed_at", label: "Mới nhất" },
  { value: "views", label: "Nhiều view nhất" },
  { value: "engagement_rate", label: "Tương tác cao" },
];

function ExploreGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] animate-pulse">
          <div className="aspect-[9/16] w-full bg-[var(--border)]" />
          <div className="space-y-2 p-2">
            <div className="h-3 w-2/3 rounded bg-[var(--border)]" />
            <div className="h-3 w-1/2 rounded bg-[var(--border)]" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ExploreScreen() {
  const navigate = useNavigate();
  const [selectedNicheId, setSelectedNicheId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<SortKey>("indexed_at");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [muted, setMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);
  const loaderRef = useRef<HTMLDivElement>(null);

  const filters = useMemo<VideoCorpusFilters>(
    () => ({
      nicheId: selectedNicheId,
      sortBy,
      sortOrder: "desc",
      dateFrom: dateFrom || null,
      dateTo: dateTo || null,
    }),
    [selectedNicheId, sortBy, dateFrom, dateTo],
  );

  const { data: niches } = useNicheTaxonomy();
  const { data, isPending, isError, refetch, hasNextPage, isFetchingNextPage, fetchNextPage } =
    useVideoCorpus(filters);

  const flatVideos = useMemo(() => (data?.pages ?? []).flat() as CorpusRow[], [data?.pages]);

  const totalLabel = useMemo(() => {
    const n = flatVideos.length;
    if (n === 0 && !isPending) return "0";
    return hasNextPage ? `${n}+` : String(n);
  }, [flatVideos.length, hasNextPage, isPending]);

  const fetchNextPageStable = useCallback(() => {
    void fetchNextPage();
  }, [fetchNextPage]);

  useEffect(() => {
    const el = loaderRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPageStable();
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPageStable]);

  const { data: detail, isPending: detailLoading } = useVideoDetail(selectedVideoId);

  const nicheIdForRelated = detail?.niche_id ?? null;
  const { data: related } = useQuery({
    queryKey: corpusKeys.related(selectedVideoId ?? "", nicheIdForRelated ?? 0),
    queryFn: () => getRelatedVideos(selectedVideoId!, nicheIdForRelated!, 5),
    enabled: Boolean(selectedVideoId && nicheIdForRelated != null),
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    setMuted(true);
    const v = videoRef.current;
    if (v) v.muted = true;
  }, [selectedVideoId]);

  useEffect(() => {
    const v = videoRef.current;
    if (v) v.muted = muted;
  }, [muted]);

  const toggleMute = () => {
    setMuted((m) => !m);
  };

  return (
    <AppLayout active="explore" enableMobileSidebar>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-[var(--surface-alt)]">
        <header className="flex-shrink-0 border-b border-[var(--border)] bg-[var(--surface)] px-4 py-4 pl-14 lg:pl-6">
          <h1 className="text-lg font-extrabold text-[var(--ink)]">
            Khám phá <span className="font-mono text-[var(--faint)]">{totalLabel}</span> video
          </h1>
        </header>

        <div className="flex-1 overflow-y-auto px-4 pb-24 pt-4">
          {/* Niche chips */}
          <div className="mb-4 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <button
              type="button"
              onClick={() => setSelectedNicheId(null)}
              className={`min-h-[44px] flex-shrink-0 rounded-full px-4 text-sm font-semibold transition-colors duration-[120ms] ${
                selectedNicheId === null
                  ? "bg-[var(--purple)] text-white"
                  : "border border-[var(--border)] bg-[var(--surface)] text-[var(--ink-soft)]"
              }`}
            >
              Tất cả
            </button>
            {(niches ?? []).map((n) => (
              <button
                key={n.id}
                type="button"
                onClick={() => setSelectedNicheId(n.id)}
                className={`min-h-[44px] flex-shrink-0 rounded-full px-4 text-sm font-semibold transition-colors duration-[120ms] ${
                  selectedNicheId === n.id
                    ? "bg-[var(--purple)] text-white"
                    : "border border-[var(--border)] bg-[var(--surface)] text-[var(--ink-soft)]"
                }`}
              >
                {n.name}
              </button>
            ))}
          </div>

          {/* Sort + dates */}
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
            <label className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="text-xs font-medium text-[var(--muted)]">Sắp xếp</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortKey)}
                className="min-h-[44px] rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--ink)] outline-none focus:border-[var(--border-active)]"
              >
                {SORT_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-0 flex-col gap-1">
              <span className="text-xs font-medium text-[var(--muted)]">Từ ngày</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="min-h-[44px] rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--ink)]"
              />
            </label>
            <label className="flex min-w-0 flex-col gap-1">
              <span className="text-xs font-medium text-[var(--muted)]">Đến ngày</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="min-h-[44px] rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--ink)]"
              />
            </label>
          </div>

          {isPending ? <ExploreGridSkeleton /> : null}

          {isError ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-center">
              <p className="mb-4 text-sm text-[var(--ink)]">Không thể tải video — thử lại</p>
              <Button type="button" variant="secondary" onClick={() => void refetch()}>
                Thử lại
              </Button>
            </div>
          ) : null}

          {!isPending && !isError && flatVideos.length === 0 ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
              <p className="text-sm text-[var(--ink-soft)]">
                Không có video nào trong khoảng này — thử bỏ bộ lọc.
              </p>
            </div>
          ) : null}

          {!isPending && !isError && flatVideos.length > 0 ? (
            <div className="grid grid-cols-2 gap-3">
              {flatVideos.map((video) => (
                <button
                  key={video.id}
                  type="button"
                  onClick={() => setSelectedVideoId(video.id)}
                  className="group overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] text-left transition-shadow duration-[120ms] hover:border-[var(--border-active)] hover:shadow-sm"
                >
                  <img
                    src={video.thumbnail_url || PLACEHOLDER_THUMB}
                    alt={video.creator_handle ? `@${video.creator_handle}` : "Video"}
                    loading="lazy"
                    className="aspect-[9/16] w-full object-cover"
                  />
                  <div className="space-y-1 p-2">
                    <span className="block truncate text-xs font-semibold text-[var(--ink)]">
                      @{video.creator_handle ?? "—"}
                    </span>
                    <span className="block font-mono text-[11px] text-[var(--muted)]">
                      {formatViewsDisplay(video.views)} lượt xem
                    </span>
                    <span className="block font-mono text-[11px] text-[var(--muted)]">{erPercent(video.engagement_rate)} ER</span>
                  </div>
                </button>
              ))}
            </div>
          ) : null}

          <div ref={loaderRef} className="flex min-h-[48px] items-center justify-center py-4" aria-hidden>
            {isFetchingNextPage ? <Loader2 className="h-6 w-6 animate-spin text-[var(--purple)]" /> : null}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {selectedVideoId ? (
          <motion.div
            key="sheet"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex flex-col justify-end bg-black/40"
            role="presentation"
            onClick={() => setSelectedVideoId(null)}
          >
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ duration: 0.28, ease: [0.32, 0.72, 0, 1] }}
              className="max-h-[90vh] overflow-y-auto rounded-t-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-xl"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-label="Chi tiết video"
            >
              <div className="mb-3 flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => setSelectedVideoId(null)}
                  className="flex h-11 w-11 items-center justify-center rounded-lg text-[var(--ink-soft)] hover:bg-[var(--surface-alt)]"
                  aria-label="Đóng"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {detailLoading || !detail ? (
                <div className="space-y-3 animate-pulse py-4">
                  <div className="aspect-video w-full rounded-xl bg-[var(--border)]" />
                  <div className="h-4 w-1/2 rounded bg-[var(--border)]" />
                </div>
              ) : (
                <>
                  <div className="relative">
                    {detail.video_url ? (
                      <video
                        ref={videoRef}
                        src={detail.video_url}
                        muted={muted}
                        autoPlay
                        playsInline
                        controls
                        className="w-full rounded-xl"
                      />
                    ) : (
                      <img
                        src={detail.thumbnail_url || PLACEHOLDER_THUMB}
                        alt={detail.creator_handle ? `@${detail.creator_handle}` : "Video"}
                        className="w-full rounded-xl object-cover"
                        style={{ aspectRatio: "9/16", maxHeight: "60vh" }}
                      />
                    )}
                    {detail.video_url ? (
                      <button
                        type="button"
                        onClick={toggleMute}
                        className="absolute bottom-3 right-3 flex h-11 w-11 items-center justify-center rounded-full bg-black/50 text-white"
                        aria-label={muted ? "Bật tiếng" : "Tắt tiếng"}
                      >
                        {muted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
                      </button>
                    ) : null}
                  </div>

                  <div className="mt-4 space-y-1">
                    <p className="text-base font-bold text-[var(--ink)]">@{detail.creator_handle ?? "—"}</p>
                    <p className="font-mono text-sm text-[var(--muted)]">
                      {formatViewsDisplay(detail.views)} lượt xem · {erPercent(detail.engagement_rate)} ER
                    </p>
                    {detail.indexed_at ? (
                      <p className="font-mono text-xs text-[var(--faint)]">
                        Cập nhật kho: {formatDate(detail.indexed_at)}
                      </p>
                    ) : null}
                  </div>

                  <Button
                    type="button"
                    className="mt-4"
                    fullWidth
                    onClick={() => {
                      const url = detail.tiktok_url;
                      setSelectedVideoId(null);
                      navigate("/app", { state: url ? { prefillUrl: url } : undefined });
                    }}
                  >
                    Phân tích video này
                  </Button>

                  {related && related.length > 0 ? (
                    <div className="mt-6">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--faint)]">
                        Video liên quan
                      </p>
                      <div className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                        {related.map((r) => (
                          <button
                            key={r.id}
                            type="button"
                            onClick={() => setSelectedVideoId(r.id)}
                            className="w-20 flex-shrink-0 overflow-hidden rounded-lg border border-[var(--border)]"
                          >
                            <img
                              src={r.thumbnail_url || PLACEHOLDER_THUMB}
                              alt={r.creator_handle ? `@${r.creator_handle}` : ""}
                              loading="lazy"
                              className="aspect-[9/16] w-full object-cover"
                            />
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </AppLayout>
  );
}
