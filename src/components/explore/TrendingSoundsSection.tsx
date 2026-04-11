import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";
import { TrendingSoundCard, type TrendingSoundData } from "@/components/chat/TrendingSoundCard";

interface Props {
  nicheId: number | null;
}

function mondayWeekOfDateString(): string {
  const d = new Date();
  const day = d.getDay();
  d.setDate(d.getDate() - day + 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function SoundRowSkeleton() {
  return <div className="h-16 min-w-[200px] flex-shrink-0 animate-pulse rounded-xl bg-gray-100" aria-hidden />;
}

export function TrendingSoundsSection({ nicheId }: Props) {
  const weekStr = useMemo(() => mondayWeekOfDateString(), []);

  const { data: rows = [], isPending } = useQuery({
    queryKey: ["trending_sounds", nicheId, weekStr],
    queryFn: async () => {
      // TODO: remove cast after `supabase gen types` includes `trending_sounds`
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data, error } = await (supabase as any)
        .from("trending_sounds")
        .select("sound_name,usage_count,total_views,commerce_signal")
        .eq("niche_id", nicheId!)
        .eq("week_of", weekStr)
        .order("usage_count", { ascending: false })
        .limit(10);
      if (error) throw error;
      return (data ?? []) as TrendingSoundData[];
    },
    enabled: nicheId != null,
    staleTime: 30 * 60 * 1000,
  });

  const showSkeleton = nicheId === null || isPending;

  if (!showSkeleton && rows.length === 0) return null;

  return (
    <div className="mb-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">Âm thanh đang nổi</h2>
      {showSkeleton ? (
        <div className="flex gap-3 overflow-x-auto pb-2">
          <SoundRowSkeleton />
          <SoundRowSkeleton />
          <SoundRowSkeleton />
        </div>
      ) : (
        <div className="-mx-5 flex gap-3 overflow-x-auto px-5 pb-2 [scrollbar-width:none] lg:-mx-7 lg:px-7 [&::-webkit-scrollbar]:hidden">
          {rows.map((row, idx) => (
            <TrendingSoundCard key={`${row.sound_name}-${idx}`} data={row} />
          ))}
        </div>
      )}
    </div>
  );
}
