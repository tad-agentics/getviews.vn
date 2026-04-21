import { useState, useRef, useEffect, useCallback, useMemo, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import {
  ChevronRight,
  Search,
  X,
  ChevronDown,
  Loader2,
  LayoutGrid,
  List,
} from "lucide-react";
import { getISOWeek } from "date-fns";
import { AppLayout } from "@/components/AppLayout";
import { supabase } from "@/lib/supabase";
import { corpusKeys, useVideoCorpus } from "@/hooks/useVideoCorpus";
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

function topJsonbCounts(
  dist: unknown,
  limit: number,
): { key: string; count: number }[] {
  if (!dist || typeof dist !== "object" || Array.isArray(dist)) return [];
  const rec = dist as Record<string, unknown>;
  return Object.entries(rec)
    .map(([key, raw]) => {
      const n = typeof raw === "number" ? raw : Number(raw);
      return { key, count: Number.isFinite(n) ? n : 0 };
    })
    .filter((e) => e.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, limit);
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


/* --- Video Thumbnail Card (UIUX `trends.jsx` `VideoTile` parity) --- */
function VideoCard({
  video,
  allVideos,
  onNavigate,
  nicheLabel,
}: {
  video: ExploreGridVideo;
  allVideos: ExploreGridVideo[];
  onNavigate?: () => void;
  nicheLabel?: string;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);

  const cardLabel = video.text
    ? `Video ${video.handle}: ${video.text}`
    : `Video ${video.handle}`;

  const br = video.breakoutMultiplier;
  const showBreakout = br != null && br >= 1.5;
  const showViral = Boolean(video.isViral);

  return (
    <>
      {modalOpen && <VideoPlayerModal video={video} allVideos={allVideos} onClose={() => setModalOpen(false)} />}
      <div className="flex flex-col gap-2">
        <div
          role="button"
          tabIndex={0}
          aria-label={cardLabel}
          onClick={() => setModalOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setModalOpen(true);
            }
          }}
          className="relative overflow-hidden rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] cursor-pointer hover:border-[var(--gv-ink)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--gv-accent)] transition-colors duration-[120ms]"
          style={{ aspectRatio: "9/16" }}
        >
          {!imgFailed ? (
            <img
              src={video.img}
              alt=""
              loading="lazy"
              className="w-full h-full object-cover"
              onError={() => setImgFailed(true)}
            />
          ) : (
            <div className="w-full h-full bg-[var(--surface-alt)]" />
          )}
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent from-40% to-black/70" />
          {(showBreakout || showViral) && (
            <div className="absolute top-2 left-2 flex gap-1">
              {showBreakout ? (
                <span className="rounded px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-white bg-[var(--gv-accent)]">
                  BREAKOUT
                </span>
              ) : null}
              {showViral ? (
                <span className="rounded px-1.5 py-0.5 text-[9px] font-bold tracking-wide text-[var(--ink)] bg-[var(--gv-accent-2)]">
                  VIRAL
                </span>
              ) : null}
            </div>
          )}
          {video.durationLabel ? (
            <div className="absolute top-2 right-2 rounded bg-[var(--gv-scrim)] px-1.5 py-0.5 font-mono text-[10px] text-white">
              {video.durationLabel}
            </div>
          ) : null}
          <div className="absolute bottom-2 left-2.5 right-2.5 text-white">
            <p className="mb-0.5 font-mono text-[11px]">↑ {video.views}</p>
            <p className="line-clamp-2 text-xs font-medium leading-snug">{video.text || video.caption}</p>
          </div>
        </div>
        <div className="flex items-center justify-between gap-2 px-0.5">
          <span className="truncate font-mono text-[10px] text-[var(--gv-ink-3)]">{video.handle}</span>
          <span className="shrink-0 font-mono text-[10px] text-[var(--faint)]">{video.time}</span>
        </div>
        {onNavigate ? (
          <button
            type="button"
            onClick={() => onNavigate()}
            className="flex min-h-[44px] items-center justify-between rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-left text-[11px] text-[var(--gv-ink-3)] transition-colors duration-[120ms] hover:border-[var(--gv-ink)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--gv-accent)]"
          >
            <span>Phân tích →</span>
            <span className="max-w-[45%] truncate font-mono text-[10px] text-[var(--faint)]">
              {nicheLabel ?? video.contentFormat ?? "—"}
            </span>
          </button>
        ) : null}
      </div>
    </>
  );
}

/* --- Sidebar Video Row -------------------------------------------- */
function SidebarVideoRow({
  item,
  rank,
  onClick,
}: {
  item: {
    title: string;
    views: string;
    handle: string;
    time: string;
    img: string;
    video_id?: string;
  };
  rank?: number;
  onClick?: () => void;
}) {
  const [imgFailed, setImgFailed] = useState(false);

  const rowLabel = onClick ? `${item.title} — ${item.handle}, ${item.views} lượt xem` : undefined;

  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={rowLabel}
      onClick={onClick}
      onKeyDown={onClick ? (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      } : undefined}
      className={`flex items-start gap-2.5 py-2.5 border-b border-[var(--border)] last:border-0 group ${onClick ? "cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--gv-accent)]" : ""}`}
    >
      {rank !== undefined && (
        <span className="text-xs font-mono text-[var(--faint)] w-4 flex-shrink-0 pt-0.5 text-right">{rank}</span>
      )}
      <div className="w-9 h-12 flex-shrink-0 rounded-md overflow-hidden bg-[var(--surface-alt)] border border-[var(--border)]">
        {!imgFailed ? (
          <img
            src={item.img}
            alt=""
            loading="lazy"
            className="w-full h-full object-cover"
            onError={() => setImgFailed(true)}
          />
        ) : (
          <div className="w-full h-full bg-[var(--surface-alt)]" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-[12px] font-semibold text-[var(--ink)] leading-snug line-clamp-2 transition-colors duration-[120ms] ${onClick ? "group-hover:text-[var(--gv-accent)]" : ""}`}>
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
      : "border-[var(--border)] text-[var(--muted)] bg-[var(--surface)] hover:border-[var(--gv-ink)] hover:text-[var(--ink)]"
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
          className="flex items-center rounded-full hover:opacity-100 opacity-60"
          onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); }}
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
        >
          <X className="w-3 h-3" strokeWidth={2} />
        </button>
      ) : hasArrow ? (
        <ChevronDown className="w-3 h-3 opacity-60" strokeWidth={2} />
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
          className="overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-alt)]"
          style={{ aspectRatio: "9/16" }}
        />
      ))}
    </div>
  );
}

function RailBlock({
  kicker,
  title,
  children,
}: {
  kicker: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="mt-8 border-t border-[var(--border)] pt-6 first:mt-6 first:border-t-0 first:pt-0 min-[1100px]:first:mt-0">
      <p className="mb-1 font-mono text-[9px] font-medium uppercase tracking-wider text-[var(--faint)]">
        {kicker}
      </p>
      <h3 className="mb-3 border-b border-[var(--ink)] pb-2.5 text-[22px] font-extrabold leading-tight text-[var(--ink)]">
        {title}
      </h3>
      {children}
    </div>
  );
}

function HeroStatLine({
  label,
  value,
  delta,
}: {
  label: string;
  value: string;
  delta?: string;
}) {
  return (
    <div>
      <div className="mb-1 font-mono text-[9px] font-medium uppercase tracking-wider text-[var(--gv-ink-4)]">
        {label}
      </div>
      <div className="text-[28px] font-semibold leading-none text-[var(--surface)]">{value}</div>
      {delta ? (
        <div className="mt-1 font-mono text-[10px] text-[var(--gv-pos-deep)]">{delta}</div>
      ) : null}
    </div>
  );
}

function TrendsHeroCompact({
  nicheName,
  nicheIntel,
  corpusCount,
}: {
  nicheName: string | undefined;
  nicheIntel: Record<string, unknown> | null | undefined;
  corpusCount: number | null | undefined;
}) {
  if (!nicheIntel || !nicheName) return null;
  const sample = nicheCorpusSampleCount(nicheIntel);
  const head = corpusCount != null ? corpusCount.toLocaleString("vi-VN") : sample.toLocaleString("vi-VN");
  const commercePct = nicheIntel.commerce_pct;
  const medEr = nicheIntel.median_er;
  const pctCommerce =
    typeof commercePct === "number" && Number.isFinite(commercePct)
      ? `${commercePct.toFixed(0)}%`
      : "—";
  const erPct =
    typeof medEr === "number" && Number.isFinite(medEr)
      ? `${(medEr * 100).toFixed(1)}%`
      : "—";
  const topHooks = topJsonbCounts(nicheIntel.hook_distribution, 1);
  const topFormats = topJsonbCounts(nicheIntel.format_distribution, 1);
  const hookLine = topHooks[0]
    ? `Hook mạnh: ${String(topHooks[0].key).replace(/_/g, " ")}`
    : "Hook: đang cập nhật";
  const formatLine = topFormats[0]
    ? `Format dẫn: ${String(topFormats[0].key).replace(/_/g, " ")}`
    : "Format: đang cập nhật";

  return (
    <div
      className="mb-7 grid grid-cols-1 gap-5 rounded-[12px] bg-[var(--ink)] px-6 py-7 text-[var(--surface)] min-[1100px]:grid-cols-3 min-[1100px]:gap-8"
      aria-label="Tóm tắt tuần theo ngách"
    >
      <div>
        <p className="mb-2 font-mono text-[9px] font-medium uppercase tracking-wider text-[var(--gv-ink-4)]">
          {viWeekKicker()}
        </p>
        <p className="mb-2 text-[34px] font-semibold leading-none tracking-tight">
          {head}{" "}
          <span className="text-[var(--gv-accent)]">được giải mã</span>
        </p>
        <p className="max-w-sm text-xs leading-relaxed text-[var(--gv-ink-4)]">
          Dữ liệu 30 ngày gần nhất trong ngách {nicheName}. Cập nhật theo lô phân tích corpus.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 content-center">
        <HeroStatLine label="Video mẫu (30d)" value={sample.toLocaleString("vi-VN")} />
        <HeroStatLine label="TTTB (median ER)" value={erPct} />
        <HeroStatLine label="Video commerce" value={pctCommerce} />
        <HeroStatLine label="Hook nổi" value={topHooks[0] ? String(topHooks[0].count) : "—"} />
      </div>
      <div>
        <p className="mb-2 font-mono text-[9px] font-medium uppercase tracking-wider text-[var(--gv-ink-4)]">
          Tóm tắt biên tập
        </p>
        <p className="text-base font-medium leading-snug text-[var(--surface)]">
          {formatLine}. {hookLine}.
        </p>
      </div>
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
      <span className="hidden text-[11px] font-medium text-[var(--gv-pos-deep)] min-[900px]:block">Phân tích →</span>
    </button>
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

  // Profile → niche auto-seed. `?niche=0` in the URL encodes "user cleared
  // niche this session" and suppresses the seed. Any positive `?niche=N`
  // wins over profile.
  const selectedNicheId: number | null = nicheParam;

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

  // Auto-seed niche from profile on first load. Skip when the URL explicitly
  // carries `?niche=0` (user cleared this session) or already carries a
  // positive `?niche=N` (shared link / bookmark wins).
  useEffect(() => {
    if (nicheExplicitClear) return;
    if (selectedNicheId !== null) return;
    const id = profile?.primary_niche;
    if (id != null) setFilter({ niche: String(id) });
  }, [profile?.primary_niche, selectedNicheId, nicheExplicitClear, setFilter]);

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
    queryKey: corpusKeys.breakout(selectedNicheId),
    queryFn: async () => {
      const { data, error } = await supabase
        .from("video_corpus")
        .select("id, creator_handle, views, thumbnail_url, content_type, indexed_at, tiktok_url")
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
    return rows.map((r) => {
      const rawType = String(r.content_type ?? "").replace(/_/g, " ").trim();
      const title = rawType
        ? rawType.charAt(0).toUpperCase() + rawType.slice(1)
        : `@${r.creator_handle}`;
      return {
        video_id: r.id as string,
        title,
        views: r.views != null ? formatViews(r.views) : "—",
        handle: `@${r.creator_handle ?? ""}`,
        time: r.indexed_at ? formatDate(r.indexed_at) : "",
        img: r.thumbnail_url ?? PLACEHOLDER_THUMB,
        tiktok_url: r.tiktok_url ?? null,
      };
    });
  }, [breakoutVideosRaw]);

  const nicheIntelRecord = nicheIntel as Record<string, unknown> | null | undefined;

  const lowVideoCorpus = Boolean(
    selectedNicheId &&
      !nicheIntelLoading &&
      !nicheIntelQueryError &&
      (nicheIntel == null || nicheCorpusSampleCount(nicheIntelRecord) < 10),
  );

  const formatDistTop = useMemo(
    () => topJsonbCounts(nicheIntelRecord?.format_distribution, 6),
    [nicheIntelRecord],
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
    queryKey: corpusKeys.count({
      nicheId: selectedNicheId,
      search: searchQuery || undefined,
      minViews: activeViewFilter ?? undefined,
      contentFormat: activeFormat ?? undefined,
    }),
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
    scrollContainerRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [viewMode]);

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

  const hasPipelineFormats = risingFormats.length > 0 || fallingFormats.length > 0;

  return (
    <AppLayout active="trends" enableMobileSidebar>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden min-[1100px]:flex-row">
        <div ref={scrollContainerRef} className="min-h-0 min-w-0 flex-1 overflow-y-auto border-[var(--border)] min-[1100px]:border-r" style={{ scrollbarWidth: "thin" }}>
          {/* ── Zone 1: Discovery + hero (sounds → rail ≥1100px) ───────── */}
          <section className="px-7 pb-4 pt-14 md:pt-6">
            {selectedNicheId !== null && nicheIntel && !nicheIntelLoading && !nicheIntelQueryError ? (
              <TrendsHeroCompact
                nicheName={selectedNicheName}
                nicheIntel={nicheIntelRecord}
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

          <section className="px-7 pb-4">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <h2 className="tight text-[26px] font-extrabold leading-none tracking-tight text-[var(--ink)]">
                {exploreTitleBase}
                {exploreTitleCount != null ? (
                  <span className="ml-2 align-middle font-mono text-[13px] font-semibold text-[var(--faint)]">
                    {exploreTitleCount}
                  </span>
                ) : null}
              </h2>
            </div>

            <div className="mb-4 flex flex-wrap items-center gap-2">
              <div ref={nicheMenuRef} className="relative">
                <FilterChip
                  label={selectedNicheName ?? "Niche"}
                  hasArrow={selectedNicheId === null}
                  active={selectedNicheId !== null}
                  onRemove={selectedNicheId !== null ? () => { setFilter({ niche: "0" }); setShowNicheMenu(false); } : undefined}
                  onClick={() => setShowNicheMenu((v) => !v)}
                />
                {showNicheMenu ? (
                  <div className="absolute left-0 top-full z-20 mt-1 w-[200px] rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg max-h-[320px] overflow-y-auto">
                    {niches?.map((n) => (
                      <button
                        key={n.id}
                        type="button"
                        onClick={() => { setFilter({ niche: String(n.id) }); setShowNicheMenu(false); }}
                        className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${selectedNicheId === n.id ? "font-semibold text-[var(--gv-accent)]" : "text-[var(--ink)]"}`}
                      >
                        {n.name}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="flex min-h-[44px] min-w-[200px] flex-1 items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-2 transition-colors duration-[120ms] hover:border-[var(--gv-ink)] min-[768px]:w-[260px] min-[768px]:flex-none">
                <Search className="h-3.5 w-3.5 flex-shrink-0 text-[var(--faint)]" strokeWidth={1.8} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setFilter({ q: e.target.value || null })}
                  className="min-w-0 flex-1 border-none bg-transparent text-[16px] text-[var(--ink)] outline-none placeholder:text-[var(--faint)] md:text-xs"
                  placeholder="Tìm video, hook, creator…"
                  aria-label="Tìm video"
                />
              </div>
              <div className="relative">
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
                        onClick={() => { setFilter({ sort: opt === "indexed_at" ? null : opt }); setShowSortMenu(false); }}
                        className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${sortBy === opt ? "font-semibold text-[var(--gv-accent)]" : "text-[var(--ink)]"}`}
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
                  onRemove={activeFormat !== null ? () => setFilter({ format: null }) : undefined}
                  onClick={() => setShowFormatMenu((v) => !v)}
                />
                {showFormatMenu ? (
                  <div className="absolute left-0 top-full z-20 mt-1 min-w-[140px] rounded-xl border border-[var(--border)] bg-[var(--surface)] py-1 shadow-lg">
                    {TYPE_FORMAT_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => { setFilter({ format: opt.value }); setShowFormatMenu(false); }}
                        className={`w-full px-4 py-2 text-left text-xs transition-colors hover:bg-[var(--surface-alt)] ${activeFormat === opt.value ? "font-semibold text-[var(--gv-accent)]" : "text-[var(--ink)]"}`}
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
                    onRemove={activeViewFilter === opt.value ? () => setFilter({ min_views: null }) : undefined}
                    onClick={activeViewFilter !== opt.value ? () => setFilter({ min_views: String(opt.value) }) : undefined}
                  />
                ))}
              </div>
              <div
                className="ml-auto flex shrink-0 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] p-0.5"
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
                      allVideos={videos}
                      nicheLabel={selectedNicheName}
                      onNavigate={() =>
                        navigate(`/app/video?video_id=${encodeURIComponent(video.id)}`)
                      }
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
                    onNavigate={() =>
                      navigate(`/app/video?video_id=${encodeURIComponent(video.id)}`)
                    }
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

          {/* ── Zone 2: Analytics (requires niche) ─────────────────────── */}
          <section className="px-7 pb-15">
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
                    className="mt-4 pt-4 border-t border-[var(--border)] -mx-7 px-7"
                  >
                    {hookDataStale ? (
                      <p className="text-xs font-medium text-[var(--gv-ink-3)] mb-3 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
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
                        const fadeOpacity = isTop ? 1 : Math.max(0.28, 0.78 - i * 0.09);
                        return (
                          <div key={h.id ?? i} className="flex flex-col gap-1">
                            <div className="flex items-center justify-between gap-2">
                              <span className="max-w-[70%] truncate text-xs font-medium text-[var(--ink)]">
                                {String(h.hook_type ?? "").replace(/_/g, " ")}
                              </span>
                              <div className="flex flex-shrink-0 items-center gap-2">
                                <span className="font-mono text-xs text-[var(--gv-ink-3)]">{(er * 100).toFixed(1)}%</span>
                                <motion.span
                                  className="text-[10px] font-semibold tabular-nums text-[var(--gv-accent)]"
                                  initial={{ opacity: 0 }}
                                  animate={{ opacity: 1 }}
                                  transition={{ duration: 0.25, delay: i * 0.1 + 0.35, ease: [0.16, 1, 0.3, 1] }}
                                >
                                  ×{mult}
                                </motion.span>
                              </div>
                            </div>
                            <div className="relative h-2 overflow-hidden rounded-full bg-[var(--border)]">
                              <motion.div
                                className={`absolute left-0 top-0 h-full rounded-full ${isTop ? "bg-[var(--gv-accent)]" : "bg-[var(--gv-ink-3)]"}`}
                                style={isTop ? undefined : { opacity: fadeOpacity }}
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
              </>
            )}
          </section>
        </div>

        <aside
          className="flex w-full shrink-0 flex-col overflow-y-auto border-t border-[var(--border)] bg-[var(--surface)] min-[1100px]:w-[320px] min-[1100px]:border-l min-[1100px]:border-t-0"
          style={{ scrollbarWidth: "thin" }}
        >
          <div className="px-4 pt-5 pb-3 border-b border-[var(--border)]">
            <button type="button" className="flex items-center gap-1 group">
              <h2 className="font-extrabold text-[var(--ink)] group-hover:text-[var(--gv-accent)] transition-colors duration-[120ms]">
                Video nên xem
              </h2>
              <ChevronRight
                className="w-4 h-4 text-[var(--ink)] group-hover:text-[var(--gv-accent)] transition-colors duration-[120ms]"
                strokeWidth={2.5}
              />
            </button>
            <p className="text-xs text-[var(--faint)] mt-0.5">Cập nhật {asideUpdatedLabel}</p>
          </div>

          <div className="flex-1 px-4 pb-6">
            <div className="mt-4 mb-1">
              <div className="flex items-center gap-2 mb-1">
                <div className="h-2 w-2 shrink-0 rounded-full bg-[var(--gv-accent)]" />
                <span className="text-xs font-bold text-[var(--ink)]">Breakout tuần này</span>
              </div>
            </div>
            {breakoutSidebarItems.slice(0, 5).length > 0 ? (
              <div>
                {breakoutSidebarItems.slice(0, 5).map((item, idx) => (
                  <SidebarVideoRow
                    key={`b-${idx}`}
                    item={item}
                    rank={idx + 1}
                    onClick={
                      item.video_id
                        ? () => navigate(`/app/video?video_id=${encodeURIComponent(item.video_id)}`)
                        : undefined
                    }
                  />
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
                <div className="h-2 w-2 shrink-0 rounded-full bg-[var(--gv-accent)]" />
                <span className="text-xs font-bold text-[var(--ink)]">Đang viral</span>
              </div>
            </div>
            {breakoutSidebarItems.slice(5).length > 0 ? (
              <div>
                {breakoutSidebarItems.slice(5).map((item, idx) => (
                  <SidebarVideoRow
                    key={`v-${idx}`}
                    item={item}
                    rank={idx + 6}
                    onClick={
                      item.video_id
                        ? () => navigate(`/app/video?video_id=${encodeURIComponent(item.video_id)}`)
                        : undefined
                    }
                  />
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-[var(--faint)]">Chưa có video viral trong niche này.</p>
            )}

            <div className="hidden min-[1100px]:block">
              <RailBlock kicker="Âm thanh đang lên" title="Sounds">
                <TrendingSoundsSection nicheId={selectedNicheId} className="mb-0" />
              </RailBlock>
            </div>

            {selectedNicheId !== null ? (
              <RailBlock kicker="Hình thức hot" title="Format">
                {hasPipelineFormats && !lowVideoCorpus ? (
                  <>
                    {risingFormats.length > 0 ? (
                      <div className="mb-4 flex flex-col gap-0">
                        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                          Đang lên
                        </p>
                        {risingFormats.map((f, i) => (
                          <div
                            key={f.id ?? `rr-${i}`}
                            className="flex items-center justify-between border-b border-dashed border-[var(--border)] py-2.5 last:border-b-0"
                          >
                            <span className="text-sm text-[var(--ink)]">{f.format_type}</span>
                            <span className="text-xs font-semibold text-[var(--success)]">
                              +{((Number(f.engagement_trend) || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                    {fallingFormats.length > 0 ? (
                      <div className="flex flex-col gap-0">
                        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
                          Đang giảm
                        </p>
                        {fallingFormats.map((f, i) => (
                          <div
                            key={f.id ?? `fr-${i}`}
                            className="flex items-center justify-between border-b border-dashed border-[var(--border)] py-2.5 last:border-b-0"
                          >
                            <span className="text-sm text-[var(--gv-ink-3)]">{f.format_type}</span>
                            <span className="text-xs font-semibold text-[var(--danger)]">
                              {((Number(f.engagement_trend) || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </>
                ) : formatDistTop.length > 0 ? (
                  <div className="flex flex-col gap-0">
                    <p className="mb-2 text-xs text-[var(--muted)]">Top format trong mẫu 30 ngày</p>
                    {formatDistTop.map((row, i) => (
                      <div
                        key={row.key}
                        className="flex items-center justify-between border-b border-dashed border-[var(--border)] py-2.5 last:border-b-0"
                      >
                        <span className="text-sm capitalize text-[var(--ink)]">
                          {row.key.replace(/_/g, " ")}
                        </span>
                        <span className="font-mono text-xs text-[var(--gv-ink-3)]">{row.count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[var(--faint)]">Chưa có dữ liệu format cho ngách này.</p>
                )}
              </RailBlock>
            ) : null}
          </div>
        </aside>
      </div>
    </AppLayout>
  );
}
