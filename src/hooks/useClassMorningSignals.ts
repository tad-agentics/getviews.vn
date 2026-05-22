import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import {
  pickMorningSignals,
  readDismissedClassIds,
  type ClassMorningSignal,
} from "@/lib/classMorningSignals";
import { fetchContentClassIdsForCreatorNiche } from "@/lib/corpusNicheFilter";
import type { MorningEnergyMode } from "@/lib/productionFriction";
import type { ContentClassIntelligenceRow } from "@/hooks/useContentClassIntelligence";

export const classMorningSignalsKeys = {
  all: () => ["class_morning_signals"] as const,
  niche: (creatorNicheId: number, energyMode: MorningEnergyMode) =>
    ["class_morning_signals", creatorNicheId, energyMode] as const,
};

async function fetchClassMeta(
  classIds: number[],
): Promise<{ labels: Map<number, string>; formatAxisByClassId: Map<number, string> }> {
  if (classIds.length === 0) return { labels: new Map(), formatAxisByClassId: new Map() };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, error } = await (supabase as any)
    .from("content_classifications")
    .select("id,name_vn,format_axis")
    .in("id", classIds);
  if (error) throw error;
  const labels = new Map<number, string>();
  const formatAxisByClassId = new Map<number, string>();
  for (const row of data ?? []) {
    if (typeof row.id !== "number") continue;
    if (typeof row.name_vn === "string") labels.set(row.id, row.name_vn);
    if (typeof row.format_axis === "string") formatAxisByClassId.set(row.id, row.format_axis);
  }
  return { labels, formatAxisByClassId };
}

async function fetchMorningSignals(
  creatorNicheId: number,
  energyMode: MorningEnergyMode,
): Promise<ClassMorningSignal[]> {
  const classIds = await fetchContentClassIdsForCreatorNiche(creatorNicheId, {
    primaryOnly: true,
  });
  if (classIds.length === 0) return [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, error } = await (supabase as any)
    .from("content_class_intelligence")
    .select(
      "content_class_id,sample_size,median_views,avg_views,claim_tier,computed_at,video_count_7d,video_count_prior_7d,avg_views_7d,avg_views_prior_7d,view_velocity,format_momentum,lifecycle_stage,hook_distribution",
    )
    .in("content_class_id", classIds);
  if (error) throw error;

  const rows = (data ?? []) as ContentClassIntelligenceRow[];
  const { labels, formatAxisByClassId } = await fetchClassMeta(classIds);
  const dismissed = readDismissedClassIds();
  return pickMorningSignals(rows, labels, dismissed, { energyMode, formatAxisByClassId });
}

/**
 * Morning Signal strip — junction-scoped class intelligence with Max-2-Card selection.
 * See `artifacts/docs/class-intelligence-ui-spec.md`.
 */
export function useClassMorningSignals(
  creatorNicheId: number | null,
  energyMode: MorningEnergyMode = "high",
) {
  return useQuery({
    queryKey: classMorningSignalsKeys.niche(creatorNicheId ?? -1, energyMode),
    queryFn: () => fetchMorningSignals(creatorNicheId!, energyMode),
    enabled: creatorNicheId != null,
    staleTime: 30 * 60_000,
    refetchOnWindowFocus: false,
  });
}

export type { ClassMorningSignal };
