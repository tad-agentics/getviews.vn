import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShoppingBag } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { TrendingSoundCard, type TrendingSoundData } from "@/components/chat/TrendingSoundCard";
import { formatVN } from "@/lib/formatters";

interface Props {
  nicheId: number | null;
  /** Extra classes on the outer wrapper (e.g. rail spacing). */
  className?: string;
}

interface BreakoutSound {
  sound_name: string;
  total_usage: number;
  total_views: number;
  niche_count: number;
  commerce_signal: boolean;
}

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
        <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--gv-accent)]">
          Breakout xuyên niche
        </span>
        <span className="rounded-full bg-[var(--gv-accent)]/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--gv-accent)]">
          {sound.niche_count} niche
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

export function TrendingSoundsSection({ nicheId, className = "" }: Props) {
  const weekStr = useMemo(() => mondayWeekOfDateString(), []);

  // Fetch all sounds this week across all niches — used for breakout detection + niche filter
  const { data: allRows = [], isPending } = useQuery({
    queryKey: ["trending_sounds_all", weekStr],
    queryFn: async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (supabase as any)
        .from("trending_sounds")
        .select("sound_name, sound_id, usage_count, total_views, commerce_signal, niche_id")
        .eq("week_of", weekStr)
        .order("usage_count", { ascending: false })
        .limit(200);
      if (error) throw error;
      return (data ?? []) as Array<TrendingSoundData & { sound_id: string; niche_id: number }>;
    },
    staleTime: 30 * 60 * 1000,
  });

  // Cross-niche breakout: sound appearing in 3+ niches, ranked by total usage
  const breakoutSound = useMemo<BreakoutSound | null>(() => {
    if (allRows.length === 0) return null;

    const bySound = new Map<string, {
      sound_name: string;
      total_usage: number;
      total_views: number;
      niche_ids: Set<number>;
      commerce_signal: boolean;
    }>();

    for (const row of allRows) {
      const key = row.sound_id ?? row.sound_name;
      const existing = bySound.get(key) ?? {
        sound_name: row.sound_name,
        total_usage: 0,
        total_views: 0,
        niche_ids: new Set<number>(),
        commerce_signal: false,
      };
      existing.total_usage += row.usage_count ?? 0;
      existing.total_views += (row.total_views as number) ?? 0;
      existing.niche_ids.add(row.niche_id);
      existing.commerce_signal = existing.commerce_signal || Boolean(row.commerce_signal);
      bySound.set(key, existing);
    }

    const candidate = [...bySound.values()]
      .filter((s) => s.niche_ids.size >= 3)
      .sort((a, b) => b.total_usage - a.total_usage)[0] ?? null;

    if (!candidate) return null;
    return {
      sound_name: candidate.sound_name,
      total_usage: candidate.total_usage,
      total_views: candidate.total_views,
      niche_count: candidate.niche_ids.size,
      commerce_signal: candidate.commerce_signal,
    };
  }, [allRows]);

  // Niche-specific sounds (filtered client-side from the already-fetched allRows)
  const nicheRows = useMemo<TrendingSoundData[]>(() => {
    if (nicheId == null) return [];
    return allRows
      .filter((r) => r.niche_id === nicheId)
      .slice(0, 10)
      .map(({ sound_name, usage_count, total_views, commerce_signal }) => ({
        sound_name,
        usage_count,
        total_views: total_views as number,
        commerce_signal,
      }));
  }, [allRows, nicheId]);

  // Nothing to show: still loading and no niche
  if (isPending && nicheId === null) {
    return (
      <div className={`mb-4 ${className}`.trim()}>
        <div className="mb-3 h-[72px] animate-pulse rounded-xl bg-[var(--surface-alt)]" aria-hidden />
      </div>
    );
  }

  // Nothing at all (loaded, no breakout, no niche rows)
  if (!isPending && !breakoutSound && nicheRows.length === 0) return null;

  return (
    <div className={`mb-4 ${className}`.trim()}>
      {/* Cross-niche breakout banner — always shown when a breakout sound exists */}
      {breakoutSound ? <BreakoutSoundBanner sound={breakoutSound} /> : null}

      {/* Niche-specific sound row */}
      {nicheId !== null ? (
        <>
          <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
            Âm thanh đang nổi
          </p>
          {isPending ? (
            <div className="flex gap-3 overflow-x-auto pb-2">
              <SoundRowSkeleton />
              <SoundRowSkeleton />
            </div>
          ) : nicheRows.length > 0 ? (
            <div className="-mx-5 flex gap-3 overflow-x-auto px-5 pb-2 [scrollbar-width:none] lg:-mx-7 lg:px-7 [&::-webkit-scrollbar]:hidden">
              {nicheRows.map((row, idx) => (
                <TrendingSoundCard key={`${row.sound_name}-${idx}`} data={row} />
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
