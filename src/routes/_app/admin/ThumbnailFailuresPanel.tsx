/**
 * ThumbnailFailuresPanel — thumbnail load failure rate and top-N hot spots.
 *
 * Queries the `thumbnail_failures` table (populated by track-thumbnail-failure
 * Edge Function) to surface the 7-day failure count and top-10 most-failed
 * video_ids. Use this to detect R2 outages or corpus-level thumbnail gaps
 * before they become user-facing problems.
 */
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/lib/supabase";

type FailureRow = {
  video_id: string;
  fail_count: number;
};

type PanelData = {
  total_7d: number;
  top_failures: FailureRow[];
  as_of: string;
};

function useThumbnailFailures() {
  return useQuery<PanelData>({
    queryKey: ["admin", "thumbnail-failures"],
    queryFn: async () => {
      const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

      // Both queries use SECURITY DEFINER RPCs — the thumbnail_failures table
      // has RLS enabled with no SELECT policies, so direct table queries from
      // user JWTs are always denied. The RPCs run as the function owner and
      // bypass RLS at the function level.
      const [countRes, topRes] = await Promise.all([
        supabase.rpc("thumbnail_failures_count_7d", { cutoff_ts: cutoff }),
        supabase.rpc("thumbnail_failures_top10", { cutoff_ts: cutoff }),
      ]);

      if (countRes.error) throw countRes.error;
      if (topRes.error) throw topRes.error;

      return {
        total_7d: (countRes.data as number) ?? 0,
        top_failures: (topRes.data ?? []) as FailureRow[],
        as_of: new Date().toISOString(),
      };
    },
    staleTime: 5 * 60_000,
  });
}

function FailureRow({ row }: { row: FailureRow }) {
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 font-mono text-[12px] text-[color:var(--gv-ink)] break-all">
        {row.video_id}
      </td>
      <td className="py-2.5 gv-mono text-[12px] tabular-nums text-[color:var(--gv-danger)]">
        {row.fail_count}
      </td>
    </tr>
  );
}

function TH({ children }: { children: React.ReactNode }) {
  return (
    <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
      {children}
    </th>
  );
}

export function ThumbnailFailuresPanel() {
  const q = useThumbnailFailures();

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải thumbnail failures"
        className="h-32 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (q.isError) {
    const msg = q.error instanceof Error ? q.error.message : "unknown";
    return (
      <p className="text-sm text-[color:var(--gv-danger)]">
        Không tải được thumbnail failures ({msg}).
      </p>
    );
  }
  if (!q.data) return null;

  const { total_7d, top_failures, as_of } = q.data;
  const isEmpty = top_failures.length === 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
        <div className="flex flex-col gap-1.5">
          <span className="gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
            Lỗi thumbnail · 7 ngày
          </span>
          <span
            className="gv-bignum tabular-nums"
            style={{ color: total_7d > 0 ? "var(--gv-danger)" : "var(--gv-ink)" }}
          >
            {total_7d.toLocaleString("vi-VN")}
          </span>
        </div>
        <div className="flex flex-col gap-1.5">
          <span className="gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
            Video bị ảnh hưởng
          </span>
          <span className="gv-bignum tabular-nums text-[color:var(--gv-ink)]">
            {top_failures.length.toLocaleString("vi-VN")}
          </span>
        </div>
      </div>

      {isEmpty ? (
        <p className="text-sm text-[color:var(--gv-ink-3)]">
          Không có lỗi thumbnail trong 7 ngày qua.
        </p>
      ) : (
        <div className="rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
          <p className="gv-kicker gv-kicker--dot gv-kicker--muted mb-3">
            Top video_id bị lỗi (7 ngày, tối đa 10)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-[color:var(--gv-rule)]">
                  <TH>video_id</TH>
                  <TH>Lần lỗi</TH>
                </tr>
              </thead>
              <tbody>
                {top_failures.map((row) => (
                  <FailureRow key={row.video_id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <p className="gv-kicker text-[color:var(--gv-ink-3)]">
        Cập nhật {new Date(as_of).toLocaleString("vi-VN")} · nguồn: thumbnail_failures table
      </p>
    </div>
  );
}
