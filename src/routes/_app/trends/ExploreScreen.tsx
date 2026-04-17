import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  ChevronRight,
  Search,
  X,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { supabase } from "@/lib/supabase";
import { useVideoCorpus } from "@/hooks/useVideoCorpus";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useHookEffectiveness } from "@/hooks/useHookEffectiveness";
import { useFormatLifecycle } from "@/hooks/useFormatLifecycle";
import { useNicheIntelligence } from "@/hooks/useNicheIntelligence";
import { formatDate, formatViews } from "@/lib/formatters";
import { TrendingSection } from "@/components/explore/TrendingSection";
import { TrendingSoundsSection } from "@/components/explore/TrendingSoundsSection";
import { VideoDangHocSidebar } from "@/components/explore/VideoDangHocSidebar";
import { VideoPlayerModal, type ExploreGridVideo } from "@/components/explore/VideoPlayerModal";

const PLACEHOLDER_THUMB = "/placeholder.svg";

const SUGGESTED_FULL_DATA_NICHE_ID = 1;

type CorpusRow = {
  id: string;
  tiktok_url: string | null;
  video_url: string | null;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number | null;
  indexed_at: string | null;
  likes: number | null;
  shares: number | null;
  comments: number | null;
  hook_phrase: string | null;
  content_format: string | null;
  breakout_multiplier: number | null;
};


function corpusRowToExploreVideo(row: CorpusRow): ExploreGridVideo {
  const v = row.views ?? 0;
  return {
    id: row.id,
    views: v === 0 ? "—" : formatViews(v),
    time: row.indexed_at ? formatDate(row.indexed_at) : "—",
    img: row.thumbnail_url || PLACEHOLDER_THUMB,
    text: row.hook_phrase ?? "",
    handle: row.creator_handle ? `@${row.creator_handle}` : "@—",
    caption: row.hook_phrase || (row.creator_handle ? `Video @${row.creator_handle}` : "Video"),
    likes: row.likes != null ? formatViews(row.likes) : "—",
    comments: row.comments != null ? formatViews(row.comments) : "—",
    shares: row.shares != null ? formatViews(row.shares) : "—",
    videoUrl: row.video_url ?? "",
    tiktok_url: row.tiktok_url,
    breakout: row.breakout_multiplier != null
      ? `${row.breakout_multiplier.toFixed(1)}×`
      : null,
    contentFormat: row.content_format ?? null,
  };
}

/* --- Platform Icon SVGs ------------------------------------------ */
function TikTokIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path
        fill="#69C9D0"
        d="M10.06 13.28a2.89 2.89 0 0 0-2.89 2.89 2.89 2.89 0 0 0 2.89 2.89 2.89 2.89 0 0 0 2.88-2.5V2h3.45c.09.78.4 1.5.88 2.08a4.83 4.83 0 0 0 2.9 2.17v3.44a8.18 8.18 0 0 1-4.78-1.52v6.5a6.34 6.34 0 0 1-6.33 6.33 6.34 6.34 0 0 1-6.34-6.34 6.34 6.34 0 0 1 6.34-6.34c.27 0 .53.02.79.05v3.48a2.89 2.89 0 0 0-.79-.1z"
      />
      <path
        fill="#EE1D52"
        d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.18 8.18 0 0 0 4.78 1.52V6.76a4.85 4.85 0 0 1-1.01-.07z"
      />
      <path
        fill="#ffffff"
        d="M18.58 6.09a4.83 4.83 0 0 1-3.77-4.25V1.36h-3.45v13.31a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V7.97a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V7.9a8.18 8.18 0 0 0 4.78 1.52V6.05a4.85 4.85 0 0 1-1.01.04z"
      />
    </svg>
  );
}

function IGIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <defs>
        <linearGradient id="ig-grad" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#f09433" />
          <stop offset="25%" stopColor="#e6683c" />
          <stop offset="50%" stopColor="#dc2743" />
          <stop offset="75%" stopColor="#cc2366" />
          <stop offset="100%" stopColor="#bc1888" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5" fill="url(#ig-grad)" />
      <circle cx="12" cy="12" r="4.5" fill="none" stroke="white" strokeWidth="1.8" />
      <circle cx="17.5" cy="6.5" r="1.2" fill="white" />
    </svg>
  );
}

function YTIcon({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="1" y="5" width="22" height="14" rx="4" fill="#FF0000" />
      <polygon points="9.5,8.5 16,12 9.5,15.5" fill="white" />
    </svg>
  );
}



/* --- Video Thumbnail Card ----------------------------------------- */
function VideoCard({
  video,
  allVideos,
  onNavigate,
}: {
  video: ExploreGridVideo;
  allVideos: ExploreGridVideo[];
  onNavigate?: () => void;
}) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      {modalOpen && <VideoPlayerModal video={video} allVideos={allVideos} onClose={() => setModalOpen(false)} />}
      <div
        onClick={() => setModalOpen(true)}
        className="relative rounded-xl overflow-hidden bg-[var(--surface-alt)] border border-[var(--border)] cursor-pointer hover:border-[var(--border-active)] transition-colors duration-[120ms]"
        style={{ aspectRatio: "9/14" }}
      >
        <img src={video.img} alt="" className="w-full h-full object-cover" onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_THUMB; }} />
        {video.text && (
          <div className="absolute top-2 left-2 right-2">
            <p className="text-white text-[11px] font-semibold drop-shadow leading-snug line-clamp-2">{video.text}</p>
          </div>
        )}
        <div className="absolute bottom-0 inset-x-0 px-2 py-2 bg-gradient-to-t from-black/80 to-transparent flex flex-col gap-1.5">
          <div className="flex items-end justify-between w-full">
            <div className="flex items-center gap-1.5">
              <span className="text-white text-[11px] font-semibold">{video.views} views</span>
              {video.breakout ? (
                <span className="text-[10px] font-mono text-emerald-300">{video.breakout}</span>
              ) : null}
            </div>
            <span className="text-white/70 text-[10px]">{video.time}</span>
          </div>
          {onNavigate ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onNavigate();
              }}
              className="w-full min-h-[36px] rounded-md bg-white/20 py-1.5 text-center text-[10px] font-semibold text-white backdrop-blur-sm"
            >
              Phân tích video này
            </button>
          ) : null}
        </div>
      </div>
    </>
  );
}

/* --- Sidebar Video Row -------------------------------------------- */
function SidebarVideoRow({
  item,
  rank,
}: {
  item: { title: string; views: string; handle: string; time: string; img: string };
  rank?: number;
}) {
  return (
    <div className="flex items-start gap-2.5 py-2.5 border-b border-[var(--border)] last:border-0 cursor-pointer group">
      {rank !== undefined && (
        <span className="text-xs font-mono text-[var(--faint)] w-4 flex-shrink-0 pt-0.5 text-right">{rank}</span>
      )}
      <div className="w-9 h-12 flex-shrink-0 rounded-md overflow-hidden bg-[var(--surface-alt)] border border-[var(--border)]">
        <img src={item.img} alt="" className="w-full h-full object-cover" onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = PLACEHOLDER_THUMB; }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-semibold text-[var(--ink)] leading-snug line-clamp-2 group-hover:text-[var(--purple)] transition-colors duration-[120ms]">
          {item.title}
        </p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="text-[11px] font-mono font-semibold text-[var(--ink)]">{item.views}</span>
          <span className="text-[10px] text-[var(--muted)]">{item.handle}</span>
        </div>
        <span className="text-[10px] text-[var(--faint)]">{item.time}</span>
      </div>
    </div>
  );
}

/* --- Filter Chip -------------------------------------------------- */
function FilterChip({
  label,
  active = false,
  onRemove,
  onClick,
  hasArrow = false,
}: {
  label: string;
  active?: boolean;
  onRemove?: () => void;
  onClick?: () => void;
  hasArrow?: boolean;
}) {
  const baseClass = `flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border transition-all duration-[120ms] whitespace-nowrap ${
    active
      ? "border-[var(--ink)] text-[var(--ink)] bg-[var(--surface)]"
      : "border-[var(--border)] text-[var(--muted)] bg-[var(--surface)] hover:border-[var(--border-active)] hover:text-[var(--ink)]"
  }`;

  return (
    <button
      onClick={onClick}
      className={baseClass}
    >
      {label === "App" && (
        <span className="flex items-center mr-0.5">
          <TikTokIcon size={11} />
        </span>
      )}
      <span>{label}</span>
      {onRemove ? (
        <span
          role="button"
          aria-label="Xóa bộ lọc"
          tabIndex={0}
          className="flex items-center rounded-full hover:opacity-100 opacity-60"
          onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); onRemove(); }}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); onRemove(); } }}
        >
          <X className="w-3 h-3" strokeWidth={2} />
        </span>
      ) : hasArrow ? (
        <ChevronDown className="w-3 h-3 opacity-60" strokeWidth={2} />
      ) : null}
    </button>
  );
}

function ExploreGridSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--surface-alt)] animate-pulse"
          style={{ aspectRatio: "9/14" }}
        />
      ))}
    </div>
  );
}

/* --- ExploreScreen (Make TrendScreen + corpus) -------------------- */
type HookEffectivenessRow = {
  id?: string;
  hook_type: string;
  avg_engagement_rate: number | string | null;
  sample_size: number | null;
  computed_at: string | null;
};


type SortOption = "indexed_at" | "views" | "engagement_rate";

const SORT_LABELS: Record<SortOption, string> = {
  indexed_at: "Mới nhất",
  views: "Lượt xem",
  engagement_rate: "Tương tác",
};

const VIEW_FILTER_OPTIONS: { label: string; value: number }[] = [
  { label: "100K+", value: 100_000 },
  { label: "500K+", value: 500_000 },
  { label: "1M+",   value: 1_000_000 },
];

const TYPE_FORMAT_OPTIONS: { label: string; value: string }[] = [
  { label: "Tutorial",  value: "tutorial" },
  { label: "Review",    value: "review" },
  { label: "Haul",      value: "haul" },
  { label: "GRWM",      value: "grwm" },
  { label: "Vlog",      value: "vlog" },
  { label: "Trước/Sau", value: "before_after" },
  { label: "POV",       value: "pov" },
];

export default function ExploreScreen() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeViewFilter, setActiveViewFilter] = useState<number | null>(null);
  const [selectedNicheId, setSelectedNicheId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>("indexed_at");
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [activeFormat, setActiveFormat] = useState<string | null>(null);
  const [showFormatMenu, setShowFormatMenu] = useState(false);
  const formatMenuRef = useRef<HTMLDivElement>(null);
  const [showNicheMenu, setShowNicheMenu] = useState(false);
  const nicheMenuRef = useRef<HTMLDivElement>(null);
  const loaderRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const { data: profile } = useProfile();
  const { data: niches } = useNicheTaxonomy();
  const { data: hookDataRaw } = useHookEffectiveness(selectedNicheId);
  const { data: formatData } = useFormatLifecycle(selectedNicheId);
  const {
    data: nicheIntel,
    isPending: nicheIntelLoading,
    isError: nicheIntelQueryError,
  } = useNicheIntelligence(selectedNicheId);

  const hookData = hookDataRaw as HookEffectivenessRow[] | undefined;

  useEffect(() => {
    if (selectedNicheId !== null) return;
    const id = profile?.primary_niche;
    if (id != null) setSelectedNicheId(id);
  }, [profile?.primary_niche, selectedNicheId]);

  const selectedNicheName = useMemo(
    () => niches?.find((n) => n.id === selectedNicheId)?.name,
    [niches, selectedNicheId],
  );

  const risingFormats = useMemo(
    () => (formatData ?? []).filter((f) => (f.engagement_trend ?? 0) > 0).slice(0, 5),
    [formatData],
  );
  const fallingFormats = useMemo(
    () => (formatData ?? []).filter((f) => (f.engagement_trend ?? 0) <= 0).slice(0, 3),
    [formatData],
  );

  const { data: breakoutVideosRaw } = useQuery({
    queryKey: ["breakout_videos", selectedNicheId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("video_corpus")
        .select("id, creator_handle, views, thumbnail_url, content_type, indexed_at")
        .eq("niche_id", selectedNicheId!)
        .not("thumbnail_url", "is", null)
        .order("views", { ascending: false })
        .limit(10);
      if (error) throw error;
      return data ?? [];
    },
    enabled: !!selectedNicheId,
    staleTime: 10 * 60_000,
  });

  const breakoutSidebarItems = useMemo(() => {
    const rows = breakoutVideosRaw ?? [];
    return rows.map((r) => ({
      title: String(r.content_type ?? "").replace(/_/g, " ") || `@${r.creator_handle}`,
      views: r.views != null ? formatViews(r.views) : "—",
      handle: `@${r.creator_handle ?? ""}`,
      time: r.indexed_at ? formatDate(r.indexed_at) : "",
      img: r.thumbnail_url ?? PLACEHOLDER_THUMB,
    }));
  }, [breakoutVideosRaw]);

  const lowVideoCorpus = Boolean(
    selectedNicheId &&
      !nicheIntelLoading &&
      !nicheIntelQueryError &&
      (nicheIntel == null || (nicheIntel.video_count_7d ?? 0) < 10),
  );

  const newestComputedAt = hookData?.[0]?.computed_at ?? null;
  const staleTimestamp = nicheIntel?.computed_at ?? newestComputedAt;
  const hookDataStale =
    staleTimestamp != null && Date.now() - new Date(staleTimestamp).getTime() > 36 * 3600 * 1000;

  const totalHookSamples = useMemo(
    () => (hookData ?? []).reduce((s, h) => s + (h.sample_size ?? 0), 0),
    [hookData],
  );

  const asideUpdatedLabel = useMemo(() => {
    const t = nicheIntel?.computed_at;
    if (!t) return "—";
    const h = Math.round((Date.now() - new Date(t).getTime()) / 3600000);
    return `${h}h trước`;
  }, [nicheIntel?.computed_at]);

  const { data, isPending, isError, refetch, hasNextPage, isFetchingNextPage, fetchNextPage } = useVideoCorpus({
    nicheId: selectedNicheId,
    sortBy,
    sortOrder: "desc",
    search: searchQuery || undefined,
    minViews: activeViewFilter ?? undefined,
    contentFormat: activeFormat ?? undefined,
  });

  // Exact total count for the current filter combination (head-only, no rows fetched)
  const { data: corpusCount } = useQuery({
    queryKey: ["corpus_count", selectedNicheId, searchQuery, activeViewFilter, activeFormat],
    queryFn: async () => {
      let q = supabase
        .from("video_corpus")
        .select("*", { count: "exact", head: true });
      if (selectedNicheId != null) q = q.eq("niche_id", selectedNicheId);
      if (searchQuery?.trim()) q = q.textSearch("search_vector", searchQuery.trim(), { config: "simple", type: "plain" });
      if (activeViewFilter != null) q = q.gte("views", activeViewFilter);
      if (activeFormat != null) q = q.eq("content_format", activeFormat);
      const { count, error } = await q;
      if (error) return null;
      return count;
    },
    staleTime: 5 * 60_000,
  });

  const corpusRows = useMemo(() => (data?.pages ?? []).flat() as CorpusRow[], [data?.pages]);
  const videos = useMemo(() => corpusRows.map(corpusRowToExploreVideo), [corpusRows]);

  const exploreTitle = isPending
    ? "Khám phá video"
    : corpusCount != null
      ? `Khám phá ${corpusCount.toLocaleString("vi-VN")} video`
      : `Khám phá ${videos.length}${hasNextPage ? "+" : ""} video`;

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
  }, [hasNextPage, isFetchingNextPage, fetchNextPageStable, isPending, isError]);

  // Scroll the content column back to top whenever sort changes so the user
  // immediately sees page 0 of the new sort order instead of staying mid-list.
  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [sortBy]);

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [searchQuery]);

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [activeViewFilter]);

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [activeFormat]);

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [selectedNicheId]);

  useEffect(() => {
    if (!showFormatMenu) return;
    const handler = (e: MouseEvent) => {
      if (formatMenuRef.current && !formatMenuRef.current.contains(e.target as Node)) {
        setShowFormatMenu(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showFormatMenu]);

  useEffect(() => {
    if (!showNicheMenu) return;
    const handler = (e: MouseEvent) => {
      if (nicheMenuRef.current && !nicheMenuRef.current.contains(e.target as Node)) {
        setShowNicheMenu(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showNicheMenu]);

  return (
    <AppLayout active="trends" enableMobileSidebar>
      <div className="flex-1 overflow-hidden flex min-h-0">
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto min-w-0" style={{ scrollbarWidth: "thin" }}>
          {/* ── Zone 1: Discovery (always visible) ─────────────────────── */}
          <section className="px-5 lg:px-7 pt-14 lg:pt-2 pb-4">
            <TrendingSection nicheId={selectedNicheId} />
            <TrendingSoundsSection nicheId={selectedNicheId} />
            {selectedNicheId !== null && lowVideoCorpus ? (
              <p className="mb-4 text-xs text-[var(--muted)]">
                Niche này mới có {nicheIntel?.video_count_7d ?? 0} video 7 ngày — dữ liệu phân tích chưa đầy đủ.
              </p>
            ) : null}
          </section>

          <section className="px-5 lg:px-7 pb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-extrabold text-[var(--ink)]">{exploreTitle}</h2>
            </div>

            <div className="flex items-center gap-2 mb-4 flex-wrap">
              <div ref={nicheMenuRef} className="relative">
                <FilterChip
                  label={selectedNicheName ?? "Niche"}
                  hasArrow={selectedNicheId === null}
                  active={selectedNicheId !== null}
                  onRemove={selectedNicheId !== null ? () => { setSelectedNicheId(null); setShowNicheMenu(false); } : undefined}
                  onClick={() => setShowNicheMenu((v) => !v)}
                />
                {showNicheMenu ? (
                  <div className="absolute left-0 top-full z-20 mt-1 w-[200px] rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg max-h-[320px] overflow-y-auto">
                    {niches?.map((n) => (
                      <button
                        key={n.id}
                        type="button"
                        onClick={() => { setSelectedNicheId(n.id); setShowNicheMenu(false); }}
                        className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${selectedNicheId === n.id ? "font-semibold text-[var(--purple)]" : "text-[var(--ink)]"}`}
                      >
                        {n.name}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="flex-1 min-w-[200px] flex items-center gap-2 px-3 py-2 rounded-full border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-active)] transition-colors duration-[120ms]">
                <Search className="w-3.5 h-3.5 text-[var(--faint)] flex-shrink-0" strokeWidth={1.8} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 text-xs bg-transparent border-none outline-none text-[var(--ink)] placeholder:text-[var(--faint)]"
                  placeholder="Tim video..."
                />
              </div>
              <div className="relative">
                <FilterChip
                  label={SORT_LABELS[sortBy]}
                  hasArrow
                  active={sortBy !== "indexed_at"}
                  onRemove={sortBy !== "indexed_at" ? () => setSortBy("indexed_at") : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowSortMenu((v) => !v)}
                  className="absolute inset-0"
                  aria-label="Sắp xếp"
                />
                {showSortMenu ? (
                  <div className="absolute left-0 top-full z-20 mt-1 min-w-[140px] rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg">
                    {(["indexed_at", "views", "engagement_rate"] as SortOption[]).map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        onClick={() => { setSortBy(opt); setShowSortMenu(false); }}
                        className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${sortBy === opt ? "font-semibold text-[var(--purple)]" : "text-[var(--ink)]"}`}
                      >
                        {SORT_LABELS[opt]}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <div ref={formatMenuRef} className="relative">
                <FilterChip
                  label={activeFormat ? (TYPE_FORMAT_OPTIONS.find((o) => o.value === activeFormat)?.label ?? "Loại") : "Loại"}
                  hasArrow={!activeFormat}
                  active={activeFormat !== null}
                  onRemove={activeFormat !== null ? () => setActiveFormat(null) : undefined}
                  onClick={() => setShowFormatMenu((v) => !v)}
                />
                {showFormatMenu ? (
                  <div className="absolute left-0 top-full z-20 mt-1 min-w-[140px] rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg">
                    {TYPE_FORMAT_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => { setActiveFormat(opt.value); setShowFormatMenu(false); }}
                        className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${activeFormat === opt.value ? "font-semibold text-[var(--purple)]" : "text-[var(--ink)]"}`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="flex gap-1.5">
                {VIEW_FILTER_OPTIONS.map((opt) => (
                  <FilterChip
                    key={opt.label}
                    label={opt.label}
                    active={activeViewFilter === opt.value}
                    onRemove={activeViewFilter === opt.value ? () => setActiveViewFilter(null) : undefined}
                    onClick={activeViewFilter !== opt.value ? () => setActiveViewFilter(opt.value) : undefined}
                  />
                ))}
              </div>
            </div>

            {isPending ? <ExploreGridSkeleton /> : null}

            {isError ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-center">
                <p className="mb-4 text-sm text-[var(--ink)]">Không thể tải video — thử lại</p>
                <button
                  type="button"
                  onClick={() => void refetch()}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--border-active)] transition-colors duration-[120ms]"
                >
                  Thử lại
                </button>
              </div>
            ) : null}

            {!isPending && !isError && videos.length === 0 ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
                <p className="text-sm text-[var(--ink-soft)]">Chưa có video trong khoảng này — thử lại sau.</p>
              </div>
            ) : null}

            {!isPending && !isError && videos.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2.5">
                {videos.map((video, idx) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18, delay: idx * 0.04, ease: "easeOut" }}
                  >
                    <VideoCard
                      video={video}
                      allVideos={videos}
                      onNavigate={() =>
                        navigate("/app", {
                          state: video.tiktok_url ? { prefillUrl: video.tiktok_url } : undefined,
                        })
                      }
                    />
                  </motion.div>
                ))}
              </div>
            ) : null}

            {!isPending && !isError ? (
              <div ref={loaderRef} className="flex min-h-[48px] items-center justify-center py-4" aria-hidden>
                {isFetchingNextPage ? <Loader2 className="h-6 w-6 animate-spin text-[var(--purple)]" /> : null}
              </div>
            ) : null}
          </section>

          {/* ── Zone 2: Analytics (requires niche) ─────────────────────── */}
          <section className="px-5 lg:px-7 pb-8">
            {selectedNicheId === null ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-5 py-6 text-center">
                <p className="text-sm font-semibold text-[var(--ink)] mb-1">Phân tích chuyên sâu</p>
                <p className="text-xs text-[var(--muted)]">
                  Chọn niche từ bộ lọc để xem hook hiệu quả, format đang lên và phân tích corpus
                </p>
              </div>
            ) : (
              <>
                <VideoDangHocSidebar />

                {hookData && hookData.length > 0 && !lowVideoCorpus ? (
                  <section
                    key={`hook-ranking-${selectedNicheId}`}
                    className="mt-4 pt-4 border-t border-[var(--border)] -mx-5 lg:-mx-7 px-5 lg:px-7"
                  >
                    {hookDataStale ? (
                      <p className="text-xs font-medium text-[var(--ink-soft)] mb-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
                        Data cũ hơn 36 tiếng — đang cập nhật.
                      </p>
                    ) : null}
                    <h2 className="font-extrabold text-[var(--ink)] mb-3">
                      Hook đang chạy trong {selectedNicheName ?? "…"}
                    </h2>
                    <p className="text-xs text-[var(--faint)] mb-4">
                      {totalHookSamples} video · 7 ngày · Cập nhật{" "}
                      <span>
                        {newestComputedAt
                          ? `${Math.max(0, Math.round((Date.now() - new Date(newestComputedAt).getTime()) / 3600000))}h trước`
                          : "—"}
                      </span>
                    </p>
                    <div className="flex flex-col gap-2">
                      {hookData.slice(0, 8).map((h, i) => {
                        const maxEr = Number(hookData[0]?.avg_engagement_rate) || 1;
                        const er = Number(h.avg_engagement_rate) || 0;
                        const pct = Math.min(100, Math.round((er / maxEr) * 100));
                        const isTop = i === 0;
                        const mult = maxEr > 0 ? (er / maxEr).toFixed(2) : "—";
                        const barColor = isTop
                          ? "var(--purple)"
                          : `rgba(100, 100, 120, ${Math.max(0.10, 0.65 - i * 0.08)})`;
                        return (
                          <div key={h.id ?? i} className="flex flex-col gap-1">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-xs text-[var(--ink)] font-medium truncate max-w-[70%]">
                                {String(h.hook_type ?? "").replace(/_/g, " ")}
                              </span>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <span className="text-xs font-mono text-[var(--ink-soft)]">{(er * 100).toFixed(1)}%</span>
                                <motion.span
                                  className="text-[10px] font-semibold text-[var(--purple)] tabular-nums"
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  transition={{ duration: 0.25, delay: i * 0.1 + 0.35, ease: [0.16, 1, 0.3, 1] }}
                                >
                                  ×{mult}
                                </motion.span>
                              </div>
                            </div>
                            <div className="relative h-2 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                              <motion.div
                                className="absolute left-0 top-0 h-full rounded-full"
                                style={{ background: barColor }}
                                initial={{ width: 0 }}
                                animate={{ width: `${pct}%` }}
                                transition={{ duration: 0.4, delay: i * 0.1, ease: [0.16, 1, 0.3, 1] }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                ) : null}

                {(risingFormats.length > 0 || fallingFormats.length > 0) && !lowVideoCorpus ? (
                  <section className="mt-4 pt-4 border-t border-[var(--border)] -mx-5 lg:-mx-7 px-5 lg:px-7">
                    {risingFormats.length > 0 ? (
                      <>
                        <h2 className="font-extrabold text-[var(--ink)] mb-3">Format đang lên</h2>
                        <div className="flex flex-col gap-2">
                          {risingFormats.map((f, i) => (
                            <div key={f.id ?? `r-${i}`} className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0">
                              <span className="text-sm text-[var(--ink)]">{f.format_type}</span>
                              <span className="text-xs font-semibold" style={{ color: "var(--success, #22c55e)" }}>
                                +{((Number(f.engagement_trend) || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : null}
                    {fallingFormats.length > 0 ? (
                      <>
                        <h2 className={`font-extrabold text-[var(--ink)] mb-3 ${risingFormats.length > 0 ? "mt-4" : ""}`}>
                          Format đang giảm
                        </h2>
                        <div className="flex flex-col gap-2">
                          {fallingFormats.map((f, i) => (
                            <div key={f.id ?? `f-${i}`} className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0">
                              <span className="text-sm text-[var(--ink-soft)]">{f.format_type}</span>
                              <span className="text-xs font-semibold" style={{ color: "var(--danger, #ef4444)" }}>
                                {((Number(f.engagement_trend) || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : null}
                  </section>
                ) : null}
              </>
            )}
          </section>
        </div>

        <aside
          className="hidden lg:flex flex-col w-[290px] flex-shrink-0 border-l border-[var(--border)] bg-[var(--surface)] overflow-y-auto"
          style={{ scrollbarWidth: "thin" }}
        >
          <div className="px-4 pt-5 pb-3 border-b border-[var(--border)]">
            <button type="button" className="flex items-center gap-1 group">
              <h2 className="font-extrabold text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]">
                Video nên xem
              </h2>
              <ChevronRight
                className="w-4 h-4 text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]"
                strokeWidth={2.5}
              />
            </button>
            <p className="text-xs text-[var(--faint)] mt-0.5">Cập nhật {asideUpdatedLabel}</p>
          </div>

          <div className="flex-1 px-4 pb-6">
            <div className="mt-4 mb-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-orange-500 flex-shrink-0" />
                <span className="text-xs font-bold text-[var(--ink)]">Breakout tuần này</span>
              </div>
            </div>
            {breakoutSidebarItems.slice(0, 5).length > 0 ? (
              <div>
                {breakoutSidebarItems.slice(0, 5).map((item, idx) => (
                  <SidebarVideoRow key={`b-${idx}`} item={item} rank={idx + 1} />
                ))}
              </div>
            ) : (
              <div>
                <SidebarVideoRow
                  item={{
                    title: "Đang cập nhật…",
                    views: "—",
                    handle: "",
                    time: "",
                    img: PLACEHOLDER_THUMB,
                  }}
                />
              </div>
            )}

            <div className="mt-5 mb-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2 h-2 rounded-full bg-orange-500 flex-shrink-0" />
                <span className="text-xs font-bold text-[var(--ink)]">Đang viral</span>
              </div>
            </div>
            {breakoutSidebarItems.slice(5).length > 0 ? (
              <div>
                {breakoutSidebarItems.slice(5).map((item, idx) => (
                  <SidebarVideoRow key={`v-${idx}`} item={item} rank={idx + 6} />
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-[var(--faint)]">Chưa có video viral trong niche này.</p>
            )}
          </div>
        </aside>
      </div>
    </AppLayout>
  );
}
