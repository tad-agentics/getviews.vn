import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShoppingBag } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { TrendingSoundCard, type TrendingSoundData } from "@/components/chat/TrendingSoundCard";
import { formatVN } from "@/lib/formatters";

interface Props {
  /** Junction content classes — primary filter (Round B). */
  contentClassIds: number[];
  /** Legacy fallback when junction is empty. */
  legacyNicheId?: number | null;
  /** Extra classes on the outer wrapper (e.g. rail spacing). */
  className?: string;
}

interface BreakoutSound {
  sound_name: string;
  total_usage: number;
  total_views: number;
  class_count: number;
  commerce_signal: boolean;
}

type TrendingSoundRow = TrendingSoundData & {
  sound_id: string;
  content_class_id: number;
};

/** Week key for `trending_sounds.week_of` — exported so callers can share React Query keys. */
export function mondayWeekOfDateString(): string {
  const d = new Date();
  const day = d.getDay();
  d.setDate(d.getDate() - day + (day === 0 ? -6 : 1));
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function SoundRowSkeleton() {
  return <div className="h-16 min-w-[200px] flex-shrink-0 animate-pulse rounded-xl bg-[var(--surface-alt)]" aria-hidden />;
}

function BreakoutSoundBanner({ sound }: { sound: BreakoutSound }) {
  return (
    <div className="mb-3 rounded-xl border border-[var(--gv-accent)]/40 bg-gradient-to-r from-[var(--gv-accent-soft)] to-[var(--surface)] p-3.5">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-[11px] font-bold gv-kicker tracking-widest text-[var(--gv-accent)]">
          Breakout xuyên format
        </span>
        <span className="rounded-full bg-[var(--gv-accent)]/10 px-2 py-0.5 text-[11px] font-semibold text-[var(--gv-accent)]">
          {sound.class_count} format
        </span>
      </div>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold leading-snug text-[var(--ink)]">
            {sound.sound_name}
          </p>
          <p className="mt-1 font-mono text-xs text-[var(--muted)]">
            {formatVN(sound.total_usage)} video · {formatVN(sound.total_views)} lượt xem
          </p>
        </div>
        {sound.commerce_signal ? (
          <span className="flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium bg-[var(--gv-warn-soft)] text-[var(--gv-warn)]">
            <ShoppingBag className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            Commerce
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function TrendingSoundsSection({
  contentClassIds,
  legacyNicheId = null,
  className = "",
}: Props) {
  const weekStr = useMemo(() => mondayWeekOfDateString(), []);
  const classKey = useMemo(
    () => [...contentClassIds].sort((a, b) => a - b).join(","),
    [contentClassIds],
  );
  const hasClassScope = contentClassIds.length > 0;

  const { data: allRows = [], isPending } = useQuery({
    queryKey: ["trending_sounds_all", weekStr, classKey, legacyNicheId],
    queryFn: async () => {
      if (hasClassScope) {
        const { data, error } = await supabase
          .from("trending_sounds")
          .select("sound_name, sound_id, usage_count, total_views, commerce_signal, content_class_id")
          .eq("week_of", weekStr)
          .in("content_class_id", contentClassIds)
          .order("usage_count", { ascending: false })
          .limit(200);
        if (error) throw error;
        return (data ?? []) as TrendingSoundRow[];
      }
      if (legacyNicheId != null) {
        // Legacy rows may still exist until batch repopulates — query corpus sounds instead.
        const sinceIso = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
        const { data: corpusRows, error: cErr } = await supabase
          .from("video_corpus")
          .select("sound_id, sound_name, views, is_original_sound")
          .eq("ingest_loop_niche_id", legacyNicheId)
          .not("sound_id", "is", null)
          .gte("indexed_at", sinceIso)
          .limit(500);
        if (cErr) throw cErr;
        const agg = new Map<string, TrendingSoundRow>();
        for (const row of corpusRows ?? []) {
          const sid = String((row as { sound_id?: string | null }).sound_id ?? "");
          if (!sid) continue;
          if ((row as { is_original_sound?: boolean | null }).is_original_sound) continue;
          const existing = agg.get(sid) ?? {
            sound_id: sid,
            sound_name: String((row as { sound_name?: string | null }).sound_name ?? sid),
            usage_count: 0,
            total_views: 0,
            commerce_signal: false,
            content_class_id: 0,
          };
          existing.usage_count += 1;
          existing.total_views += Number((row as { views?: number | null }).views ?? 0);
          agg.set(sid, existing);
        }
        return [...agg.values()]
          .sort((a, b) => b.usage_count - a.usage_count)
          .slice(0, 10);
      }
      return [];
    },
    enabled: hasClassScope || legacyNicheId != null,
    staleTime: 30 * 60 * 1000,
  });

  const { data: breakoutPool = [] } = useQuery({
    queryKey: ["trending_sounds_breakout_pool", weekStr],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("trending_sounds")
        .select("sound_name, sound_id, usage_count, total_views, commerce_signal, content_class_id")
        .eq("week_of", weekStr)
        .limit(400);
      if (error) throw error;
      return (data ?? []) as TrendingSoundRow[];
    },
    staleTime: 30 * 60 * 1000,
  });

  const breakoutSound = useMemo<BreakoutSound | null>(() => {
    if (breakoutPool.length === 0) return null;

    const bySound = new Map<string, {
      sound_name: string;
      total_usage: number;
      total_views: number;
      class_ids: Set<number>;
      commerce_signal: boolean;
    }>();

    for (const row of breakoutPool) {
      const key = row.sound_id ?? row.sound_name;
      const existing = bySound.get(key) ?? {
        sound_name: row.sound_name,
        total_usage: 0,
        total_views: 0,
        class_ids: new Set<number>(),
        commerce_signal: false,
      };
      existing.total_usage += row.usage_count ?? 0;
      existing.total_views += (row.total_views as number) ?? 0;
      if (row.content_class_id != null) {
        existing.class_ids.add(row.content_class_id);
      }
      existing.commerce_signal = existing.commerce_signal || Boolean(row.commerce_signal);
      bySound.set(key, existing);
    }

    const candidate = [...bySound.values()]
      .filter((s) => s.class_ids.size >= 3)
      .sort((a, b) => b.total_usage - a.total_usage)[0] ?? null;

    if (!candidate) return null;
    return {
      sound_name: candidate.sound_name,
      total_usage: candidate.total_usage,
      total_views: candidate.total_views,
      class_count: candidate.class_ids.size,
      commerce_signal: candidate.commerce_signal,
    };
  }, [breakoutPool]);

  const scopedRows = useMemo<TrendingSoundData[]>(() => {
    if (!hasClassScope && legacyNicheId == null) return [];
    return allRows.slice(0, 10).map(({ sound_name, usage_count, total_views, commerce_signal }) => ({
      sound_name,
      usage_count,
      total_views: total_views as number,
      commerce_signal,
    }));
  }, [allRows, hasClassScope, legacyNicheId]);

  const showSection = hasClassScope || legacyNicheId != null;

  if (!showSection) return null;

  if (isPending && scopedRows.length === 0 && !breakoutSound) {
    return (
      <div className={`mb-4 ${className}`.trim()}>
        <div className="mb-3 h-[72px] animate-pulse rounded-xl bg-[var(--surface-alt)]" aria-hidden />
      </div>
    );
  }

  if (!isPending && !breakoutSound && scopedRows.length === 0) return null;

  return (
    <div className={`mb-4 ${className}`.trim()}>
      {breakoutSound ? <BreakoutSoundBanner sound={breakoutSound} /> : null}

      {showSection ? (
        <>
          <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
            Âm thanh đang nổi
          </p>
          {isPending ? (
            <div className="flex gap-3 overflow-x-auto pb-2">
              <SoundRowSkeleton />
              <SoundRowSkeleton />
            </div>
          ) : scopedRows.length > 0 ? (
            <div className="-mx-5 flex gap-3 overflow-x-auto px-5 pb-2 [scrollbar-width:none] lg:-mx-7 lg:px-7 [&::-webkit-scrollbar]:hidden">
              {scopedRows.map((row, idx) => (
                <TrendingSoundCard key={`${row.sound_name}-${idx}`} data={row} />
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
