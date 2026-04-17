import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { queryKeys } from "@/lib/query-keys";

export interface VideoRow {
  video_id: string;
  thumbnail_url: string | null;
  tiktok_url: string | null;
  creator_handle: string | null;
  views: number;
  breakout_multiplier: number | null;
  velocity: number | null;
  rank: number;
  list_type: "bung_no" | "dang_hot";
}

type RankingRow = {
  video_id: string;
  list_type: "bung_no" | "dang_hot";
  rank: number;
  breakout_multiplier: number | null;
  velocity: number | null;
};

function toNum(v: unknown): number {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v);
    return Number.isNaN(n) ? 0 : n;
  }
  return 0;
}

async function fetchRankingRows(listType: "bung_no" | "dang_hot"): Promise<RankingRow[]> {
  const { data, error } = await supabase
    .from("video_dang_hoc")
    .select("video_id, list_type, rank, breakout_multiplier, velocity")
    .eq("list_type", listType)
    .order("rank", { ascending: true });
  if (error) throw error;
  return (data ?? []) as RankingRow[];
}

async function fetchVideoDangHocMerged(): Promise<{ bungNo: VideoRow[]; dangHot: VideoRow[] }> {
  const [bungRank, hotRank] = await Promise.all([
    fetchRankingRows("bung_no"),
    fetchRankingRows("dang_hot"),
  ]);

  const ids = [...new Set([...bungRank, ...hotRank].map((r) => r.video_id))];
  if (ids.length === 0) {
    return { bungNo: [], dangHot: [] };
  }

  const { data: corpusRows, error: corpusError } = await supabase
    .from("video_corpus")
    .select("video_id, thumbnail_url, tiktok_url, creator_handle, views, breakout_multiplier")
    .in("video_id", ids);

  if (corpusError) throw corpusError;

  const meta = new Map(
    (corpusRows ?? []).map((row) => [
      row.video_id as string,
      {
        thumbnail_url: (row.thumbnail_url as string | null) ?? null,
        tiktok_url: (row.tiktok_url as string | null) ?? null,
        creator_handle: (row.creator_handle as string | null) ?? null,
        views: toNum(row.views),
        breakout_multiplier:
          row.breakout_multiplier === null || row.breakout_multiplier === undefined
            ? null
            : toNum(row.breakout_multiplier),
      },
    ]),
  );

  function buildVideoRows(rankings: RankingRow[], listType: "bung_no" | "dang_hot"): VideoRow[] {
    return rankings.map((r) => {
      const m = meta.get(r.video_id);
      return {
        video_id: r.video_id,
        rank: r.rank,
        list_type: listType,
        velocity: r.velocity === null || r.velocity === undefined ? null : Number(r.velocity),
        thumbnail_url: m?.thumbnail_url ?? null,
        tiktok_url: m?.tiktok_url ?? null,
        creator_handle: m?.creator_handle ?? null,
        views: m?.views ?? 0,
        breakout_multiplier:
          listType === "bung_no"
            ? (r.breakout_multiplier !== null && r.breakout_multiplier !== undefined
                ? Number(r.breakout_multiplier)
                : (m?.breakout_multiplier ?? null))
            : (m?.breakout_multiplier ?? null),
      };
    });
  }

  return {
    bungNo: buildVideoRows(bungRank, "bung_no"),
    dangHot: buildVideoRows(hotRank, "dang_hot"),
  };
}

export function useVideoDangHoc() {
  const q = useQuery({
    queryKey: queryKeys.videoDangHoc(),
    queryFn: fetchVideoDangHocMerged,
    staleTime: 5 * 60 * 1000,
  });

  return {
    bungNo: q.data?.bungNo ?? [],
    dangHot: q.data?.dangHot ?? [],
    isLoading: q.isPending,
    error: q.error,
  };
}
