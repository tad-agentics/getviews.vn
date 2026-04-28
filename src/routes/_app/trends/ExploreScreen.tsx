import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  Search,
  X,
  ChevronDown,
  Loader2,
  LayoutGrid,
  List,
  Plus,
} from "lucide-react";
import { getISOWeek } from "date-fns";
import { AppLayout } from "@/components/AppLayout";
import { TopBar } from "@/components/v2/TopBar";
import { Btn } from "@/components/v2/Btn";
import { supabase } from "@/lib/supabase";
import { corpusKeys, useVideoCorpus } from "@/hooks/useVideoCorpus";
import { useProfile } from "@/hooks/useProfile";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { TrendsDouyinCard } from "./TrendsDouyinCard";
import { TrendsPatternGrid } from "./TrendsPatternGrid";
import { TrendsPatternThesisHero } from "./TrendsPatternThesisHero";
import { TrendsRail } from "./TrendsRail";
import { useNicheIntelligence } from "@/hooks/useNicheIntelligence";
import { formatDate, formatViews, formatRelativeSinceVi } from "@/lib/formatters";
import { looksLikeNonVietnameseCaption } from "@/lib/nonVietnameseFilter";
import { TrendingSection } from "@/components/explore/TrendingSection";
import {
  TrendingSoundsSection,
} from "@/components/explore/TrendingSoundsSection";
import { type ExploreGridVideo } from "@/components/explore/VideoPlayerModal";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { VideoThumbnail } from "@/components/VideoThumbnail";
import { tiktokAwemeIdForEmbed } from "@/lib/tiktokEmbed";

const PLACEHOLDER_THUMB = "/placeholder.svg";

type CorpusRow = {
  id: string;
  /** TikTok ``aweme_id`` — the value ``/app/video`` expects at ``?video_id=``. */
  video_id: string;
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
  tone: string | null;
  cta_type: string | null;
  is_commerce: boolean | null;
  sound_name: string | null;
  creator_tier: string | null;
  posting_hour: number | null;
  video_duration?: number | null;
};

function corpusMetadataChips(row: CorpusRow): string[] {
  const chips: string[] = [];
  if (row.is_commerce === true) chips.push("Mua bán");
  const tier = row.creator_tier?.trim();
  if (tier) chips.push(tier);
  const sound = row.sound_name?.trim();
  if (sound) chips.push(sound.length > 22 ? `${sound.slice(0, 20)}…` : sound);
  if (chips.length >= 3) return chips.slice(0, 3);
  const tone = row.tone?.trim();
  if (tone) chips.push(tone);
  if (chips.length >= 3) return chips.slice(0, 3);
  const cta = row.cta_type?.trim();
  if (cta) chips.push(cta);
  if (chips.length >= 3) return chips.slice(0, 3);
  if (
    row.posting_hour != null &&
    row.posting_hour >= 0 &&
    row.posting_hour <= 23
  ) {
    chips.push(`Đăng ${row.posting_hour}h`);
  }
  return chips.slice(0, 3);
}

function formatDurationSeconds(sec: number | null | undefined): string | null {
  if (sec == null || !Number.isFinite(sec) || sec <= 0) return null;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** `niche_intelligence` MV shape varies by migration; prefer `sample_size` when `video_count_7d` absent. */
function nicheCorpusSampleCount(intel: Record<string, unknown> | null | undefined): number {
  if (!intel || typeof intel !== "object") return 0;
  const v7 = intel.video_count_7d;
  if (typeof v7 === "number" && Number.isFinite(v7)) return v7;
  const ss = intel.sample_size;
  if (typeof ss === "number" && Number.isFinite(ss)) return ss;
  return 0;
}

function viWeekKicker(): string {
  const d = new Date();
  const w = getISOWeek(d);
  const start = new Date(d);
  const day = start.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  start.setDate(start.getDate() + diff);
  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  const fmt = new Intl.DateTimeFormat("vi-VN", { day: "numeric", month: "long" });
  return `TUẦN ${w} · ${fmt.format(start)}—${fmt.format(end)}`;
}

function corpusRowToExploreVideo(row: CorpusRow): ExploreGridVideo {
  const v = row.views ?? 0;
  const br = row.breakout_multiplier;
  const isViral = v >= 500_000 || (br != null && br >= 2.5);
  return {
    id: row.id,
    video_id: row.video_id,
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
    breakout: br != null ? `${br.toFixed(1)}×` : null,
    contentFormat: row.content_format ?? null,
    metadataChips: corpusMetadataChips(row),
    durationLabel: formatDurationSeconds(row.video_duration),
    isViral,
    breakoutMultiplier: br,
  };
}

function ExploreCorpusVideoModal({
  video,
  open,
  onOpenChange,
  onAnalyze,
}: {
  video: ExploreGridVideo | null;
  open: boolean;
  onOpenChange: (next: boolean) => void;
  onAnalyze: (v: ExploreGridVideo) => void;
}) {
  const embedId = video ? tiktokAwemeIdForEmbed(video.video_id, video.tiktok_url) : null;
  const thumbUrl =
    video && video.img && video.img !== PLACEHOLDER_THUMB ? video.img : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="!max-w-[min(420px,calc(100%-2rem))] gap-0 overflow-hidden border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] p-0"
      >
        {video ? (
          <>
            <header className="flex items-start justify-between gap-3 border-b border-[color:var(--gv-rule)] px-4 py-3 min-[420px]:px-5">
              <div className="min-w-0 flex-1">
                <DialogTitle className="gv-tight m-0 text-left text-[15px] font-semibold leading-snug text-[color:var(--gv-ink)]">
                  {video.text || video.caption}
                </DialogTitle>
                <p className="gv-mono mt-1 mb-0 text-[10px] text-[color:var(--gv-ink-4)]">
                  {video.handle} · ↑ {video.views}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                aria-label="Đóng"
                className="-mr-1 -mt-0.5 shrink-0 rounded-md p-2 text-[color:var(--gv-ink-3)] transition-colors hover:bg-[color:var(--gv-canvas-2)] hover:text-[color:var(--gv-ink)]"
              >
                <X className="h-4 w-4" strokeWidth={2} aria-hidden />
              </button>
            </header>
            <DialogDescription className="sr-only">
              Xem video TikTok trong nền tảng trước khi mở phân tích
            </DialogDescription>
            <div className="px-4 pb-4 pt-4 min-[420px]:px-5">
              {embedId ? (
                <div
                  className="relative mx-auto max-w-[280px] overflow-hidden rounded-[10px] bg-[color:var(--gv-canvas-2)]"
                  style={{ aspectRatio: "9 / 16" }}
                >
                  <iframe
                    key={embedId}
                    title={`TikTok video ${embedId}`}
                    src={`https://www.tiktok.com/embed/v2/${embedId}`}
                    className="absolute inset-0 h-full w-full border-0"
                    allow="encrypted-media; fullscreen; autoplay; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              ) : (
                <div
                  className="relative mx-auto max-w-[280px] overflow-hidden rounded-[10px] bg-[color:var(--gv-canvas-2)]"
                  style={{ aspectRatio: "9 / 16" }}
                >
                  <VideoThumbnail
                    thumbnailUrl={thumbUrl}
                    className="absolute inset-0 h-full w-full"
                    placeholderClassName=""
                  />
                  {video.tiktok_url ? (
                    <a
                      href={video.tiktok_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="gv-mono absolute bottom-3 left-1/2 z-10 -translate-x-1/2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-ink)] shadow-sm hover:border-[color:var(--gv-ink)]"
                    >
                      Mở trên TikTok
                    </a>
                  ) : null}
                </div>
              )}
            </div>
            <div className="border-t border-[color:var(--gv-rule)] px-4 py-4 min-[420px]:px-5">
              <Btn
                variant="accent"
                size="md"
                type="button"
                className="w-full justify-center"
                onClick={() => onAnalyze(video)}
              >
                Phân tích video này
              </Btn>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}


/* --- Video Thumbnail Card (UIUX `trends.jsx` `VideoTile`: one button, navigate) --- */
function VideoCard({
  video,
  onNavigate,
  nicheLabel,
}: {
  video: ExploreGridVideo;
  onNavigate?: () => void;
  nicheLabel?: string;
}) {
  const [imgFailed, setImgFailed] = useState(false);

  const cardLabel = video.text
    ? `Video ${video.handle}: ${video.text}`
    : `Video ${video.handle}`;

  const br = video.breakoutMultiplier;
  const showBreakout = br != null && br >= 1.5;
  const showViral = Boolean(video.isViral);

  return (
    <button
      type="button"
      aria-label={cardLabel}
      onClick={() => onNavigate?.()}
      className="flex w-full cursor-pointer flex-col gap-2 rounded-none border-0 bg-transparent p-0 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--gv-accent)]"
    >
      <div
        className="relative overflow-hidden rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] transition-colors duration-[120ms] hover:border-[var(--gv-ink)]"
        style={{ aspectRatio: "9/16" }}
      >
        {!imgFailed ? (
          <img
            src={video.img}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="h-full w-full bg-[var(--surface-alt)]" />
        )}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent from-40% to-black/70" />
        {(showBreakout || showViral) && (
          <div className="absolute top-2 left-2 flex gap-1">
            {showBreakout ? (
              <span className="rounded-[3px] px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-white bg-[var(--gv-accent)]">
                BREAKOUT
              </span>
            ) : null}
            {showViral ? (
              <span className="rounded-[3px] px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-[var(--ink)] bg-[var(--gv-accent-2)]">
                VIRAL
              </span>
            ) : null}
          </div>
        )}
        {video.durationLabel ? (
          <div className="absolute top-2 right-2 rounded-[3px] bg-black/50 px-1.5 py-0.5 font-mono text-[10px] text-white">
            {video.durationLabel}
          </div>
        ) : null}
        <div className="pointer-events-none absolute bottom-2 left-2.5 right-2.5 text-white">
          <p className="mb-0.5 font-mono text-[11px]">↑ {video.views}</p>
          <p className="line-clamp-2 text-[12px] font-medium leading-tight">{video.text || video.caption}</p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-2 px-0.5">
        <span className="truncate font-mono text-[10px] text-[var(--gv-ink-3)]">{video.handle}</span>
        <span className="shrink-0 font-mono text-[10px] text-[var(--faint)]">{video.time}</span>
      </div>
      {onNavigate ? (
        <div className="flex items-center justify-between rounded-md border border-[var(--border)] bg-[var(--surface-alt)] px-2.5 py-1.5 text-[11px] text-[var(--gv-ink-3)]">
          <span>Xem clip →</span>
          <span className="max-w-[45%] truncate font-mono text-[10px] text-[var(--faint)]">
            {nicheLabel ?? video.contentFormat ?? "—"}
          </span>
        </div>
      ) : null}
    </button>
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
  const baseClass = `flex items-center gap-1 rounded-full border px-3 py-1.5 text-[11px] font-medium transition-all duration-[120ms] whitespace-nowrap ${
    active
      ? "border-[var(--ink)] bg-[var(--ink)] text-[var(--surface)]"
      : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--gv-ink-2)] hover:border-[var(--gv-ink)] hover:text-[var(--ink)]"
  }`;

  return (
    <button
      type="button"
      onClick={onClick}
      className={baseClass}
    >
      <span>{label}</span>
      {onRemove ? (
        <button
          type="button"
          aria-label="Xóa bộ lọc"
          className={`flex items-center rounded-full opacity-60 hover:opacity-100 ${active ? "text-[var(--surface)]" : ""}`}
          onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); }}
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
        >
          <X className="w-3 h-3" strokeWidth={2} />
        </button>
      ) : hasArrow ? (
        <ChevronDown className={`w-3 h-3 opacity-60 ${active ? "text-[var(--surface)]" : ""}`} strokeWidth={2} />
      ) : null}
    </button>
  );
}

function ExploreGridSkeleton() {
  return (
    <div
      className="grid gap-3.5 animate-pulse"
      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))" }}
    >
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface-alt)]"
          style={{ aspectRatio: "9/16" }}
        />
      ))}
    </div>
  );
}

function ExploreVideoListRow({
  video,
  onNavigate,
  nicheLabel,
}: {
  video: ExploreGridVideo;
  onNavigate: () => void;
  nicheLabel?: string;
}) {
  const br = video.breakoutMultiplier;
  const showBreakout = br != null && br >= 1.5;
  const showViral = Boolean(video.isViral);
  return (
    <button
      type="button"
      onClick={onNavigate}
      className="flex w-full cursor-pointer items-center gap-3.5 border-b border-[var(--border)] px-4 py-3 text-left last:border-b-0 hover:bg-[var(--surface-alt)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--gv-accent)] min-[900px]:grid min-[900px]:grid-cols-[60px_1fr_100px_minmax(0,1fr)_72px_80px] min-[900px]:items-center"
    >
      <div className="h-16 w-[45px] shrink-0 overflow-hidden rounded bg-[var(--surface-alt)] min-[900px]:w-auto" style={{ aspectRatio: "9/16" }}>
        <img src={video.img} alt="" className="h-full w-full object-cover" loading="lazy" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-0.5 flex flex-wrap gap-1">
          {showBreakout ? (
            <span className="rounded bg-[var(--gv-accent)] px-1 py-0.5 text-[8px] font-bold tracking-wide text-white">
              BREAKOUT
            </span>
          ) : null}
          {showViral ? (
            <span className="rounded bg-[var(--gv-accent-2)] px-1 py-0.5 text-[8px] font-bold tracking-wide text-[var(--ink)]">
              VIRAL
            </span>
          ) : null}
        </div>
        <p className="truncate text-[13px] font-medium text-[var(--ink)]">{video.text || video.caption}</p>
        <p className="mt-0.5 truncate font-mono text-[10px] text-[var(--faint)]">
          {video.handle} · {nicheLabel ?? video.contentFormat ?? "—"}
        </p>
        <p className="mt-1 font-mono text-xs text-[var(--gv-ink-3)] min-[900px]:hidden">↑ {video.views}</p>
      </div>
      <span className="hidden font-mono text-xs text-[var(--gv-ink-3)] min-[900px]:block">↑ {video.views}</span>
      <p className="hidden min-w-0 truncate text-sm italic text-[var(--gv-ink-3)] min-[900px]:block">
        &ldquo;{video.text || "—"}&rdquo;
      </p>
      <span className="hidden font-mono text-[11px] text-[var(--faint)] min-[900px]:block">
        {video.durationLabel ?? "—"}
      </span>
      <span className="hidden text-[11px] font-medium text-[var(--gv-pos-deep)] min-[900px]:block">Xem clip →</span>
    </button>
  );
}

/* --- ExploreScreen (Make TrendScreen + corpus) -------------------- */
type SortOption = "indexed_at" | "views" | "engagement_rate";

const SORT_LABELS: Record<SortOption, string> = {
  indexed_at: "Mới nhất",
  views: "Lượt xem",
  engagement_rate: "Tương tác",
};

const SORT_VALUES: Set<string> = new Set(Object.keys(SORT_LABELS));

/** Parse a positive integer query-string value, returning null on anything
 *  non-numeric or ≤0. Used for `niche` + `min_views` URL params. */
function parsePositiveInt(raw: string | null): number | null {
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : null;
}

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
  const [searchParams, setSearchParams] = useSearchParams();

  // Filter state lives in the URL so bookmarks/back-nav/reload restore the
  // view, and filtered pages are shareable with a teammate. `setFilter`
  // below is the single write path — direct setState for these removed.
  const sortByParam = searchParams.get("sort");
  const sortBy: SortOption = sortByParam && SORT_VALUES.has(sortByParam)
    ? (sortByParam as SortOption)
    : "indexed_at";
  const activeFormat = searchParams.get("format");
  const activeViewFilter = parsePositiveInt(searchParams.get("min_views"));
  const searchQuery = searchParams.get("q") ?? "";
  const nicheParam = parsePositiveInt(searchParams.get("niche"));
  const nicheExplicitClear = searchParams.get("niche") === "0";
  const viewMode: "grid" | "list" = searchParams.get("view") === "list" ? "list" : "grid";
  // PR-T7 — date filter pills (Hôm nay / 7 ngày). Maps to ``dateFrom``
  // on ``useVideoCorpus`` (filtered against ``indexed_at``). Not in
  // ``SORT_VALUES`` style — only two valid values.
  const dateRange: "today" | "7d" | null = (() => {
    const v = searchParams.get("date");
    return v === "today" || v === "7d" ? v : null;
  })();

  const setFilter = useCallback(
    (patch: Record<string, string | null>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [k, v] of Object.entries(patch)) {
            if (v == null || v === "") next.delete(k);
            else next.set(k, v);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // Local UI state (dropdown open/closed etc.) stays in React — not worth
  // round-tripping through URL params.
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [showFormatMenu, setShowFormatMenu] = useState(false);
  const formatMenuRef = useRef<HTMLDivElement>(null);
  const [showNicheMenu, setShowNicheMenu] = useState(false);
  const nicheMenuRef = useRef<HTMLDivElement>(null);
  const loaderRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [corpusPreview, setCorpusPreview] = useState<ExploreGridVideo | null>(null);
  /** Defer open to the next task so the opening click's pointer-up cannot be treated as "outside" the portal content (Radix dismiss). */
  const openCorpusPreview = useCallback((video: ExploreGridVideo) => {
    window.setTimeout(() => setCorpusPreview(video), 0);
  }, []);

  // Profile → niche auto-seed. `?niche=0` in the URL encodes "user cleared
  // niche this session" and suppresses the seed. Any positive `?niche=N`
  // wins over profile.
  const selectedNicheId: number | null = nicheParam;

  const { data: profile } = useProfile();
  const { data: niches } = useNicheTaxonomy();

  const {
    data: nicheIntel,
    isPending: nicheIntelLoading,
    isError: nicheIntelQueryError,
  } = useNicheIntelligence(selectedNicheId);

  // Auto-seed niche from profile on first load. Skip when the URL explicitly
  // carries `?niche=0` (user cleared this session) or already carries a
  // positive `?niche=N` (shared link / bookmark wins).
  useEffect(() => {
    if (nicheExplicitClear) return;
    if (selectedNicheId !== null) return;
    const id = profile?.primary_niche;
    if (id != null) setFilter({ niche: String(id) });
  }, [profile?.primary_niche, selectedNicheId, nicheExplicitClear, setFilter]);

  // T5 (D7) — seed the 100K+ view filter on first mount when the URL
  // doesn't already carry a ``?min_views=`` param. Design pack
  // ``screens/trends.jsx`` line 1003 marks this chip as ``active`` by
  // default; the prior implementation only activated it when the URL
  // had the param, so a fresh visit showed all view counts.
  //
  // Once seeded, subsequent setFilter writes (including user-driven
  // chip clicks that clear it) carry an explicit ``min_views=`` token,
  // so this effect won't re-fire and re-seed.
  const [didSeedViewFilter, setDidSeedViewFilter] = useState(false);
  useEffect(() => {
    if (didSeedViewFilter) return;
    if (searchParams.has("min_views")) {
      setDidSeedViewFilter(true);
      return;
    }
    setFilter({ min_views: "100000" });
    setDidSeedViewFilter(true);
  }, [didSeedViewFilter, searchParams, setFilter]);

  const selectedNicheName = useMemo(
    () => niches?.find((n) => n.id === selectedNicheId)?.name,
    [niches, selectedNicheId],
  );

  const nicheIntelRecord = nicheIntel as Record<string, unknown> | null | undefined;

  const lowVideoCorpus = Boolean(
    selectedNicheId &&
      !nicheIntelLoading &&
      !nicheIntelQueryError &&
      (nicheIntel == null || nicheCorpusSampleCount(nicheIntelRecord) < 10),
  );

  const staleTimestamp = nicheIntel?.computed_at ?? null;
  const trendsDataFreshLabel = useMemo(() => {
    if (!staleTimestamp) return null;
    const d = new Date(staleTimestamp);
    if (Number.isNaN(d.getTime())) return null;
    return formatRelativeSinceVi(new Date(), d);
  }, [staleTimestamp]);

  // PR-T7 — translate ``dateRange`` URL param into a concrete
  // ``dateFrom`` ISO string. ``useVideoCorpus`` filters on
  // ``indexed_at`` (corpus ingest time) which is the closest proxy
  // we have for "recently posted" without a coordinated BE change.
  const dateFromIso = useMemo(() => {
    if (!dateRange) return undefined;
    const now = Date.now();
    const cutoffMs =
      dateRange === "today"
        ? new Date().setHours(0, 0, 0, 0)
        : now - 7 * 24 * 60 * 60 * 1000;
    return new Date(cutoffMs).toISOString();
  }, [dateRange]);

  const { data, isPending, isError, refetch, hasNextPage, isFetchingNextPage, fetchNextPage } = useVideoCorpus({
    nicheId: selectedNicheId,
    sortBy,
    sortOrder: "desc",
    search: searchQuery || undefined,
    minViews: activeViewFilter ?? undefined,
    contentFormat: activeFormat ?? undefined,
    dateFrom: dateFromIso,
  });

  // Estimated total count for the current filter combination (head-only, no rows fetched).
  // BUG-05 (QA audit 2026-04-22): ``count: "exact"`` forced PostgREST to run
  // a full ``SELECT count(*)`` with the filter applied, which on a 1K+-row
  // corpus with a textSearch filter planned a seq-scan and timed out →
  // 503 twice per page load. The trends chip only needs a rough "N kết
  // quả" — ``planned`` uses the planner estimate (fast, bounded memory)
  // and is plenty accurate for UI purposes.
  const { data: corpusCount } = useQuery({
    queryKey: corpusKeys.count({
      nicheId: selectedNicheId,
      search: searchQuery || undefined,
      minViews: activeViewFilter ?? undefined,
      contentFormat: activeFormat ?? undefined,
    }),
    queryFn: async () => {
      let q = supabase
        .from("video_corpus")
        .select("*", { count: "planned", head: true });
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
  // BUG-14 (QA audit 2026-04-22): all corpus rows are tagged ``language='vi'``
  // even when the caption is Han/Hangul ("沉浸式早八 淡颜韩系日常妆" showed up
  // in the Skincare feed). Until the analyse pipeline sets ``language``
  // correctly, drop any video whose caption is >25% CJK characters. The
  // heuristic is conservative — borderline bilingual captions still render.
  const videos = useMemo(() => {
    const mapped = corpusRows.map(corpusRowToExploreVideo);
    return mapped.filter((v) => {
      if (looksLikeNonVietnameseCaption(v.caption)) return false;
      if (looksLikeNonVietnameseCaption(v.text)) return false;
      return true;
    });
  }, [corpusRows]);

  const exploreTitleBase = "Khám phá";
  const exploreTitleCount = isPending
    ? null
    : corpusCount != null
      ? corpusCount.toLocaleString("vi-VN")
      : `${videos.length}${hasNextPage ? "+" : ""}`;

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

  // Scroll back to top whenever sort/search/filter/niche/view changes so the
  // user immediately sees page 0 of the new result set. On desktop (≥1100px)
  // ``scrollContainerRef`` is the actual scroll container; on mobile we walk
  // up the DOM to find the nearest ancestor that overflows (AppLayout's inner
  // ``overflow-y-auto`` wrapper), since this component's outer div is no
  // longer a scroll container below 1100px.
  const scrollResultsToTop = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    if (typeof getComputedStyle === "function" && getComputedStyle(el).overflowY === "auto") {
      el.scrollTo({ top: 0, behavior: "instant" });
      return;
    }
    let node: HTMLElement | null = el.parentElement;
    while (node) {
      const style = getComputedStyle(node);
      if ((style.overflowY === "auto" || style.overflowY === "scroll") && node.scrollHeight > node.clientHeight) {
        node.scrollTo({ top: 0, behavior: "instant" });
        return;
      }
      node = node.parentElement;
    }
    window.scrollTo({ top: 0, behavior: "instant" });
  }, []);

  useEffect(() => { scrollResultsToTop(); }, [sortBy, scrollResultsToTop]);
  useEffect(() => { scrollResultsToTop(); }, [searchQuery, scrollResultsToTop]);
  useEffect(() => { scrollResultsToTop(); }, [activeViewFilter, scrollResultsToTop]);
  useEffect(() => { scrollResultsToTop(); }, [activeFormat, scrollResultsToTop]);
  useEffect(() => { scrollResultsToTop(); }, [selectedNicheId, scrollResultsToTop]);
  useEffect(() => { scrollResultsToTop(); }, [viewMode, scrollResultsToTop]);
  useEffect(() => { scrollResultsToTop(); }, [dateRange, scrollResultsToTop]);

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
      <div className="flex min-h-0 w-full min-w-0 flex-1 flex-col bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="Báo cáo"
          title="Xu Hướng Tuần Này"
          right={
            <>
              <span className="hide-narrow hidden items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)] md:inline-flex">
                <span
                  className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--gv-accent)]"
                  style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
                />
                Dữ liệu cập nhật {trendsDataFreshLabel ?? "—"}
              </span>
              <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/answer")}>
                <Plus className="h-3.5 w-3.5" strokeWidth={2} />
                Phân tích mới
              </Btn>
            </>
          }
        />
        <div className="flex min-h-0 flex-1 flex-col min-[1100px]:grid min-[1100px]:grid-cols-[minmax(0,1fr)_320px] min-[1100px]:overflow-hidden">
          <div
            ref={scrollContainerRef}
            className="border-[var(--border)] px-4 pb-[60px] pt-4 sm:px-7 min-[1100px]:min-h-0 min-[1100px]:min-w-0 min-[1100px]:overflow-y-auto min-[1100px]:border-r min-[1100px]:pt-5"
            style={{ scrollbarWidth: "thin" }}
          >
          {/* ── Zone 1: Discovery + hero (sounds carousel &lt;1100px) ───── */}
          <section className="pb-4">
            {/* PR-T2 — pattern-thesis hero replaces the old niche-intel
             * snapshot. Renders when a niche is selected, regardless of
             * niche-intel query state — pattern stats + corpus count
             * are independent fetches. */}
            {selectedNicheId !== null && selectedNicheName ? (
              <TrendsPatternThesisHero
                nicheId={selectedNicheId}
                nicheLabel={selectedNicheName}
                weekKicker={viWeekKicker()}
                corpusCount={corpusCount}
              />
            ) : null}
            <TrendingSection nicheId={selectedNicheId} />
            <TrendingSoundsSection nicheId={selectedNicheId} className="mb-4 min-[1100px]:hidden" />
            {selectedNicheId !== null && lowVideoCorpus ? (
              <p className="mb-4 text-xs text-[var(--muted)]">
                Niche này mới có {nicheCorpusSampleCount(nicheIntelRecord)} video trong mẫu phân tích — dữ liệu chưa đầy đủ.
              </p>
            ) : null}
          </section>

          {/* PR-T5 — compact Kho Douyin link card. Visible on every
           * Trends view (regardless of selectedNicheId) so the
           * pre-VN-signal jump-off stays present even before the
           * creator has picked a niche. */}
          <TrendsDouyinCard />

          {/* PR-T3/T4 — § I PATTERN grid + click-to-open modal. Renders
           * the 6 hot patterns for the niche as 2×2-collage cards. */}
          {selectedNicheId !== null ? (
            <TrendsPatternGrid nicheId={selectedNicheId} />
          ) : null}

          <section className="pb-4">
            {/* PR-T7 — § II — KHO VIDEO header per design pack
             * ``screens/trends.jsx`` lines 419-427. The bold thesis
             * ("Tìm trong N video {niche}") shows when both a niche is
             * selected AND we have a corpus count; otherwise we fall
             * back to the original "Khám phá N" line so users without a
             * selected niche still see the count. */}
            <p className="gv-mono mb-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-ink-4)]">
              § II — KHO VIDEO
            </p>
            <div className="mb-5 flex flex-col gap-4 min-[1100px]:flex-row min-[1100px]:items-center min-[1100px]:justify-between min-[1100px]:gap-4">
              <h2 className="gv-tight m-0 text-[clamp(22px,2.5vw,28px)] font-semibold tracking-[-0.02em] text-[color:var(--gv-ink)] min-[1100px]:shrink-0">
                {selectedNicheName && exploreTitleCount != null ? (
                  <>
                    Tìm trong{" "}
                    <span className="gv-mono text-[14px] font-medium text-[color:var(--gv-ink-4)]">
                      {exploreTitleCount}
                    </span>{" "}
                    video {selectedNicheName.toLowerCase()}
                  </>
                ) : (
                  <>
                    {exploreTitleBase}
                    {exploreTitleCount != null ? (
                      <span className="ml-2 align-middle font-mono text-[13px] font-semibold text-[var(--faint)]">
                        {exploreTitleCount}
                      </span>
                    ) : null}
                  </>
                )}
              </h2>

              <div className="flex min-w-0 w-full flex-col gap-3 min-[1100px]:max-w-[calc(100%-220px)] min-[1100px]:flex-1 min-[1100px]:flex-row min-[1100px]:flex-wrap min-[1100px]:items-center min-[1100px]:justify-end min-[1100px]:gap-2">
                <div className="order-1 w-full min-w-0 min-[1100px]:order-2 min-[1100px]:w-[260px] min-[1100px]:shrink-0">
                  <div className="flex h-8 w-full items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 transition-colors duration-[120ms] hover:border-[var(--gv-ink)]">
                    <Search className="h-3 w-3 shrink-0 text-[var(--faint)]" strokeWidth={1.8} />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setFilter({ q: e.target.value || null })}
                      className="min-h-0 min-w-0 flex-1 border-none bg-transparent py-0 text-[11px] font-medium leading-none text-[var(--ink)] outline-none placeholder:text-[var(--faint)] placeholder:font-medium"
                      placeholder="Tìm video, hook, creator…"
                      aria-label="Tìm video"
                    />
                  </div>
                </div>

                <div
                  className="order-2 w-full min-w-0 overflow-x-auto overflow-y-hidden overscroll-x-contain pb-1 [-webkit-overflow-scrolling:touch] [scrollbar-width:thin] [-ms-overflow-style:auto] -mx-4 px-4 sm:-mx-7 sm:px-7 min-[1100px]:mx-0 min-[1100px]:contents min-[1100px]:overflow-visible min-[1100px]:px-0 min-[1100px]:pb-0"
                  role="toolbar"
                  aria-label="Bộ lọc kho video"
                >
                  <div className="flex w-max max-w-none flex-nowrap items-center gap-2 min-[1100px]:contents">
                  <div ref={nicheMenuRef} className="relative shrink-0 min-[1100px]:order-1">
                    <FilterChip
                      label={selectedNicheName ?? "Niche"}
                      hasArrow={selectedNicheId === null}
                      active={selectedNicheId !== null}
                      onRemove={
                        selectedNicheId !== null
                          ? () => {
                              setFilter({ niche: "0" });
                              setShowNicheMenu(false);
                            }
                          : undefined
                      }
                      onClick={() => setShowNicheMenu((v) => !v)}
                    />
                    {showNicheMenu ? (
                      <div className="absolute left-0 top-full z-20 mt-1 max-h-[320px] w-[200px] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg">
                        {niches?.map((n) => (
                          <button
                            key={n.id}
                            type="button"
                            onClick={() => {
                              setFilter({ niche: String(n.id) });
                              setShowNicheMenu(false);
                            }}
                            className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${selectedNicheId === n.id ? "font-semibold text-[var(--gv-accent)]" : "text-[var(--ink)]"}`}
                          >
                            {n.name}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div className="relative shrink-0 min-[1100px]:order-3">
                    <FilterChip
                      label={SORT_LABELS[sortBy]}
                      hasArrow
                      active={sortBy !== "indexed_at"}
                      onRemove={sortBy !== "indexed_at" ? () => setFilter({ sort: null }) : undefined}
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
                            onClick={() => {
                              setFilter({ sort: opt === "indexed_at" ? null : opt });
                              setShowSortMenu(false);
                            }}
                            className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${sortBy === opt ? "font-semibold text-[var(--gv-accent)]" : "text-[var(--ink)]"}`}
                          >
                            {SORT_LABELS[opt]}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div ref={formatMenuRef} className="relative shrink-0 min-[1100px]:order-4">
                    <FilterChip
                      label={
                        activeFormat
                          ? (TYPE_FORMAT_OPTIONS.find((o) => o.value === activeFormat)?.label ?? "Loại")
                          : "Loại"
                      }
                      hasArrow={!activeFormat}
                      active={activeFormat !== null}
                      onRemove={activeFormat !== null ? () => setFilter({ format: null }) : undefined}
                      onClick={() => setShowFormatMenu((v) => !v)}
                    />
                    {showFormatMenu ? (
                      <div className="absolute left-0 top-full z-20 mt-1 min-w-[140px] rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg">
                        {TYPE_FORMAT_OPTIONS.map((opt) => (
                          <button
                            key={opt.value}
                            type="button"
                            onClick={() => {
                              setFilter({ format: opt.value });
                              setShowFormatMenu(false);
                            }}
                            className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${activeFormat === opt.value ? "font-semibold text-[var(--gv-accent)]" : "text-[var(--ink)]"}`}
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 gap-1.5 min-[1100px]:order-5">
                    {VIEW_FILTER_OPTIONS.map((opt) => (
                      <FilterChip
                        key={opt.label}
                        label={opt.label}
                        active={activeViewFilter === opt.value}
                        onRemove={activeViewFilter === opt.value ? () => setFilter({ min_views: null }) : undefined}
                        onClick={activeViewFilter !== opt.value ? () => setFilter({ min_views: String(opt.value) }) : undefined}
                      />
                    ))}
                  </div>
                  {/* PR-T7 — date filter pills (Hôm nay / 7 ngày). Map
                   * to ``dateFrom`` on ``useVideoCorpus`` (filtered
                   * against ``indexed_at``). */}
                  <div className="flex shrink-0 gap-1.5 min-[1100px]:order-5">
                    <FilterChip
                      label="Hôm nay"
                      active={dateRange === "today"}
                      onRemove={dateRange === "today" ? () => setFilter({ date: null }) : undefined}
                      onClick={dateRange !== "today" ? () => setFilter({ date: "today" }) : undefined}
                    />
                    <FilterChip
                      label="7 ngày"
                      active={dateRange === "7d"}
                      onRemove={dateRange === "7d" ? () => setFilter({ date: null }) : undefined}
                      onClick={dateRange !== "7d" ? () => setFilter({ date: "7d" }) : undefined}
                    />
                  </div>
                  <div
                    className="flex shrink-0 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] p-0.5 min-[1100px]:order-6"
                    role="group"
                    aria-label="Chế độ xem"
                  >
                    <button
                      type="button"
                      aria-pressed={viewMode === "grid"}
                      onClick={() => setFilter({ view: null })}
                      className={`flex h-6 w-7 items-center justify-center rounded-full transition-colors ${viewMode === "grid" ? "bg-[var(--ink)] text-[var(--surface)]" : "text-[var(--gv-ink-3)]"}`}
                      aria-label="Lưới"
                    >
                      <LayoutGrid className="h-3 w-3" strokeWidth={2} />
                    </button>
                    <button
                      type="button"
                      aria-pressed={viewMode === "list"}
                      onClick={() => setFilter({ view: "list" })}
                      className={`flex h-6 w-7 items-center justify-center rounded-full transition-colors ${viewMode === "list" ? "bg-[var(--ink)] text-[var(--surface)]" : "text-[var(--gv-ink-3)]"}`}
                      aria-label="Danh sách"
                    >
                      <List className="h-3 w-3" strokeWidth={2} />
                    </button>
                  </div>
                  </div>
                </div>
              </div>
            </div>

            {isPending ? <ExploreGridSkeleton /> : null}

            {isError ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-center">
                <p className="mb-4 text-sm text-[var(--ink)]">Không thể tải video — thử lại</p>
                <button
                  type="button"
                  onClick={() => void refetch()}
                  className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-xs font-semibold text-[var(--ink)] hover:border-[var(--gv-ink)] transition-colors duration-[120ms]"
                >
                  Thử lại
                </button>
              </div>
            ) : null}

            {!isPending && !isError && videos.length === 0 ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
                <p className="text-sm text-[var(--gv-ink-3)]">Chưa có video trong khoảng này — thử lại sau.</p>
              </div>
            ) : null}

            {!isPending && !isError && videos.length > 0 && viewMode === "grid" ? (
              <div
                className="grid gap-3.5"
                style={{ gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))" }}
              >
                {videos.map((video, idx) => (
                  <motion.div
                    key={video.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.18, delay: Math.min(idx * 0.04, 0.3), ease: "easeOut" }}
                  >
                    <VideoCard
                      video={video}
                      nicheLabel={selectedNicheName}
                      onNavigate={() => openCorpusPreview(video)}
                    />
                  </motion.div>
                ))}
              </div>
            ) : null}

            {!isPending && !isError && videos.length > 0 && viewMode === "list" ? (
              <div className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)]">
                {videos.map((video) => (
                  <ExploreVideoListRow
                    key={video.id}
                    video={video}
                    nicheLabel={selectedNicheName}
                    onNavigate={() => openCorpusPreview(video)}
                  />
                ))}
              </div>
            ) : null}

            {!isPending && !isError ? (
              <div ref={loaderRef} className="flex min-h-[48px] items-center justify-center py-4" aria-hidden>
                {isFetchingNextPage ? <Loader2 className="h-6 w-6 animate-spin text-[var(--gv-accent)]" /> : null}
              </div>
            ) : null}
          </section>

          {/* ── Zone 2: CTA khi chưa chọn niche (đã gỡ bảng hook hiệu quả) ─ */}
          {selectedNicheId === null ? (
            <section className="pb-15">
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-5 py-6 text-center">
                <p className="text-sm font-semibold text-[var(--ink)] mb-1">Phân tích chuyên sâu</p>
                <p className="text-xs text-[var(--muted)]">
                  Chọn niche từ bộ lọc để xem pattern, kho video và bảng xếp hạng bên phải
                </p>
              </div>
            </section>
          ) : null}
          </div>

          {/* PR-T6 — right rail: 2 sections (Đang nổi lên / Viral mọi
           * thời) per design pack ``screens/trends.jsx`` lines 432-446.
           * Sounds + Format rails were removed — sounds carousel still
           * surfaces below the hero on < 1100px via the existing
           * TrendingSoundsSection. */}
          <aside
            className="w-full shrink-0 border-t border-[var(--border)] bg-[var(--surface)] px-4 pb-[60px] pt-6 sm:px-7 min-[1100px]:w-[320px] min-[1100px]:overflow-y-auto min-[1100px]:border-l min-[1100px]:border-t-0 min-[1100px]:px-[22px] min-[1100px]:py-6 min-[1100px]:pb-6"
            style={{ scrollbarWidth: "thin" }}
          >
            <TrendsRail nicheId={selectedNicheId} />
          </aside>
        </div>
        <ExploreCorpusVideoModal
          video={corpusPreview}
          open={corpusPreview != null}
          onOpenChange={(next) => {
            if (!next) setCorpusPreview(null);
          }}
          onAnalyze={(v) => {
            setCorpusPreview(null);
            navigate(`/app/video?video_id=${encodeURIComponent(v.video_id)}`);
          }}
        />
      </div>
    </AppLayout>
  );
}
