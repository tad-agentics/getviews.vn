import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { KolBrowseResponse, KolBrowseTab } from "@/lib/api-types";
import { env } from "@/lib/env";
import { supabase } from "@/lib/supabase";
import { queryKeys } from "@/lib/query-keys";

/** URL `?followers=` preset — maps to Cloud Run `followers_min` / `followers_max`. */
export type KolFollowerPreset = "" | "10k-100k" | "100k-1m" | "1m-5m";

/** Cloud Run `sort` query (B.2.4 server-side ordering). */
export type KolApiSort = "pinned" | "rank" | "match" | "followers" | "avg_views" | "growth" | "name";

export type KolOrderDir = "asc" | "desc";

export function parseKolFollowerPreset(raw: string | null): KolFollowerPreset {
  if (raw === "10k-100k" || raw === "100k-1m" || raw === "1m-5m") return raw;
  return "";
}

export function defaultKolApiSort(tab: KolBrowseTab): KolApiSort {
  return tab === "pinned" ? "pinned" : "match";
}

export function defaultKolOrderDir(tab: KolBrowseTab, sort: KolApiSort): KolOrderDir {
  if (sort === "pinned" || sort === "rank" || sort === "name") return "asc";
  return "desc";
}

const API_SORT_SET = new Set<string>(["pinned", "rank", "match", "followers", "avg_views", "growth", "name"]);

export function parseKolApiSort(tab: KolBrowseTab, raw: string | null): KolApiSort {
  if (!raw || !API_SORT_SET.has(raw)) return defaultKolApiSort(tab);
  const s = raw as KolApiSort;
  if (tab === "pinned" && s === "rank") return "pinned";
  if (tab === "discover" && s === "pinned") return "match";
  return s;
}

export function parseKolOrderDir(tab: KolBrowseTab, sort: KolApiSort, raw: string | null): KolOrderDir {
  if (raw === "asc" || raw === "desc") return raw;
  return defaultKolOrderDir(tab, sort);
}

function boundsForPreset(p: KolFollowerPreset): { min?: number; max?: number } {
  switch (p) {
    case "10k-100k":
      return { min: 10_000, max: 100_000 };
    case "100k-1m":
      return { min: 100_000, max: 1_000_000 };
    case "1m-5m":
      return { min: 1_000_000, max: 5_000_000 };
    default:
      return {};
  }
}

function kolBrowseFilterSig(preset: KolFollowerPreset, growthFast: boolean, search?: string): string {
  const raw = (search ?? "").trim().toLowerCase().replace(/^@+/, "");
  return `${preset || "none"}:${growthFast ? "1" : "0"}:search:${raw || "none"}`;
}

function kolSortSig(sort: KolApiSort, orderDir: KolOrderDir): string {
  return `${sort}:${orderDir}`;
}

export const kolBrowseKeys = {
  all: () => ["kol-browse"] as const,
  list: (
    nicheId: number,
    tab: KolBrowseTab,
    page: number,
    pageSize: number,
    filterSig: string,
    sortSig: string,
  ) => [...kolBrowseKeys.all(), nicheId, tab, page, pageSize, filterSig, sortSig] as const,
  discoverTotal: (nicheId: number, filterSig: string) =>
    [...kolBrowseKeys.all(), "discover-total", nicheId, filterSig] as const,
};

/** Normalized search for API (trim, lower, strip @). */
export function normalizeKolSearchInput(raw: string | undefined): string {
  return (raw ?? "").trim().toLowerCase().replace(/^@+/, "");
}

function isKolBrowseResponse(v: unknown): v is KolBrowseResponse {
  return (
    typeof v === "object" &&
    v != null &&
    "rows" in v &&
    Array.isArray((v as KolBrowseResponse).rows) &&
    "reference_handles" in v
  );
}

async function fetchKolBrowse(params: {
  nicheId: number;
  tab: KolBrowseTab;
  page: number;
  pageSize: number;
  followerPreset: KolFollowerPreset;
  growthFast: boolean;
  sort: KolApiSort;
  orderDir: KolOrderDir;
  search?: string;
}): Promise<KolBrowseResponse> {
  const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
  if (!cloudRunUrl) throw new Error("Cloud Run URL chưa cấu hình");
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) throw new Error("Chưa đăng nhập");

  const sp = new URLSearchParams({
    tab: params.tab,
    page: String(params.page),
    page_size: String(params.pageSize),
    niche_id: String(params.nicheId),
    sort: params.sort,
    order_dir: params.orderDir,
  });
  const { min, max } = boundsForPreset(params.followerPreset);
  if (min != null) sp.set("followers_min", String(min));
  if (max != null) sp.set("followers_max", String(max));
  if (params.growthFast) sp.set("growth_fast", "true");
  const qSearch = normalizeKolSearchInput(params.search);
  if (qSearch) sp.set("search", qSearch);

  const res = await fetch(`${cloudRunUrl}/kol/browse?${sp.toString()}`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  if (res.status === 404) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(detail.detail ?? "Chưa chọn ngách");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as KolBrowseResponse;
}

export function useKolBrowse(params: {
  nicheId: number | null | undefined;
  tab: KolBrowseTab;
  page: number;
  pageSize?: number;
  followerPreset?: KolFollowerPreset;
  growthFast?: boolean;
  sort: KolApiSort;
  orderDir: KolOrderDir;
  /** Server substring filter (debounced in UI). */
  search?: string;
  enabled?: boolean;
}) {
  const pageSize = params.pageSize ?? 20;
  const nicheId = params.nicheId ?? null;
  const preset = params.followerPreset ?? "";
  const growthFast = Boolean(params.growthFast);
  const searchNorm = normalizeKolSearchInput(params.search);
  const filterSig = kolBrowseFilterSig(preset, growthFast, searchNorm);
  const sortSig = kolSortSig(params.sort, params.orderDir);
  const enabled = Boolean(params.enabled !== false && nicheId != null && env.VITE_CLOUD_RUN_API_URL);

  return useQuery({
    queryKey: kolBrowseKeys.list(nicheId as number, params.tab, params.page, pageSize, filterSig, sortSig),
    queryFn: () =>
      fetchKolBrowse({
        nicheId: nicheId as number,
        tab: params.tab,
        page: params.page,
        pageSize,
        followerPreset: preset,
        growthFast,
        sort: params.sort,
        orderDir: params.orderDir,
        search: searchNorm || undefined,
      }),
    enabled,
    staleTime: 60_000,
  });
}

/** Discover list total (tab badge) — respects filters only (total invariant to sort). */
export function useKolDiscoverTotal(
  nicheId: number | null | undefined,
  enabled: boolean,
  opts?: { followerPreset?: KolFollowerPreset; growthFast?: boolean },
) {
  const nid = nicheId ?? null;
  const preset = opts?.followerPreset ?? "";
  const growthFast = Boolean(opts?.growthFast);
  const filterSig = kolBrowseFilterSig(preset, growthFast);

  return useQuery({
    queryKey: kolBrowseKeys.discoverTotal(nid ?? -1, filterSig),
    queryFn: async () => {
      const data = await fetchKolBrowse({
        nicheId: nid as number,
        tab: "discover",
        page: 1,
        pageSize: 1,
        followerPreset: preset,
        growthFast,
        sort: "match",
        orderDir: "desc",
      });
      return data.total;
    },
    enabled: Boolean(enabled && nid != null && env.VITE_CLOUD_RUN_API_URL),
    staleTime: 60_000,
  });
}

export function useKolTogglePin(userId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (handle: string) => {
      const cloudRunUrl = env.VITE_CLOUD_RUN_API_URL;
      if (!cloudRunUrl) throw new Error("Cloud Run URL chưa cấu hình");
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) throw new Error("Chưa đăng nhập");
      const norm = handle.trim().replace(/^@+/, "").toLowerCase();
      const res = await fetch(`${cloudRunUrl}/kol/toggle-pin`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ handle: norm }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
    },
    onMutate: async (handle) => {
      const norm = handle.trim().replace(/^@+/, "").toLowerCase();
      await qc.cancelQueries({ queryKey: kolBrowseKeys.all() });
      for (const [key, data] of qc.getQueriesData<KolBrowseResponse>({ queryKey: kolBrowseKeys.all() })) {
        if (!isKolBrowseResponse(data)) continue;
        const had = data.reference_handles.includes(norm);
        const nextRefs = had
          ? data.reference_handles.filter((h) => h !== norm)
          : [...data.reference_handles, norm].slice(0, 10);
        const next: KolBrowseResponse = {
          ...data,
          reference_handles: nextRefs,
          rows: data.rows.map((r) => (r.handle === norm ? { ...r, is_pinned: !had } : r)),
        };
        qc.setQueryData(key, next);
      }
    },
    onError: () => {
      void qc.invalidateQueries({ queryKey: kolBrowseKeys.all() });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: kolBrowseKeys.all() });
      if (userId) void qc.invalidateQueries({ queryKey: queryKeys.profile(userId) });
    },
  });
}
