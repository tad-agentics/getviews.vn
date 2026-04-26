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
import { useNicheRowsForIds } from "@/hooks/useTopNiches";
import { normalizeNicheIds } from "@/lib/profileNiches";
import { TrendsNicheTabs } from "./TrendsNicheTabs";
import { useHookEffectiveness } from "@/hooks/useHookEffectiveness";
import { useFormatLifecycle } from "@/hooks/useFormatLifecycle";
import { useNicheIntelligence } from "@/hooks/useNicheIntelligence";
import { formatDate, formatViews, formatVN, formatRelativeSinceVi } from "@/lib/formatters";
import { looksLikeNonVietnameseCaption } from "@/lib/nonVietnameseFilter";
import { TrendingSection } from "@/components/explore/TrendingSection";
import {
  TrendingSoundsSection,
  mondayWeekOfDateString,
} from "@/components/explore/TrendingSoundsSection";
import { VideoDangHocSidebar } from "@/components/explore/VideoDangHocSidebar";
import { type ExploreGridVideo } from "@/components/explore/VideoPlayerModal";

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
          <span>Phân tích →</span>
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

type RailCuratedItem = { tag: string; body: string; accent?: boolean };

/** Curated right rail (`trends.jsx` `RailSection`). */
function ReferenceRailSection({
  kicker,
  title,
  items,
}: {
  kicker: string;
  title: string;
  items: RailCuratedItem[];
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="mb-1 font-mono text-[9px] font-medium uppercase tracking-wider text-[var(--faint)]">
        {kicker}
      </p>
      <h3 className="mb-3 border-b border-[var(--ink)] pb-2.5 text-[22px] font-extrabold leading-tight text-[var(--ink)]">
        {title}
      </h3>
      <div className="flex flex-col gap-3.5">
        {items.map((it, i) => (
          <div
            key={`${it.tag}-${i}`}
            className={
              i < items.length - 1
                ? "border-b border-dashed border-[var(--border)] pb-3.5"
                : ""
            }
          >
            <div
              className={`mb-1 flex items-center gap-1.5 font-mono text-[9px] font-medium uppercase tracking-wider ${
                it.accent ? "text-[color:var(--gv-accent-deep)]" : "text-[var(--faint)]"
              }`}
            >
              {it.accent ? (
                <span
                  className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--gv-accent)] align-middle"
                  aria-hidden
                />
              ) : null}
              <span>{it.tag}</span>
            </div>
            <p className="text-sm leading-[1.35] text-[var(--gv-ink-2)]">{it.body}</p>
          </div>
        ))}
      </div>
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
      className="mb-7 grid grid-cols-1 gap-[18px] rounded-[12px] bg-[var(--ink)] px-5 py-6 text-[var(--surface)] sm:px-8 sm:py-7 min-[1100px]:grid-cols-3 min-[1100px]:gap-8"
      aria-label="Tóm tắt tuần theo ngách"
    >
      <div>
        <p className="mb-2 font-mono text-[9px] font-medium uppercase tracking-wider text-[var(--gv-ink-4)]">
          {viWeekKicker()}
        </p>
        <p className="mb-2 text-[26px] font-semibold leading-[1.1] tracking-tight text-balance min-[420px]:text-[30px] sm:text-[36px] sm:leading-none">
          {head}{" "}
          <span className="text-[var(--gv-accent)]">được giải mã</span>
        </p>
        <p className="max-w-[320px] text-xs leading-relaxed text-[var(--gv-ink-4)]">
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
        <p className="text-sm font-medium leading-snug text-[var(--surface)] sm:text-base">
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

  // PR-T1 — niche tab switcher. Source = profiles.niche_ids (cap 3
  // followed niches). Renders only when ≥2 followed; single-niche
  // profiles get no switcher.
  const followedNicheIds = useMemo(
    () => normalizeNicheIds(profile?.niche_ids ?? []),
    [profile?.niche_ids],
  );
  const { data: followedNiches = [] } = useNicheRowsForIds(followedNicheIds);

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
        .select("id, creator_handle, views, thumbnail_url, content_type, indexed_at, tiktok_url, hook_phrase")
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
      const hookSnippet = String((r as { hook_phrase?: string | null }).hook_phrase ?? "").trim();
      return {
        video_id: r.id as string,
        title,
        hook_snippet: hookSnippet,
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
  const trendsDataFreshLabel = useMemo(() => {
    if (!staleTimestamp) return null;
    const d = new Date(staleTimestamp);
    if (Number.isNaN(d.getTime())) return null;
    return formatRelativeSinceVi(new Date(), d);
  }, [staleTimestamp]);
  const hookDataStale =
    staleTimestamp != null && Date.now() - new Date(staleTimestamp).getTime() > 36 * 3600 * 1000;

  const totalHookSamples = useMemo(
    () => (hookData ?? []).reduce((s, h) => s + (h.sample_size ?? 0), 0),
    [hookData],
  );

  const weekStrSounds = useMemo(() => mondayWeekOfDateString(), []);

  const { data: soundsAllRows = [] } = useQuery({
    queryKey: ["trending_sounds_all", weekStrSounds],
    queryFn: async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (supabase as any)
        .from("trending_sounds")
        .select("sound_name, sound_id, usage_count, total_views, commerce_signal, niche_id")
        .eq("week_of", weekStrSounds)
        .order("usage_count", { ascending: false })
        .limit(200);
      if (error) throw error;
      return (data ?? []) as Array<{
        sound_name: string;
        sound_id: string | null;
        usage_count: number | null;
        total_views: number | null;
        commerce_signal: boolean | null;
        niche_id: number;
      }>;
    },
    staleTime: 30 * 60 * 1000,
  });

  const { data, isPending, isError, refetch, hasNextPage, isFetchingNextPage, fetchNextPage } = useVideoCorpus({
    nicheId: selectedNicheId,
    sortBy,
    sortOrder: "desc",
    search: searchQuery || undefined,
    minViews: activeViewFilter ?? undefined,
    contentFormat: activeFormat ?? undefined,
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

  const videoRailItems = useMemo((): RailCuratedItem[] => {
    const tags = ["Breakout tuần này", "Đang viral", "Đáng học"] as const;
    return breakoutSidebarItems.slice(0, 3).map((item, i) => {
      const hook = item.hook_snippet.trim();
      const snippet = hook.length > 72 ? `${hook.slice(0, 70)}…` : hook;
      const quote = snippet.length > 0 ? ` — "${snippet}"` : ` — ${item.title}`;
      const body = `${item.handle}${quote} · ${item.views} view`;
      return {
        tag: tags[i] ?? `Top ${i + 1}`,
        body,
        accent: i === 0,
      };
    });
  }, [breakoutSidebarItems]);

  const soundsRailItems = useMemo((): RailCuratedItem[] => {
    if (selectedNicheId == null) return [];
    return soundsAllRows
      .filter((r) => r.niche_id === selectedNicheId)
      .slice(0, 3)
      .map((r, i) => {
        const tag =
          r.sound_name.length > 28 ? `${r.sound_name.slice(0, 26)}…` : r.sound_name;
        const commerce = r.commerce_signal ? " · Commerce" : "";
        return {
          tag,
          body: `${formatVN(r.usage_count ?? 0)} video · ${formatVN(r.total_views ?? 0)} lượt xem${commerce}`,
          accent: i === 0,
        };
      });
  }, [soundsAllRows, selectedNicheId]);

  const formatRailItems = useMemo((): RailCuratedItem[] => {
    if (selectedNicheId == null) return [];
    if (hasPipelineFormats && !lowVideoCorpus && risingFormats.length > 0) {
      return risingFormats.slice(0, 3).map((f, i) => ({
        tag: String(f.format_type),
        body: `Xu hướng TTTB +${((Number(f.engagement_trend) || 0) * 100).toFixed(1)}% (pipeline format)`,
        accent: i === 0,
      }));
    }
    return formatDistTop.slice(0, 3).map((row, i) => ({
      tag: row.key.replace(/_/g, " "),
      body: `${row.count} video trong mẫu 30 ngày`,
      accent: i === 0,
    }));
  }, [
    selectedNicheId,
    hasPipelineFormats,
    lowVideoCorpus,
    risingFormats,
    formatDistTop,
  ]);

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
          {/* PR-T1 — NGÁCH BẠN THEO DÕI tab strip. Hidden when the
           * creator follows < 2 niches; the URL ``?niche=N`` already
           * pins the view in that case. */}
          <TrendsNicheTabs
            niches={followedNiches}
            selectedNicheId={selectedNicheId}
            onSelectNiche={(id) => setFilter({ niche: String(id) })}
            onEditNiches={() => navigate("/app/settings")}
          />
          {/* ── Zone 1: Discovery + hero (sounds carousel &lt;1100px) ───── */}
          <section className="pb-4">
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

          <section className="pb-4">
            <div className="mb-5 flex flex-col gap-4 min-[1100px]:flex-row min-[1100px]:items-center min-[1100px]:justify-between min-[1100px]:gap-4">
              <h2 className="text-[22px] font-extrabold leading-none tracking-tight text-[var(--ink)] sm:text-[26px] min-[1100px]:shrink-0">
                {exploreTitleBase}
                {exploreTitleCount != null ? (
                  <span className="ml-2 align-middle font-mono text-[13px] font-semibold text-[var(--faint)]">
                    {exploreTitleCount}
                  </span>
                ) : null}
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

                <div className="order-2 flex max-w-full items-center gap-2 overflow-x-auto overflow-y-hidden pb-0.5 [-webkit-overflow-scrolling:touch] [scrollbar-width:thin] min-[1100px]:contents min-[1100px]:overflow-visible">
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
                      onNavigate={() =>
                        navigate(`/app/video?video_id=${encodeURIComponent(video.video_id)}`)
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
                      navigate(`/app/video?video_id=${encodeURIComponent(video.video_id)}`)
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
          <section className="pb-15">
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
            className="flex w-full shrink-0 flex-col gap-6 border-t border-[var(--border)] bg-[var(--surface)] px-4 pb-[60px] pt-6 sm:px-7 min-[1100px]:w-[320px] min-[1100px]:overflow-y-auto min-[1100px]:border-l min-[1100px]:border-t-0 min-[1100px]:px-[22px] min-[1100px]:py-6 min-[1100px]:pb-6"
            style={{ scrollbarWidth: "thin" }}
          >
          <ReferenceRailSection
            kicker="VIDEO NÊN XEM"
            title="Hôm nay"
            items={
              selectedNicheId == null
                ? [
                    {
                      tag: "Chọn ngách",
                      body: "Chọn niche để xem các video nổi bật dạng gợi ý biên tập.",
                      accent: true,
                    },
                  ]
                : videoRailItems.length > 0
                  ? videoRailItems
                  : [
                      {
                        tag: "Đang cập nhật",
                        body: "Chưa có video nổi bật cho ngách này.",
                        accent: true,
                      },
                    ]
            }
          />
          <ReferenceRailSection
            kicker="ÂM THANH ĐANG LÊN"
            title="Sounds"
            items={
              selectedNicheId == null
                ? [
                    {
                      tag: "Chọn ngách",
                      body: "Chọn niche để xem âm thanh đang dùng nhiều trong tuần.",
                      accent: true,
                    },
                  ]
                : soundsRailItems.length > 0
                  ? soundsRailItems
                  : [
                      {
                        // BUG-12 (QA audit 2026-04-22): the empty state
                        // read "Đang cập nhật · Chưa có dữ liệu sounds
                        // cho tuần này." without an ETA. The sounds ETL
                        // runs every Tuesday morning (cron in
                        // supabase/functions/cron-sounds-refresh); telling
                        // the user when to come back converts the dead
                        // state into a scheduled one.
                        tag: "Cập nhật thứ Ba hàng tuần",
                        body: "Dữ liệu sounds cho tuần này chưa sẵn sàng — quay lại sau hoặc tham khảo tuần trước.",
                        accent: true,
                      },
                    ]
            }
          />
          {selectedNicheId !== null ? (
            <ReferenceRailSection
              kicker="HÌNH THỨC HOT"
              title="Format"
              items={
                formatRailItems.length > 0
                  ? formatRailItems
                  : [
                      {
                        tag: "Đang cập nhật",
                        body: "Chưa có dữ liệu format cho ngách này.",
                        accent: true,
                      },
                    ]
              }
            />
          ) : null}
          </aside>
        </div>
      </div>
    </AppLayout>
  );
}
