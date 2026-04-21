import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { Bookmark, ChevronLeft, ChevronRight, Loader2, Plus, Search, Sparkles } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { Chip } from "@/components/v2/Chip";
import { FilterChipRow } from "@/components/v2/FilterChipRow";
import { KolStickyDetailCard } from "@/components/v2/KolStickyDetailCard";
import { MatchScoreBar } from "@/components/v2/MatchScoreBar";
import { SortableCreatorsTable, type KolSortDir, type KolSortKey } from "@/components/v2/SortableCreatorsTable";
import { TopBar } from "@/components/v2/TopBar";
import { env } from "@/lib/env";
import { formatRelativeSinceVi } from "@/lib/formatters";
import { logUsage } from "@/lib/logUsage";
import type { KolBrowseRow, KolBrowseTab } from "@/lib/api-types";
import { useAuth } from "@/lib/auth";
import {
  defaultKolOrderDir,
  parseKolApiSort,
  parseKolFollowerPreset,
  parseKolOrderDir,
  type KolApiSort,
  type KolFollowerPreset,
  type KolOrderDir,
  useKolBrowse,
  useKolDiscoverTotal,
  useKolTogglePin,
  normalizeKolSearchInput,
} from "@/hooks/useKolBrowse";
import { useNicheTaxonomy } from "@/hooks/useNicheTaxonomy";
import { useProfile } from "@/hooks/useProfile";

function parseTab(raw: string | null): KolBrowseTab {
  return raw === "pinned" || raw === "discover" ? raw : "discover";
}

function parsePage(raw: string | null): number {
  const n = Number.parseInt(raw ?? "1", 10);
  return Number.isFinite(n) && n >= 1 ? n : 1;
}

const FOLLOWER_PRESETS: ReadonlyArray<{ id: KolFollowerPreset; label: string }> = [
  { id: "10k-100k", label: "10K–100K" },
  { id: "100k-1m", label: "100K–1M" },
  { id: "1m-5m", label: "1M–5M" },
];

function apiSortToUiKey(tab: KolBrowseTab, api: KolApiSort): KolSortKey {
  if (api === "pinned" || api === "rank") return "idx";
  if (api === "name") return "name";
  if (api === "followers") return "followers";
  if (api === "avg_views") return "avg_views";
  if (api === "growth") return "growth";
  return "match";
}

function uiKeyToApiSort(tab: KolBrowseTab, key: KolSortKey): KolApiSort {
  if (key === "idx") return tab === "pinned" ? "pinned" : "rank";
  if (key === "name") return "name";
  if (key === "followers") return "followers";
  if (key === "avg_views") return "avg_views";
  if (key === "growth") return "growth";
  return "match";
}

export default function KolScreen() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { session } = useAuth();
  const userId = session?.user.id;
  const { data: profile } = useProfile();
  const { data: niches } = useNicheTaxonomy();

  const tab = useMemo(() => parseTab(searchParams.get("tab")), [searchParams]);
  const page = useMemo(() => parsePage(searchParams.get("page")), [searchParams]);
  const followerPreset = useMemo(
    () => parseKolFollowerPreset(searchParams.get("followers")),
    [searchParams],
  );
  const growthFast = useMemo(() => searchParams.get("growth") === "1", [searchParams]);

  const apiSort = useMemo(() => parseKolApiSort(tab, searchParams.get("sort")), [tab, searchParams]);
  const orderDir = useMemo(
    () => parseKolOrderDir(tab, apiSort, searchParams.get("order_dir")),
    [tab, apiSort, searchParams],
  );
  const uiSortKey = useMemo(() => apiSortToUiKey(tab, apiSort), [tab, apiSort]);
  const uiSortDir: KolSortDir = orderDir;

  const nicheId = profile?.primary_niche ?? null;
  const nicheLabel =
    niches?.find((n) => n.id === nicheId)?.name ?? (nicheId != null ? `Ngách #${nicheId}` : "—");

  const cloudConfigured = Boolean(env.VITE_CLOUD_RUN_API_URL);

  const [searchQ, setSearchQ] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSearch(searchQ.trim()), 250);
    return () => window.clearTimeout(id);
  }, [searchQ]);

  const debouncedSearchNorm = normalizeKolSearchInput(debouncedSearch);

  const browse = useKolBrowse({
    nicheId: nicheId ?? undefined,
    tab,
    page,
    pageSize: 20,
    followerPreset,
    growthFast,
    sort: apiSort,
    orderDir,
    search: debouncedSearchNorm || undefined,
    enabled: Boolean(cloudConfigured && nicheId != null),
  });

  const browseAsOf = useMemo(() => {
    const t = browse.dataUpdatedAt;
    if (!t) return null;
    const d = new Date(t);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [browse.dataUpdatedAt]);
  const browseAsOfRelative = useMemo(
    () => formatRelativeSinceVi(new Date(), browseAsOf),
    [browseAsOf],
  );

  const discoverTotalQ = useKolDiscoverTotal(nicheId, Boolean(cloudConfigured && nicheId != null), {
    followerPreset,
    growthFast,
  });

  const togglePin = useKolTogglePin(userId);

  const rows = browse.data?.rows ?? [];

  const [picked, setPicked] = useState<string | null>(null);

  /** Reset to page 1 when debounced server search changes (skip initial mount). */
  const prevDebouncedSearch = useRef<string | null>(null);
  useEffect(() => {
    if (prevDebouncedSearch.current === null) {
      prevDebouncedSearch.current = debouncedSearch;
      return;
    }
    if (prevDebouncedSearch.current === debouncedSearch) return;
    prevDebouncedSearch.current = debouncedSearch;
    if (page <= 1) return;
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("page", "1");
        return next;
      },
      { replace: true },
    );
  }, [debouncedSearch, page, setSearchParams]);

  /** Keep selection in sync with visible rows (fixes card vs row after page/sort/refetch). */
  useEffect(() => {
    if (rows.length === 0) {
      setPicked(null);
      return;
    }
    const stillVisible = picked != null && rows.some((r) => r.handle === picked);
    if (!stillVisible) {
      setPicked(rows[0].handle);
    }
  }, [rows, picked]);

  const focused = useMemo(
    () => rows.find((r) => r.handle === picked) ?? rows[0] ?? null,
    [rows, picked],
  );

  const avatarPaletteIndex = useMemo(() => {
    if (!focused) return 0;
    const i = rows.findIndex((r) => r.handle === focused.handle);
    return i >= 0 ? i : 0;
  }, [rows, focused]);

  const openChannelAnalyze = useCallback(() => {
    const h = focused?.handle?.trim();
    if (!h) return;
    navigate(`/app/channel?handle=${encodeURIComponent(h)}`);
  }, [focused?.handle, navigate]);

  useEffect(() => {
    if (!browse.isSuccess || !browse.data || nicheId == null) return;
    logUsage("kol_screen_load", {
      tab: browse.data.tab,
      niche_id: nicheId,
      page: browse.data.page,
      total: browse.data.total,
      sort: apiSort,
      order_dir: orderDir,
      followers: followerPreset || null,
      growth_fast: growthFast,
      search: debouncedSearchNorm || null,
    });
  }, [
    browse.isSuccess,
    browse.dataUpdatedAt,
    nicheId,
    tab,
    page,
    apiSort,
    orderDir,
    followerPreset,
    growthFast,
    debouncedSearchNorm,
    browse.data?.total,
  ]);

  const pinnedCount = profile?.reference_channel_handles?.length ?? browse.data?.reference_handles.length ?? 0;
  const discoverCount = discoverTotalQ.data ?? browse.data?.total ?? 0;

  const pageSize = browse.data?.page_size ?? 20;
  const totalRows = browse.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));

  const setTab = (t: KolBrowseTab) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("tab", t);
        next.set("page", "1");
        next.delete("sort");
        next.delete("order_dir");
        return next;
      },
      { replace: true },
    );
    setPicked(null);
  };

  const setFollowerPreset = (p: KolFollowerPreset) => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        const cur = parseKolFollowerPreset(prev.get("followers"));
        if (p && cur === p) next.delete("followers");
        else if (p) next.set("followers", p);
        else next.delete("followers");
        next.set("page", "1");
        return next;
      },
      { replace: true },
    );
    setPicked(null);
  };

  const toggleGrowthFast = () => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (next.get("growth") === "1") next.delete("growth");
        else next.set("growth", "1");
        next.set("page", "1");
        return next;
      },
      { replace: true },
    );
    setPicked(null);
  };

  const goPage = (nextPage: number) => {
    const clamped = Math.min(Math.max(1, nextPage), totalPages);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set("page", String(clamped));
        return next;
      },
      { replace: true },
    );
  };

  const onSort = (key: KolSortKey) => {
    const nextApi = uiKeyToApiSort(tab, key);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        const curApi = parseKolApiSort(tab, prev.get("sort"));
        const curDir = parseKolOrderDir(tab, curApi, prev.get("order_dir"));
        let dir: KolOrderDir;
        if (curApi === nextApi) {
          dir = curDir === "asc" ? "desc" : "asc";
        } else {
          dir = defaultKolOrderDir(tab, nextApi);
        }
        next.set("sort", nextApi);
        next.set("order_dir", dir);
        next.set("page", "1");
        return next;
      },
      { replace: true },
    );
    setPicked(null);
  };

  const handleTogglePin = async () => {
    if (!focused) return;
    await togglePin.mutateAsync(focused.handle);
    logUsage("kol_pin", { handle: focused.handle, tab });
  };

  const refHandles = browse.data?.reference_handles ?? profile?.reference_channel_handles ?? [];
  const isPinned = Boolean(focused && refHandles.includes(focused.handle));

  const noNiche = nicheId == null;

  return (
    <AppLayout active="kol" enableMobileSidebar>
      <TopBar
        kicker="THEO DÕI"
        title="Kênh Tham Chiếu"
        right={
          <>
            <span className="hide-narrow hidden items-center gap-2 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1 gv-mono text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)] md:inline-flex">
              <span
                className="inline-block h-1.5 w-1.5 rounded-full bg-[color:var(--gv-accent)]"
                style={{ animation: "gv-pulse 1.6s ease-in-out infinite" }}
              />
              Dữ liệu cập nhật {browseAsOfRelative}
            </span>
            {/* Bookmark / "Đã Lưu" stub removed (D.6-era cleanup) — orphan
                 disabled button with no data model. The per-row pin/unpin
                 is the real "saved kênh" UX. */}
            <Btn variant="ink" size="sm" type="button" onClick={() => navigate("/app/answer")}>
              <Plus className="h-3.5 w-3.5" strokeWidth={2} />
              Phân tích mới
            </Btn>
          </>
        }
      />
      <main className="gv-route-main">
        {!cloudConfigured ? (
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Cần <span className="font-[family-name:var(--gv-font-mono)]">VITE_CLOUD_RUN_API_URL</span> trong env build.
          </p>
        ) : noNiche ? (
          <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
            <p className="gv-tight m-0 text-lg text-[color:var(--gv-ink)]">Chọn ngách trước</p>
            <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">
              Hoàn tất onboarding hoặc cập nhật ngách trong Cài đặt để xem kênh tham chiếu.
            </p>
            <Btn className="mt-4" type="button" variant="ink" size="sm" onClick={() => navigate("/app/onboarding")}>
              Mở onboarding
            </Btn>
          </div>
        ) : browse.isPending ? (
          <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-[color:var(--gv-ink-3)]" role="status">
            <Loader2 className="h-8 w-8 animate-spin text-[color:var(--gv-accent)]" strokeWidth={1.5} />
            <span className="text-sm">Đang tải danh sách…</span>
          </div>
        ) : browse.isError ? (
          (() => {
            // The Cloud Run /kol/browse endpoint emits a single 404
            // detail ("Chưa chọn ngách — chạy onboarding trước.") for
            // both real causes: profile has no primary_niche set, and
            // profile has a niche id that the server can't resolve
            // (deleted niche, cross-env drift). Without server-side
            // change we can differentiate client-side by reading
            // `profile.primary_niche`: if it's set, the error means
            // "your saved niche doesn't work anymore" — route them
            // to onboarding to re-pick rather than implying they
            // never chose one.
            const msg = browse.error?.message ?? "";
            const looksLikeNicheMissing = msg.toLowerCase().includes("ngách");
            const hasSavedNiche = nicheId != null;
            return (
              <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
                <p className="gv-tight text-[color:var(--gv-neg-deep)]">
                  {looksLikeNicheMissing && hasSavedNiche
                    ? "Không tải được danh sách ngách"
                    : "Không tải được dữ liệu"}
                </p>
                <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">
                  {looksLikeNicheMissing && hasSavedNiche
                    ? `Ngách hiện tại (#${nicheId}) không phản hồi — có thể đã bị xoá hoặc đổi. Chọn lại trong onboarding.`
                    : looksLikeNicheMissing
                      ? msg
                      : msg || "Lỗi không xác định"}
                </p>
                <div className="mt-4 flex gap-2">
                  <Btn type="button" variant="ghost" onClick={() => void browse.refetch()}>
                    Thử lại
                  </Btn>
                  {looksLikeNicheMissing ? (
                    <Btn type="button" variant="ink" onClick={() => navigate("/app/onboarding")}>
                      {hasSavedNiche ? "Chọn lại ngách" : "Chạy onboarding"}
                    </Btn>
                  ) : null}
                </div>
              </div>
            );
          })()
        ) : (
          <>
            <div className="mb-[18px] flex flex-wrap items-end justify-between gap-5 border-b border-[color:var(--gv-rule)] pb-3.5">
              <div>
                <div className="gv-mono mb-1.5 text-[10px] uppercase tracking-[0.16em] text-[color:var(--gv-ink-4)]">
                  KÊNH THAM CHIẾU · NGÁCH {nicheLabel.toUpperCase()}
                </div>
                <h1 className="gv-tight m-0 max-w-[640px] text-[clamp(28px,3.2vw,40px)] font-semibold leading-[1.05] tracking-[-0.02em] text-[color:var(--gv-ink)]">
                  {tab === "pinned" ? (
                    <>
                      {pinnedCount} kênh bạn đang{" "}
                      <em className="not-italic text-[color:var(--gv-accent)] [font-family:var(--gv-font-serif)] [font-style:italic]">
                        theo dõi sát
                      </em>
                    </>
                  ) : (
                    <>
                      Khám phá{" "}
                      <em className="not-italic text-[color:var(--gv-accent)] [font-family:var(--gv-font-serif)] [font-style:italic]">
                        kênh mới
                      </em>{" "}
                      trong ngách
                    </>
                  )}
                </h1>
              </div>
              <div className="inline-flex overflow-hidden rounded-[6px] border border-[color:var(--gv-ink)]">
                {(
                  [
                    ["pinned", "Đang theo dõi", pinnedCount, Bookmark] as const,
                    ["discover", "Khám phá", discoverCount, Sparkles] as const,
                  ] as const
                ).map(([k, lbl, n, Icon]) => {
                  const active = tab === k;
                  return (
                    <button
                      key={k}
                      type="button"
                      onClick={() => setTab(k)}
                      className={
                        "flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium transition-colors " +
                        (active
                          ? "bg-[color:var(--gv-ink)] text-[color:var(--gv-canvas)]"
                          : "bg-transparent text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)]")
                      }
                    >
                      <Icon className="h-3 w-3 shrink-0" strokeWidth={1.75} aria-hidden />
                      <span>{lbl}</span>
                      <span
                        className={
                          "gv-mono rounded px-1.5 py-0.5 text-[10px] " +
                          (active
                            ? "bg-[color:color-mix(in_srgb,var(--gv-canvas)_18%,transparent)] text-[color:var(--gv-canvas)]"
                            : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]")
                        }
                      >
                        {n}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <FilterChipRow
              trailing={
                <>
                  <div className="relative flex h-9 w-full min-w-[160px] max-w-[240px] items-center sm:w-[220px]">
                    <Search
                      className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-[color:var(--gv-ink-4)]"
                      strokeWidth={1.75}
                      aria-hidden
                    />
                    <input
                      value={searchQ}
                      onChange={(e) => setSearchQ(e.target.value)}
                      placeholder="Tìm @handle…"
                      className="gv-mono h-9 w-full rounded-lg border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] py-2 pl-8 pr-3 text-xs text-[color:var(--gv-ink)] placeholder:text-[color:var(--gv-ink-4)] outline-none ring-[color:var(--gv-accent)] focus:ring-2"
                      aria-label="Tìm theo handle hoặc tên (server)"
                    />
                  </div>
                  {tab === "pinned" ? (
                    <Btn type="button" variant="ink" size="sm" disabled title="Sắp có">
                      <Plus className="h-3 w-3" strokeWidth={2} aria-hidden />
                      Ghim kênh
                    </Btn>
                  ) : (
                    <Btn type="button" variant="ink" size="sm" disabled title="Sắp có">
                      <Sparkles className="h-3 w-3" strokeWidth={1.75} aria-hidden />
                      Gợi ý cho ngách của tôi
                    </Btn>
                  )}
                </>
              }
            >
              <Chip size="sm" variant="accent" active>
                {nicheLabel}
              </Chip>
              {FOLLOWER_PRESETS.map(({ id, label }) => (
                <Chip
                  key={id}
                  size="sm"
                  type="button"
                  active={followerPreset === id}
                  onClick={() => setFollowerPreset(followerPreset === id ? "" : id)}
                >
                  {label}
                </Chip>
              ))}
              <Chip size="sm" type="button" disabled title="Corpus chưa gắn mã quốc gia — sắp có">
                Việt Nam
              </Chip>
              <Chip
                size="sm"
                type="button"
                active={growthFast}
                onClick={toggleGrowthFast}
                title="Ưu tiên kênh view TB cao trong pool (proxy tăng trưởng)"
              >
                Tăng trưởng nhanh
              </Chip>
              <Chip size="sm" type="button" disabled title="Sắp có">
                + Thêm điều kiện
              </Chip>
            </FilterChipRow>

            <div className="grid grid-cols-1 gap-7 min-[1100px]:grid-cols-[1fr_380px] min-[1100px]:gap-7">
              <div className="min-w-0 overflow-x-auto">
                {rows.length === 0 && tab === "pinned" ? (
                  <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-8 text-center">
                    <p className="gv-tight text-lg text-[color:var(--gv-ink)]">Bạn chưa ghim kênh nào</p>
                    <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">
                      {'Chọn từ danh sách "Khám phá" để bắt đầu theo dõi.'}
                    </p>
                    <Btn className="mt-4" variant="ink" size="sm" type="button" onClick={() => setTab("discover")}>
                      <Sparkles className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden />
                      Mở Khám phá
                    </Btn>
                  </div>
                ) : rows.length ? (
                  <SortableCreatorsTable
                    rows={rows}
                    selectedHandle={picked}
                    onSelect={setPicked}
                    sortKey={uiSortKey}
                    sortDir={uiSortDir}
                    onSort={onSort}
                    tab={tab}
                    renderMatch={(row: KolBrowseRow) => <MatchScoreBar match={row.match_score} />}
                  />
                ) : (
                  <p className="py-10 text-center text-sm text-[color:var(--gv-ink-3)]">
                    Không có kênh phù hợp bộ lọc.
                  </p>
                )}
                {totalRows > pageSize ? (
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[color:var(--gv-rule)] pt-4">
                    <p className="gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
                      Trang {page}/{totalPages} · {totalRows} kênh
                    </p>
                    <div className="flex items-center gap-2">
                      <Btn
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={page <= 1}
                        onClick={() => goPage(page - 1)}
                        aria-label="Trang trước"
                      >
                        <ChevronLeft className="h-4 w-4" strokeWidth={2} />
                        Trước
                      </Btn>
                      <Btn
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={page >= totalPages}
                        onClick={() => goPage(page + 1)}
                        aria-label="Trang sau"
                      >
                        Sau
                        <ChevronRight className="h-4 w-4" strokeWidth={2} />
                      </Btn>
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="hidden min-[1100px]:block">
                <KolStickyDetailCard
                  row={focused}
                  avatarPaletteIndex={avatarPaletteIndex}
                  isPinned={isPinned}
                  pinPending={togglePin.isPending}
                  onTogglePin={() => void handleTogglePin()}
                  channelEnabled
                  onChannel={openChannelAnalyze}
                  onScript={() => {}}
                />
              </div>
            </div>

            <div className="mt-6 min-[1100px]:hidden">
              <KolStickyDetailCard
                row={focused}
                avatarPaletteIndex={avatarPaletteIndex}
                isPinned={isPinned}
                pinPending={togglePin.isPending}
                sticky={false}
                onTogglePin={() => void handleTogglePin()}
                channelEnabled
                onChannel={openChannelAnalyze}
                onScript={() => {}}
              />
            </div>
          </>
        )}
      </main>
    </AppLayout>
  );
}
