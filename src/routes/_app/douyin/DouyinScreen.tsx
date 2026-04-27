import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ArrowLeft, Loader2 } from "lucide-react";

import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { TopBar } from "@/components/v2/TopBar";
import { useDouyinFeed } from "@/hooks/useDouyinFeed";

import { DouyinHero } from "./DouyinHero";
import { DouyinNicheChips } from "./DouyinNicheChips";
import { DouyinVideoCard } from "./DouyinVideoCard";
import { useDouyinSavedSet } from "./useDouyinSavedSet";

/**
 * D4b (2026-06-04) — Kho Douyin · main screen.
 *
 * Replaces the 70-line "Đang chuẩn bị" stub with the §II surface from
 * the design pack ``screens/douyin.jsx``: hero + niche chip strip +
 * 4-col responsive ``DouyinVideoCard`` grid + localStorage saved-set.
 *
 * Out of scope for D4b (next PRs):
 *   • D4c — toolbar (search + adapt-level filter + sort + saved-only),
 *           auto-niche banner, "Xoá bộ lọc" reset.
 *   • D4d — DouyinVideoModal (phone player + stats + adapt strip +
 *           translator notes + "Adapt sang VN → Kịch bản" CTA).
 *   • D5  — § I Pattern signals (3 cards / niche / week).
 *
 * Loading + empty states are first-class citizens here so D4c can
 * extend filter logic without rewiring the render tree.
 */

export default function DouyinScreen() {
  const navigate = useNavigate();
  const { data, isPending, isError, refetch } = useDouyinFeed();
  const { has: isSaved, toggle: toggleSaved, size: savedCount } = useDouyinSavedSet();

  // Active niche filter (slug or null="all"). D4c will widen this to a
  // full filter object — keep the state local for now.
  const [activeSlug, setActiveSlug] = useState<string | null>(null);

  const niches = data?.niches ?? [];
  const allVideos = data?.videos ?? [];

  // Active-slug → niche_id map for filtering. The chip strip emits
  // slugs (FE-stable), but the corpus rows carry numeric niche_id.
  const activeNicheId = useMemo(() => {
    if (!activeSlug) return null;
    const match = niches.find((n) => n.slug === activeSlug);
    return match?.id ?? null;
  }, [activeSlug, niches]);

  const visibleVideos = useMemo(() => {
    if (activeNicheId == null) return allVideos;
    return allVideos.filter((v) => v.niche_id === activeNicheId);
  }, [allVideos, activeNicheId]);

  // Hero stats — totals are scoped to the active niche so the
  // "VIDEO TRONG KHO" number tracks the chip filter.
  const heroStats = useMemo(() => {
    const pool = activeNicheId == null
      ? allVideos
      : allVideos.filter((v) => v.niche_id === activeNicheId);
    return {
      totalInPool: pool.length,
      greenCount: pool.filter((v) => v.adapt_level === "green").length,
    };
  }, [allVideos, activeNicheId]);

  const scopeLabel = useMemo(() => {
    if (!activeSlug) return null;
    const match = niches.find((n) => n.slug === activeSlug);
    return match?.name_vn?.toLowerCase() ?? null;
  }, [activeSlug, niches]);

  return (
    <AppLayout active="trends" enableMobileSidebar>
      <div className="min-h-full w-full bg-[color:var(--gv-canvas)] text-[color:var(--gv-ink)]">
        <TopBar
          kicker="THAM CHIẾU"
          title="Kho Douyin"
          right={
            <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/trends")}>
              <ArrowLeft className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
              Về Xu hướng
            </Btn>
          }
        />

        <main className="mx-auto w-full max-w-[1400px] px-5 pb-20 pt-6 sm:px-7">
          <DouyinHero
            totalInPool={heroStats.totalInPool}
            greenCount={heroStats.greenCount}
            savedCount={savedCount}
            scopeLabel={scopeLabel}
          />

          {/* §II header — kicker + count */}
          <p className="gv-mono mb-1.5 text-[9px] font-semibold uppercase tracking-[0.06em] text-[color:var(--gv-accent-deep)]">
            § II — Kho video lẻ · Browse theo ngách
          </p>
          <h2 className="gv-tight m-0 mb-3.5 text-[22px] font-medium leading-tight text-[color:var(--gv-ink)]">
            {visibleVideos.length} video — đã sub VN
          </h2>

          <DouyinNicheChips
            niches={niches}
            activeSlug={activeSlug}
            onSelect={setActiveSlug}
          />

          {/* States — loading / error / empty / grid */}
          {isPending ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState onRetry={() => void refetch()} />
          ) : visibleVideos.length === 0 ? (
            <EmptyState onResetFilter={() => setActiveSlug(null)} hasFilter={activeSlug !== null} />
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
                  />
                </li>
              ))}
            </ul>
          )}
        </main>
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
          ? "Không có video nào khớp ngách đang chọn."
          : "Chưa có video nào — quay lại sau khi cron đầu tiên chạy."}
      </p>
      {hasFilter ? (
        <Btn variant="ghost" size="sm" type="button" onClick={onResetFilter}>
          Xem tất cả ngách
        </Btn>
      ) : null}
    </div>
  );
}
