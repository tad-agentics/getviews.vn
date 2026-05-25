/**
 * Pure helpers for Morning Signal selection — unit-tested without Supabase.
 */
import type { ContentClassIntelligenceRow } from "@/hooks/useContentClassIntelligence";
import {
  rowMatchesEnergyMode,
  type MorningEnergyMode,
} from "@/lib/productionFriction";

export type LifecycleStage =
  | "new_class"
  | "emerging"
  | "growing"
  | "peak"
  | "declining";

export type ClassMorningSignal = {
  content_class_id: number;
  label_vn: string;
  signal_type: LifecycleStage;
  avg_views: number | null;
  delta_pct: number | null;
  suggested_hook_type: string | null;
  suggested_sound: string | null;
  window_hours: 36;
  corpus_citation: string;
};

const OPPORTUNITY_STAGES: LifecycleStage[] = ["new_class", "emerging", "growing"];
const LIFECYCLE_RANK: Record<LifecycleStage, number> = {
  new_class: 0,
  emerging: 1,
  growing: 2,
  peak: 3,
  declining: 4,
};

export function lifecycleRank(stage: LifecycleStage | null | undefined): number {
  if (!stage) return 99;
  return LIFECYCLE_RANK[stage] ?? 99;
}

export function momentumScore(row: ContentClassIntelligenceRow): number {
  const vv = row.view_velocity;
  const fm = row.format_momentum;
  if (typeof vv === "number" && Number.isFinite(vv)) return vv;
  if (typeof fm === "number" && Number.isFinite(fm)) return fm;
  return 0;
}

export function deltaPctFromVelocity(viewVelocity: number | null | undefined): number | null {
  if (viewVelocity == null || !Number.isFinite(viewVelocity) || viewVelocity <= 0) return null;
  return Math.round((viewVelocity - 1) * 100);
}

export function isSignalEligible(row: ContentClassIntelligenceRow): boolean {
  if (row.claim_tier === "thin") return false;
  if ((row.video_count_7d ?? 0) < 5) return false;
  if (!row.lifecycle_stage) return false;
  return true;
}

export function sortSignalRows(rows: ContentClassIntelligenceRow[]): ContentClassIntelligenceRow[] {
  return [...rows].sort((a, b) => {
    const ra = lifecycleRank(a.lifecycle_stage as LifecycleStage);
    const rb = lifecycleRank(b.lifecycle_stage as LifecycleStage);
    if (ra !== rb) return ra - rb;
    return momentumScore(b) - momentumScore(a);
  });
}

/** Max-2-Card: 1 opportunity + 0–1 defensive. */
export function pickMorningSignals(
  rows: ContentClassIntelligenceRow[],
  labels: Map<number, string>,
  dismissedIds: Set<number>,
  options?: {
    energyMode?: MorningEnergyMode;
    formatAxisByClassId?: Map<number, string>;
  },
): ClassMorningSignal[] {
  const energyMode = options?.energyMode ?? "high";
  const formatAxisByClassId = options?.formatAxisByClassId ?? new Map();

  const eligible = sortSignalRows(
    rows.filter(
      (r) =>
        isSignalEligible(r) &&
        !dismissedIds.has(r.content_class_id) &&
        rowMatchesEnergyMode(r.content_class_id, formatAxisByClassId, energyMode),
    ),
  );

  const opportunity = eligible.find((r) =>
    OPPORTUNITY_STAGES.includes(r.lifecycle_stage as LifecycleStage),
  );
  const defensive = eligible.find(
    (r) =>
      r.lifecycle_stage === "declining" &&
      r.content_class_id !== opportunity?.content_class_id,
  );

  const out: ClassMorningSignal[] = [];
  if (opportunity) out.push(toSignal(opportunity, labels));
  if (defensive && out.length < 2) out.push(toSignal(defensive, labels));
  return out.slice(0, 2);
}

function topHookFromDistribution(dist: Record<string, number> | null | undefined): string | null {
  if (!dist || typeof dist !== "object") return null;
  let best: string | null = null;
  let bestN = -1;
  for (const [k, v] of Object.entries(dist)) {
    const n = typeof v === "number" ? v : Number(v);
    if (Number.isFinite(n) && n > bestN) {
      bestN = n;
      best = k;
    }
  }
  return best;
}

function toSignal(
  row: ContentClassIntelligenceRow,
  labels: Map<number, string>,
): ClassMorningSignal {
  const stage = row.lifecycle_stage as LifecycleStage;
  const isNew = stage === "new_class" || (row.avg_views_prior_7d ?? 0) === 0;
  return {
    content_class_id: row.content_class_id,
    label_vn: labels.get(row.content_class_id) ?? `Class ${row.content_class_id}`,
    signal_type: stage,
    avg_views: row.avg_views ?? row.median_views ?? null,
    delta_pct: isNew ? null : deltaPctFromVelocity(row.view_velocity),
    suggested_hook_type: topHookFromDistribution(row.hook_distribution ?? null),
    suggested_sound: null,
    window_hours: 36,
    corpus_citation: `${row.video_count_7d ?? row.sample_size ?? 0} video · 7 ngày`,
  };
}
