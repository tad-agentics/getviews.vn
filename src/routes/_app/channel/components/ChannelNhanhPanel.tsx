import { Link } from "react-router";
import { Loader2 } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import { useChannelQuickPeek, type ChannelQuickPeek } from "@/hooks/useChannelQuickPeek";
import { hookNameVI } from "@/lib/constants/hook-names-vi";
import { formatVN } from "@/lib/formatters";

type ChannelNhanhPanelProps = {
  handle: string;
  onUpgradeToSau: () => void;
  /** When provided, skip a second quick-peek fetch (parent already loaded). */
  peekData?: ChannelQuickPeek | null;
  peekLoading?: boolean;
  peekError?: boolean;
};

export function ChannelNhanhPanel({
  handle,
  onUpgradeToSau,
  peekData,
  peekLoading,
  peekError,
}: ChannelNhanhPanelProps) {
  const at = handle.startsWith("@") ? handle : `@${handle}`;
  const internalPeek = useChannelQuickPeek(handle, peekData === undefined);
  const data = peekData !== undefined ? peekData : internalPeek.data;
  const isLoading = peekLoading ?? internalPeek.isLoading;
  const isError = peekError ?? internalPeek.isError;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-8 text-sm text-[color:var(--gv-ink-3)]">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        Đang đọc kho corpus cho {at}…
      </div>
    );
  }

  if (isError || !data || data.corpus_video_count < 3) {
    return (
      <div className="rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6">
        <p className="m-0 text-sm text-[color:var(--gv-ink-3)]">
          Chưa đủ video của {at} trong kho để soi nhanh — thử{" "}
          <button type="button" className="font-semibold text-[color:var(--gv-accent)] underline-offset-2 hover:underline" onClick={onUpgradeToSau}>
            Sâu
          </button>{" "}
          để phân tích live.
        </p>
      </div>
    );
  }

  const breakout = data.breakout_video;
  const breakoutUrl = breakout
    ? `https://www.tiktok.com/@${handle.replace(/^@/, "")}/video/${breakout.video_id}`
    : null;

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-5 py-6 sm:px-7">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="gv-mono m-0 text-[11px] gv-kicker tracking-[0.12em] text-[color:var(--gv-accent-deep)]">
            Soi kênh · Nhanh
          </p>
          <h2 className="gv-tight m-0 mt-1 text-[17px] font-semibold text-[color:var(--gv-ink)]">{at}</h2>
          <p className="m-0 mt-1 text-[12px] text-[color:var(--gv-ink-3)]">
            {data.corpus_video_count} video gần nhất trong kho · không trừ credit
          </p>
        </div>
        <Btn type="button" variant="accent" size="sm" onClick={onUpgradeToSau}>
          Nâng Sâu · 3 credit
        </Btn>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="Median lượt xem" value={data.median_views != null ? formatVN(data.median_views) : "—"} />
        <StatCard label="Hook chính" value={data.dominant_hook ? hookNameVI(data.dominant_hook) : "—"} />
        <StatCard
          label="Video nổi bật gần nhất"
          value={breakout ? `${formatVN(breakout.views)} lượt xem` : "—"}
        />
      </div>

      {data.findings.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {data.findings.map((f) => (
            <li
              key={f.finding_id}
              className="rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2.5 text-xs leading-snug text-[color:var(--gv-ink-2)]"
            >
              {f.teaser}
            </li>
          ))}
        </ul>
      ) : data.teaser ? (
        <p className="m-0 text-xs leading-snug text-[color:var(--gv-ink-2)]">{data.teaser}</p>
      ) : null}

      {breakoutUrl ? (
        <Link
          to={`/app/answer?q=${encodeURIComponent(breakoutUrl)}&depth=basic`}
          className="text-[12px] font-medium text-[color:var(--gv-accent)] underline-offset-2 hover:underline"
        >
          Xem video nổi bật trong Answer →
        </Link>
      ) : null}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[10px] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas)] px-3 py-2.5">
      <p className="gv-mono m-0 text-[11px] gv-kicker tracking-wide text-[color:var(--gv-ink-3)]">{label}</p>
      <p className="gv-mono m-0 mt-1 text-[17px] font-semibold text-[color:var(--gv-ink)]">{value}</p>
    </div>
  );
}
