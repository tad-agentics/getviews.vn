import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

/**
 * L2.2 Sprint 4 — hydrate the per-script evidence strip on StudioHero.
 *
 * The morning_ritual cron stamps each ritual script with up to 12
 * ``evidence_video_ids`` (corpus video_ids whose hook_type matches the
 * script's hook_type_en). When a creator expands the strip, we fetch
 * just the thumbnail-rendering fields from ``video_corpus`` for those
 * ids — no new BE endpoint needed because authenticated_read_corpus RLS
 * already covers select access to these columns.
 *
 * Returned rows preserve the order of the input id list (the BE writes
 * them views-DESC), so the UI doesn't need to re-sort. Missing /
 * deleted rows simply drop out.
 */

export type EvidenceVideo = {
  video_id: string;
  thumbnail_url: string | null;
  creator_handle: string | null;
  views: number;
};

const EVIDENCE_COLS = "video_id, thumbnail_url, creator_handle, views";

export const ritualEvidenceKeys = {
  byIds: (videoIds: readonly string[]) =>
    ["ritual_evidence_videos", [...videoIds].sort().join(",")] as const,
};

export function useRitualEvidenceVideos(
  videoIds: readonly string[] | undefined,
  enabled: boolean,
) {
  const ids = videoIds ?? [];
  return useQuery<EvidenceVideo[]>({
    queryKey: ritualEvidenceKeys.byIds(ids),
    queryFn: async (): Promise<EvidenceVideo[]> => {
      if (ids.length === 0) return [];
      const { data, error } = await supabase
        .from("video_corpus")
        .select(EVIDENCE_COLS)
        .in("video_id", ids as string[]);
      if (error) throw error;
      const rows = ((data ?? []) as EvidenceVideo[]).filter(
        (r) => r.thumbnail_url != null && r.thumbnail_url.trim() !== "",
      );
      // Preserve the ranked order baked in by the BE picker.
      const order = new Map(ids.map((vid, i) => [vid, i]));
      return rows.slice().sort(
        (a, b) => (order.get(a.video_id) ?? 999) - (order.get(b.video_id) ?? 999),
      );
    },
    enabled: enabled && ids.length > 0,
    staleTime: 30 * 60 * 1000, // 30 min — corpus rows are append-mostly
    retry: false,
  });
}
