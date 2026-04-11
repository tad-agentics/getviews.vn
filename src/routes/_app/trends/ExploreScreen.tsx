import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronRight,
  Search,
  X,
  ChevronDown,
  VolumeX,
  Volume2,
  Heart,
  MessageCircle,
  Share2,
  Eye,
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
import { VideoDangHocSidebar } from "@/components/explore/VideoDangHocSidebar";

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
};

/** Shape expected by VideoCard / VideoPlayerModal (replaces Make exploreVideos items). */
type ExploreGridVideo = {
  id: string;
  views: string;
  time: string;
  img: string;
  text: string;
  handle: string;
  caption: string;
  likes: string;
  comments: string;
  shares: string;
  videoUrl: string;
  tiktok_url: string | null;
};

function corpusRowToExploreVideo(row: CorpusRow): ExploreGridVideo {
  const v = row.views ?? 0;
  return {
    id: row.id,
    views: v === 0 ? "—" : formatViews(v),
    time: row.indexed_at ? formatDate(row.indexed_at) : "—",
    img: row.thumbnail_url || PLACEHOLDER_THUMB,
    text: "",
    handle: row.creator_handle ? `@${row.creator_handle}` : "@—",
    caption: row.creator_handle ? `Video @${row.creator_handle}` : "Video",
    likes: row.likes != null ? formatViews(row.likes) : "—",
    comments: row.comments != null ? formatViews(row.comments) : "—",
    shares: row.shares != null ? formatViews(row.shares) : "—",
    videoUrl: row.video_url ?? "",
    tiktok_url: row.tiktok_url,
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

/* --- Shared VideoPlayerPanel --------------------------------------- */
function EngagementSidebar({
  img,
  likes,
  comments,
  shares,
  views,
}: {
  img: string;
  likes: string;
  comments: string;
  shares: string;
  views: string;
}) {
  return (
    <div className="hidden md:flex absolute right-3 bottom-24 z-20 flex-col items-center gap-4">
      <div className="w-9 h-9 rounded-full bg-[var(--surface)] border-2 border-white overflow-hidden">
        <img src={img} alt="" className="w-full h-full object-cover" />
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Heart className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{likes}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <MessageCircle className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{comments}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Share2 className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{shares}</span>
      </div>
      <div className="flex flex-col items-center gap-0.5">
        <Eye className="w-6 h-6 text-white" strokeWidth={2} />
        <span className="text-white text-[11px] font-semibold">{views}</span>
      </div>
    </div>
  );
}

/* --- Video Player Modal ------------------------------------------- */
function VideoPlayerModal({
  video,
  allVideos,
  onClose,
}: {
  video: ExploreGridVideo;
  allVideos: ExploreGridVideo[];
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(video);
  const [muted, setMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  }, [selected]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4"
        style={{ background: "rgba(0,0,0,0.65)", backdropFilter: "blur(8px)" }}
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 48 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 48 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className="relative flex flex-col md:flex-row bg-[var(--surface)] w-full md:rounded-2xl overflow-hidden"
          style={{
            maxWidth: 960,
            height: "95dvh",
            maxHeight: "95dvh",
            borderRadius: "20px 20px 0 0",
            boxShadow: "0 32px 80px rgba(0,0,0,0.4)",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="relative bg-black overflow-hidden order-1 md:order-2 md:flex-1" style={{ minHeight: "55%" }}>
            <video
              ref={videoRef}
              key={selected.videoUrl}
              src={selected.videoUrl}
              autoPlay
              loop
              playsInline
              muted={muted}
              className="absolute inset-0 w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20 pointer-events-none" />

            <button
              onClick={onClose}
              className="absolute top-3 right-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              <X className="w-4 h-4" strokeWidth={2} />
            </button>
            <button
              onClick={() => setMuted((v) => !v)}
              className="absolute top-3 left-3 z-20 w-9 h-9 flex items-center justify-center rounded-full bg-black/40 text-white hover:bg-black/60 transition-colors duration-[120ms] backdrop-blur-sm"
            >
              {muted ? <VolumeX className="w-4 h-4" strokeWidth={2} /> : <Volume2 className="w-4 h-4" strokeWidth={2} />}
            </button>

            <EngagementSidebar
              img={selected.img}
              likes={selected.likes}
              comments={selected.comments}
              shares={selected.shares}
              views={selected.views}
            />

            <div className="absolute bottom-0 inset-x-0 z-20 px-4 pb-4">
              <p className="text-white font-semibold text-sm mb-0.5">
                {selected.handle} · {selected.time}
              </p>
              <p className="text-white/85 text-xs leading-snug">{selected.caption}</p>
            </div>
          </div>

          <div
            className="order-2 md:order-1 flex flex-col md:w-[320px] md:flex-shrink-0 border-t md:border-t-0 md:border-r border-[var(--border)] bg-[var(--surface)] overflow-hidden"
            style={{ flex: "0 0 auto", maxHeight: "45%", minHeight: 0 }}
          >
            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] flex-shrink-0">
              <p className="text-[11px] font-bold uppercase tracking-widest text-[var(--faint)]">Kham pha video</p>
              <div className="flex md:hidden items-center gap-3">
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Heart className="w-3.5 h-3.5" strokeWidth={2} />
                  {selected.likes}
                </span>
                <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                  <Eye className="w-3.5 h-3.5" strokeWidth={2} />
                  {selected.views}
                </span>
              </div>
            </div>

            <div className="flex md:hidden flex-1 overflow-x-auto" style={{ scrollbarWidth: "none" }}>
              <div className="flex flex-row gap-2 px-3 py-2.5" style={{ width: "max-content" }}>
                {allVideos.map((v) => {
                  const isSel = v.id === selected.id;
                  return (
                    <button
                      key={v.id}
                      onClick={() => setSelected(v)}
                      className={`flex flex-col items-start gap-1 p-1.5 rounded-xl border transition-colors duration-[120ms] ${isSel ? "border-[var(--purple)] bg-[var(--purple-light)]" : "border-[var(--border)]"}`}
                      style={{ width: 80, flexShrink: 0 }}
                    >
                      <div className="w-full rounded-lg overflow-hidden relative" style={{ height: 100 }}>
                        <img src={v.img} alt="" className="w-full h-full object-cover" />
                        {isSel && (
                          <div className="absolute inset-0 bg-[var(--purple)]/20 flex items-center justify-center">
                            <div className="w-3 h-3 rounded-full bg-white/90" />
                          </div>
                        )}
                      </div>
                      {v.text && (
                        <p
                          className={`text-[10px] font-semibold leading-snug line-clamp-2 w-full text-left ${isSel ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}
                        >
                          {v.text}
                        </p>
                      )}
                      <p className="text-[10px] font-mono text-[var(--muted)]">{v.views}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="hidden md:block flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
              {allVideos.map((v) => {
                const isSel = v.id === selected.id;
                return (
                  <button
                    key={v.id}
                    onClick={() => setSelected(v)}
                    className={`w-full flex items-start gap-2.5 px-3 py-2.5 text-left transition-colors duration-[120ms] border-b border-[var(--border)] last:border-0 ${isSel ? "bg-[var(--purple-light)]" : "hover:bg-[var(--surface-alt)]"}`}
                  >
                    <div className="flex-shrink-0 rounded-md overflow-hidden border border-[var(--border)] relative" style={{ width: 36, height: 50 }}>
                      <img src={v.img} alt="" className="w-full h-full object-cover" />
                      {isSel && (
                        <div className="absolute inset-0 bg-[var(--purple)]/25 flex items-center justify-center">
                          <div className="w-2.5 h-2.5 rounded-full bg-white/90" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      {v.text && (
                        <p
                          className={`text-[11px] font-semibold leading-snug line-clamp-2 mb-0.5 ${isSel ? "text-[var(--purple)]" : "text-[var(--ink)]"}`}
                        >
                          {v.text}
                        </p>
                      )}
                      <p
                        className={`text-[11px] ${v.text ? "text-[var(--faint)]" : isSel ? "text-[var(--purple)] font-semibold" : "text-[var(--ink)] font-semibold"} leading-snug line-clamp-1`}
                      >
                        {v.handle}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[11px] font-mono font-semibold text-[var(--ink)]">{v.views}</span>
                        <span className="text-[10px] text-[var(--faint)]">{v.time}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
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
        <img src={video.img} alt="" className="w-full h-full object-cover" />
        {video.text && (
          <div className="absolute top-2 left-2 right-2">
            <p className="text-white text-[11px] font-semibold drop-shadow leading-snug line-clamp-2">{video.text}</p>
          </div>
        )}
        <div className="absolute bottom-0 inset-x-0 px-2 py-2 bg-gradient-to-t from-black/80 to-transparent flex flex-col gap-1.5">
          <div className="flex items-end justify-between w-full">
            <span className="text-white text-[11px] font-semibold">{video.views} views</span>
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
        <img src={item.img} alt="" className="w-full h-full object-cover" />
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
  hasArrow = false,
}: {
  label: string;
  active?: boolean;
  onRemove?: () => void;
  hasArrow?: boolean;
}) {
  return (
    <button
      className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border transition-all duration-[120ms] whitespace-nowrap ${
        active
          ? "border-[var(--ink)] text-[var(--ink)] bg-[var(--surface)]"
          : "border-[var(--border)] text-[var(--muted)] bg-[var(--surface)] hover:border-[var(--border-active)] hover:text-[var(--ink)]"
      }`}
    >
      {label === "App" && (
        <span className="flex items-center mr-0.5">
          <TikTokIcon size={11} />
        </span>
      )}
      <span>{label}</span>
      {onRemove ? (
        <X
          className="w-3 h-3 opacity-60"
          strokeWidth={2}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
        />
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

export default function ExploreScreen() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeViewFilter, setActiveViewFilter] = useState("100K+");
  const [selectedNicheId, setSelectedNicheId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>("indexed_at");
  const [showSortMenu, setShowSortMenu] = useState(false);
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
  });

  const corpusRows = useMemo(() => (data?.pages ?? []).flat() as CorpusRow[], [data?.pages]);
  const videos = useMemo(() => corpusRows.map(corpusRowToExploreVideo), [corpusRows]);

  const exploreTitle = isPending
    ? "Khám phá video"
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

  return (
    <AppLayout active="trends" enableMobileSidebar>
      <div className="flex-1 overflow-hidden flex min-h-0">
        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto min-w-0" style={{ scrollbarWidth: "thin" }}>
          <div
            className="overflow-x-auto px-5 lg:px-7 pt-14 lg:pt-6 pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            style={{ scrollbarWidth: "none" }}
          >
            <div className="flex gap-2" style={{ width: "max-content" }}>
              {niches?.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => setSelectedNicheId(n.id)}
                  className={`min-h-[44px] px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all duration-[120ms] ${
                    selectedNicheId === n.id
                      ? "bg-[var(--purple)] text-white"
                      : "bg-[var(--surface-alt)] text-[var(--ink-soft)] border border-[var(--border)] hover:border-[var(--border-active)]"
                  }`}
                >
                  {n.name}
                </button>
              ))}
            </div>
          </div>

          <section className="px-5 lg:px-7 pt-2 pb-4">
            {selectedNicheId !== null && lowVideoCorpus ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-center mb-4">
                <p className="text-sm text-[var(--ink)] mb-3">
                  Niche này mới có {nicheIntel?.video_count_7d ?? 0} video 7 ngày — chưa đủ để xu hướng. Thử niche Review đồ
                  Shopee / Gia dụng (data đầy đủ hơn).
                </p>
                <button
                  type="button"
                  onClick={() => setSelectedNicheId(SUGGESTED_FULL_DATA_NICHE_ID)}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--border-active)] transition-colors duration-[120ms]"
                >
                  Xem niche gợi ý
                </button>
              </div>
            ) : (
              <TrendingSection nicheId={selectedNicheId} />
            )}

            <VideoDangHocSidebar />

            {hookData && hookData.length > 0 && selectedNicheId && !lowVideoCorpus ? (
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
                    // D2: top bar = purple, others progressively lighter (0.65 → 0.10 opacity)
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
                              transition={{
                                duration: 0.25,
                                delay: i * 0.1 + 0.35,
                                ease: [0.16, 1, 0.3, 1],
                              }}
                            >
                              ×{mult}
                            </motion.span>
                          </div>
                        </div>
                        <div
                          className="relative h-2 rounded-full overflow-hidden"
                          style={{ background: "var(--border)" }}
                        >
                          <motion.div
                            className="absolute left-0 top-0 h-full rounded-full"
                            style={{ background: barColor }}
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            transition={{
                              duration: 0.4,
                              delay: i * 0.1,
                              ease: [0.16, 1, 0.3, 1],
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ) : null}

            {(risingFormats.length > 0 || fallingFormats.length > 0) && selectedNicheId && !lowVideoCorpus ? (
              <section className="mt-4 pt-4 border-t border-[var(--border)] -mx-5 lg:-mx-7 px-5 lg:px-7">
                {risingFormats.length > 0 ? (
                  <>
                    <h2 className="font-extrabold text-[var(--ink)] mb-3">Format đang lên</h2>
                    <div className="flex flex-col gap-2">
                      {risingFormats.map((f, i) => (
                        <div
                          key={f.id ?? `r-${i}`}
                          className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0"
                        >
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
                    <h2
                      className={`font-extrabold text-[var(--ink)] mb-3 ${risingFormats.length > 0 ? "mt-4" : ""}`}
                    >
                      Format đang giảm
                    </h2>
                    <div className="flex flex-col gap-2">
                      {fallingFormats.map((f, i) => (
                        <div
                          key={f.id ?? `f-${i}`}
                          className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0"
                        >
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
          </section>

          <section className="px-5 lg:px-7 pb-8">
            <button type="button" className="flex items-center gap-1 mb-4 group">
              <h2 className="font-extrabold text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]">{exploreTitle}</h2>
              <ChevronRight
                className="w-4 h-4 text-[var(--ink)] group-hover:text-[var(--purple)] transition-colors duration-[120ms]"
                strokeWidth={2.5}
              />
            </button>

            <div className="flex items-center gap-2 mb-4 flex-wrap">
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
              {activeViewFilter ? (
                <FilterChip label={activeViewFilter} active onRemove={() => setActiveViewFilter("")} />
              ) : null}
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
