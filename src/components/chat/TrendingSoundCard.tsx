/**
 * TrendingSoundCard — compact row for a trending TikTok sound (U3).
 */
import { formatVN } from "@/lib/formatters";

export interface TrendingSoundData {
  sound_name: string;
  usage_count: number;
  total_views: number;
  commerce_signal: boolean;
}

interface Props {
  data: TrendingSoundData;
}

export function TrendingSoundCard({ data }: Props) {
  return (
    <div className="min-w-[200px] flex-shrink-0 rounded-xl border border-gray-100 bg-white p-3">
      <div className="flex items-start gap-2">
        <span className="text-base leading-none" aria-hidden>
          🎵
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-bold leading-snug text-[var(--ink)] line-clamp-2">{data.sound_name}</p>
            <span className="flex-shrink-0 font-mono text-xs font-semibold text-[color:var(--gv-accent)] tabular-nums">
              {formatVN(data.usage_count)}
            </span>
          </div>
          <p className="mt-1 font-mono text-xs text-[color:var(--gv-ink-3)] tabular-nums">{formatVN(data.total_views)} lượt xem</p>
          {data.commerce_signal ? (
            <span className="mt-1 inline-block rounded px-1.5 text-xs font-medium bg-amber-50 text-amber-700">
              💰 Thương mại
            </span>
          ) : null}
        </div>
      </div>
      <p className="mt-2 text-xs text-gray-400">{formatVN(data.usage_count)} video dùng tuần này</p>
    </div>
  );
}
