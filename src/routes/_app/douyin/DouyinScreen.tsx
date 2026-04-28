import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft, Loader2 } from "lucide-react";

import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { TopBar } from "@/components/v2/TopBar";
import { DataFreshnessPill } from "@/components/v2/DataFreshnessPill";
import { useDouyinFeed } from "@/hooks/useDouyinFeed";
import { useDouyinPatterns } from "@/hooks/useDouyinPatterns";
import { useHomePulse } from "@/hooks/useHomePulse";
import { useProfile } from "@/hooks/useProfile";
import type { DouyinVideo } from "@/lib/api-types";

import { DouyinAutoNicheBanner } from "./DouyinAutoNicheBanner";
import { DouyinHero } from "./DouyinHero";
import { DouyinNicheChips } from "./DouyinNicheChips";
import { DouyinPatternsSection } from "./DouyinPatternsSection";
import { DouyinToolbar } from "./DouyinToolbar";
import { DouyinVideoCard } from "./DouyinVideoCard";
import { DouyinVideoModal } from "./DouyinVideoModal";
import {
  INITIAL_FILTERS,
  applyFiltersAndSort,
  hasAnyFilter,
  type DouyinFilters,
} from "./douyinFilters";
import { useDouyinSavedSet } from "./useDouyinSavedSet";
import { vnNicheToDouyinSlug } from "./vnNicheToDouyinSlug";

/**
 * D4b (2026-06-04) — Kho Douyin · main screen.
 * D4c (2026-06-04) — toolbar (search / adapt / sort / saved-only),
 *                    auto-niche banner from ``profiles.primary_niche``,
 *                    "Xoá bộ lọc" reset.
 *
 * Out of scope for D4c:
 *   • D4d — DouyinVideoModal (phone player + stats + adapt strip +
 *           translator notes + "Adapt sang VN → Kịch bản" CTA).
 *   • D5  — § I Pattern signals (3 cards / niche / week).
 */

export default function DouyinScreen() {
  const navigate = useNavigate();
  const { data, isPending, isError, refetch } = useDouyinFeed();
  const {
    data: patternsData,
    isPending: patternsPending,
    isError: patternsError,
    refetch: refetchPatterns,
  } = useDouyinPatterns();
  const { data: profile } = useProfile();
  const { data: pulse } = useHomePulse();
  const { has: isSaved, toggle: toggleSaved, set: savedIds, size: savedCount } =
    useDouyinSavedSet();

  // D4c — single source of truth for all filter UI controls.
  const [filters, setFilters] = useState<DouyinFilters>(INITIAL_FILTERS);
  // Auto-niche affordance dismissal — purely session-local. Once
  // dismissed, the banner stays hidden until the next mount; the niche
  // chip itself remains user-controlled.
  const [autoNicheDismissed, setAutoNicheDismissed] = useState(false);

  // D4d — currently-open video modal. ``null`` keeps the modal closed.
  const [modalVideo, setModalVideo] = useState<DouyinVideo | null>(null);

  const niches = data?.niches ?? [];
  const allVideos = data?.videos ?? [];

  // Slug → niche_id resolver, memoised so identity is stable across
  // renders and applyFiltersAndSort doesn't busy-loop the useMemo.
  const slugToNicheId = useMemo(() => {
    const map = new Map(niches.map((n) => [n.slug, n.id]));
    return (slug: string): number | null => map.get(slug) ?? null;
  }, [niches]);

  // Auto-niche heuristic: profile.primary_niche → Douyin slug, only if
  // that slug actually has videos in the corpus AND the user hasn't
  // touched the chip strip yet. We seed once on first feed-load.
  const autoSlug = useMemo(() => {
    const candidate = vnNicheToDouyinSlug(profile?.primary_niche ?? null);
    if (!candidate) return null;
    if (!niches.some((n) => n.slug === candidate)) return null;
    const niche = niches.find((n) => n.slug === candidate);
    if (!niche) return null;
    const hasVideos = allVideos.some((v) => v.niche_id === niche.id);
    return hasVideos ? candidate : null;
  }, [profile?.primary_niche, niches, allVideos]);

  // Seed the niche filter from the auto-slug exactly once after the
  // feed loads, while the user hasn't interacted yet (filters are
  // still pristine + banner not dismissed).
  useEffect(() => {
    if (
      autoSlug &&
      !autoNicheDismissed &&
      filters.nicheSlug === null &&
      !hasAnyFilter(filters)
    ) {
      setFilters((prev) => ({ ...prev, nicheSlug: autoSlug }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSlug]);

  // Hero stats — totals are scoped to the active niche so the
  // "VIDEO TRONG KHO" number tracks the chip filter.
  const activeNicheId = filters.nicheSlug
    ? slugToNicheId(filters.nicheSlug)
    : null;
  const heroStats = useMemo(() => {
    const pool =
      activeNicheId == null
        ? allVideos
        : allVideos.filter((v) => v.niche_id === activeNicheId);
    return {
      totalInPool: pool.length,
      greenCount: pool.filter((v) => v.adapt_level === "green").length,
    };
  }, [allVideos, activeNicheId]);

  const scopeLabel = useMemo(() => {
    if (!filters.nicheSlug) return null;
    const match = niches.find((n) => n.slug === filters.nicheSlug);
    return match?.name_vn?.toLowerCase() ?? null;
  }, [filters.nicheSlug, niches]);

  const visibleVideos = useMemo(
    () => applyFiltersAndSort(allVideos, filters, { slugToNicheId, savedIds }),
    [allVideos, filters, slugToNicheId, savedIds],
  );

  const showAutoBanner =
    autoSlug !== null &&
    !autoNicheDismissed &&
    filters.nicheSlug === autoSlug;
  const autoBannerLabel = useMemo(() => {
    if (!showAutoBanner) return null;
    return niches.find((n) => n.slug === autoSlug)?.name_vn ?? null;
  }, [showAutoBanner, autoSlug, niches]);

  const dismissAutoNiche = () => {
    setAutoNicheDismissed(true);
    setFilters((prev) => ({ ...prev, nicheSlug: null }));
  };

  const resetAllFilters = () => {
    setFilters(INITIAL_FILTERS);
    setAutoNicheDismissed(true);
  };

  const filtersActive = hasAnyFilter(filters);

  return (
    <AppLayout active="douyin" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="THAM CHIẾU"
          title="Kho Douyin"
          right={
            <>
              <DataFreshnessPill asOfIso={pulse?.as_of} />
              <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/trends")}>
                <ArrowLeft className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
                Về Xu hướng
              </Btn>
            </>
          }
        />

        <main className="mx-auto w-full max-w-[1400px] px-5 pb-20 pt-6 sm:px-7">
          <DouyinHero
            totalInPool={heroStats.totalInPool}
            greenCount={heroStats.greenCount}
            savedCount={savedCount}
            scopeLabel={scopeLabel}
          />

          <DouyinPatternsSection
            patterns={patternsData?.patterns ?? []}
            niches={niches}
            activeNicheSlug={filters.nicheSlug}
            isLoading={patternsPending}
            isError={patternsError}
            onRetry={() => void refetchPatterns()}
          />

          {/* §II header — kicker + count + Xoá bộ lọc */}
          <p className="gv-mono mb-1.5 text-[9px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
            § II — Kho video lẻ · Browse theo ngách
          </p>
          <div className="mb-3.5 flex items-baseline justify-between gap-3">
            <h2 className="gv-tight m-0 text-[22px] font-medium leading-tight text-[color:var(--gv-ink)]">
              {visibleVideos.length} video — đã sub VN
            </h2>
            {filtersActive ? (
              <button
                type="button"
                onClick={resetAllFilters}
                className="gv-mono shrink-0 text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)] underline-offset-4 hover:underline"
              >
                Xoá bộ lọc
              </button>
            ) : null}
          </div>

          {showAutoBanner && autoBannerLabel ? (
            <DouyinAutoNicheBanner
              nicheLabel={autoBannerLabel}
              matchCount={heroStats.totalInPool}
              onDismiss={dismissAutoNiche}
            />
          ) : null}

          <DouyinNicheChips
            niches={niches}
            activeSlug={filters.nicheSlug}
            onSelect={(nicheSlug) => {
              setAutoNicheDismissed(true);
              setFilters((prev) => ({ ...prev, nicheSlug }));
            }}
          />

          <DouyinToolbar
            filters={filters}
            onFiltersChange={setFilters}
            savedCount={savedCount}
          />

          {/* States — loading / error / empty / grid */}
          {isPending ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState onRetry={() => void refetch()} />
          ) : visibleVideos.length === 0 ? (
            <EmptyState onResetFilter={resetAllFilters} hasFilter={filtersActive} />
          ) : (
            <ul
              className="grid gap-4"
              style={{
                gridTemplateColumns:
                  "repeat(auto-fill, minmax(min(100%, 220px), 1fr))",
              }}
            >
              {visibleVideos.map((video) => (
                <li key={video.video_id} className="contents">
                  <DouyinVideoCard
                    video={video}
                    saved={isSaved(video.video_id)}
                    onToggleSave={toggleSaved}
                    onOpen={setModalVideo}
                  />
                </li>
              ))}
            </ul>
          )}
        </main>

        <DouyinVideoModal
          video={modalVideo}
          open={modalVideo !== null}
          onOpenChange={(next) => {
            if (!next) setModalVideo(null);
          }}
          saved={modalVideo ? isSaved(modalVideo.video_id) : false}
          onToggleSave={toggleSaved}
        />
      </div>
    </AppLayout>
  );
}


// ── Sub-states ──────────────────────────────────────────────────────


function LoadingState() {
  return (
    <div
      className="flex items-center justify-center rounded-lg border border-dashed border-[color:var(--gv-rule)] py-20 text-[color:var(--gv-ink-3)]"
      role="status"
      aria-label="Đang tải Kho Douyin"
    >
      <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={2} />
      <span className="text-sm">Đang tải video Douyin…</span>
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] py-12 text-center">
      <p className="gv-mono mb-2 text-[10px] uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
        Không tải được
      </p>
      <p className="mb-5 text-[14px] text-[color:var(--gv-ink-2)]">
        Thử lại sau ít phút — pipeline cập nhật mỗi 24h.
      </p>
      <Btn variant="ink" size="sm" type="button" onClick={onRetry}>
        Thử lại
      </Btn>
    </div>
  );
}

function EmptyState({
  onResetFilter,
  hasFilter,
}: {
  onResetFilter: () => void;
  hasFilter: boolean;
}) {
  return (
    <div className="rounded-lg border border-dashed border-[color:var(--gv-rule)] py-20 text-center">
      <p className="gv-mono mb-2 text-[11px] uppercase tracking-[0.06em] text-[color:var(--gv-ink-4)]">
        Không tìm thấy
      </p>
      <p className="mb-5 text-[14px] text-[color:var(--gv-ink-3)]">
        {hasFilter
          ? "Không có video nào khớp bộ lọc đang chọn."
          : "Chưa có video nào — quay lại sau khi cron đầu tiên chạy."}
      </p>
      {hasFilter ? (
        <Btn variant="ghost" size="sm" type="button" onClick={onResetFilter}>
          Xoá bộ lọc
        </Btn>
      ) : null}
    </div>
  );
}
