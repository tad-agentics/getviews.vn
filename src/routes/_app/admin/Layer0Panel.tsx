/**
 * Layer0Panel — hashtag / signal health per taxonomy niche (admin).
 *
 * Visualises the four signals that ``/batch/layer0`` produces:
 *
 *   1. Last-run header  — when the discovery loop last completed +
 *      status + duration. Mirrors the Bignum strip pattern from
 *      ``CorpusHealthPanel``.
 *   2. Niche-freshness list — niches whose ``signal_hashtags`` array is
 *      stale (most-stale first). Operators use this to decide whether
 *      to manually rerun ``/admin/trigger/layer0`` for a specific niche.
 *   3. Pending review queue — top 20 ``niche_candidates`` rows where
 *      ``reviewed=false``, sorted by ``occurrences``. Each row is a
 *      hashtag the loop discovered but couldn't auto-classify with
 *      enough confidence; a human needs to assign or reject.
 *   4. Recent-runs strip — last 5 ``batch/layer0`` rows from
 *      ``batch_job_runs`` to spot a breaking pattern.
 *
 * Read-only. Operators trigger a rerun via TriggersPanel
 * (``/admin/trigger/layer0``) — keeping the trigger surface centralised
 * there avoids duplicate UI patterns.
 */
import { useMemo } from "react";
import {
  useAdminLayer0,
  type Layer0Candidate,
  type Layer0NicheFreshness,
  type Layer0Run,
} from "@/hooks/useAdminLayer0";

function relativeAge(iso: string | null): string {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const ms = Date.now() - then;
  const hours = Math.round(ms / 3_600_000);
  if (hours < 1) {
    const mins = Math.max(0, Math.round(ms / 60_000));
    return `${mins}m`;
  }
  if (hours < 24) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

function formatDurationMs(ms: number | null): string {
  if (ms == null || ms < 0) return "—";
  if (ms < 1000) return `${ms}ms`;
  const sec = ms / 1000;
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const min = sec / 60;
  return `${min.toFixed(1)}m`;
}

function formatVN(n: number): string {
  return n.toLocaleString("vi-VN");
}

function Bignum({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  const display = typeof value === "number" ? formatVN(value) : value;
  return (
    <div className="flex flex-col gap-1.5">
      <span className="gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">{label}</span>
      <span className="gv-bignum text-[color:var(--gv-ink)] tabular-nums">{display}</span>
      {sub ? (
        <span className="gv-kicker text-[color:var(--gv-ink-3)] tabular-nums">{sub}</span>
      ) : null}
    </div>
  );
}

function StatusChip({ status }: { status: string | null }) {
  const ok = status === "ok";
  const tone = ok
    ? "bg-[color:var(--gv-pos-soft)] text-[color:var(--gv-pos-deep)]"
    : status
      ? "bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg-deep)]"
      : "bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]";
  return (
    <span
      className={
        "inline-flex items-center rounded-full px-2.5 py-0.5 gv-kicker " +
        tone
      }
    >
      {status ?? "chưa chạy"}
    </span>
  );
}

function StaleChip({ count }: { count: number }) {
  if (count === 0) {
    return (
      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 gv-kicker bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]">
        Tươi
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 gv-kicker bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg-deep)]">
      {count} tín hiệu quá hạn
    </span>
  );
}

function NicheRow({ row }: { row: Layer0NicheFreshness }) {
  const name = row.name_vn || row.name_en || `niche ${row.niche_id}`;
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 text-sm text-[color:var(--gv-ink)]">{name}</td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {row.signal_count}
      </td>
      <td className="py-2.5 pr-4">
        <StaleChip count={row.stale_count} />
      </td>
      <td className="py-2.5 pr-4 gv-kicker text-[color:var(--gv-ink-3)]">
        {row.last_hashtag_refresh ?? "—"}
      </td>
    </tr>
  );
}

function CandidateRow({ row }: { row: Layer0Candidate }) {
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 gv-mono text-[12px] text-[color:var(--gv-ink)]">#{row.hashtag}</td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {formatVN(row.occurrences)}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink-3)]">
        {row.avg_views != null ? formatVN(row.avg_views) : "—"}
      </td>
      <td className="py-2.5 pr-4 gv-kicker text-[color:var(--gv-ink-3)]">
        {row.discovery_date ?? "—"}
      </td>
    </tr>
  );
}

function RunRow({ row }: { row: Layer0Run }) {
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 gv-kicker text-[color:var(--gv-ink-3)]">
        {relativeAge(row.started_at)}
      </td>
      <td className="py-2.5 pr-4">
        <StatusChip status={row.status} />
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {formatDurationMs(row.duration_ms)}
      </td>
      <td className="py-2.5 pr-4 gv-kicker text-[color:var(--gv-ink-3)] line-clamp-1">
        {row.error ? row.error : row.summary ? JSON.stringify(row.summary) : "—"}
      </td>
    </tr>
  );
}

export function Layer0Panel() {
  const { data, isPending, isError, error } = useAdminLayer0();

  const topStaleNiches = useMemo(
    () => (data?.niches ?? []).slice(0, 10),
    [data?.niches],
  );

  if (isPending) {
    return (
      <div
        role="status"
        aria-label="Đang tải"
        className="h-40 animate-pulse rounded-[var(--gv-radius-md)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }

  if (isError) {
    const code = (error as Error)?.message ?? "unknown";
    return (
      <p className="text-sm text-[color:var(--gv-neg-deep)]">
        Không tải được dữ liệu Layer0 ({code}).
      </p>
    );
  }

  if (!data) return null;

  const { summary } = data;
  return (
    <div className="flex flex-col gap-7">
      {/* Bignum strip */}
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
        <Bignum
          label="Lần chạy gần nhất"
          value={relativeAge(summary.last_run_at)}
          sub={summary.last_run_status ?? "chưa chạy"}
        />
        <Bignum
          label="Hashtag chờ duyệt"
          value={summary.pending_review_count}
          sub={`trên ${formatVN(summary.hashtag_map_size)} hashtag đã ánh xạ`}
        />
        <Bignum
          label="Ngách có tín hiệu quá hạn"
          value={summary.niches_with_stale_signals}
          sub={`/${summary.niches_total} dòng taxonomy`}
        />
        <Bignum
          label="Thời lượng lần chạy"
          value={formatDurationMs(summary.last_run_duration_ms)}
        />
      </div>

      {/* Niche freshness */}
      <div>
        <p className="gv-uc mb-2.5 text-[11px] font-semibold text-[color:var(--gv-ink-3)]">
          Độ tươi signal · 10 dòng taxonomy ưu tiên quá hạn trước
        </p>
        {topStaleNiches.length === 0 ? (
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Không có dòng taxonomy nào — kiểm tra bảng niche_taxonomy.
          </p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Ngách (taxonomy)
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Số tín hiệu
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Quá hạn
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Refresh hashtag gần nhất
                </th>
              </tr>
            </thead>
            <tbody>
              {topStaleNiches.map((row) => (
                <NicheRow key={row.niche_id} row={row} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pending candidates */}
      <div>
        <p className="gv-uc mb-2.5 text-[11px] font-semibold text-[color:var(--gv-ink-3)]">
          Hashtag chờ duyệt · 20 dòng đầu theo số lần xuất hiện
        </p>
        {data.pending_candidates.length === 0 ? (
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Không còn hashtag ứng viên nào trong hàng đợi duyệt.
          </p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Hashtag
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Số lần xuất hiện
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  View trung bình
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Phát hiện
                </th>
              </tr>
            </thead>
            <tbody>
              {data.pending_candidates.map((row) => (
                <CandidateRow key={row.id} row={row} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Recent runs */}
      <div>
        <p className="gv-uc mb-2.5 text-[11px] font-semibold text-[color:var(--gv-ink-3)]">
          5 lần chạy gần nhất · job batch Layer0
        </p>
        {data.recent_runs.length === 0 ? (
          <p className="text-sm text-[color:var(--gv-ink-3)]">
            Chưa có lần chạy nào — kiểm tra lịch cron batch Layer0 (Cloud Run).
          </p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Thời điểm
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Trạng thái
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Thời lượng
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[11px] font-semibold text-[color:var(--gv-ink-4)]">
                  Tóm tắt / lỗi
                </th>
              </tr>
            </thead>
            <tbody>
              {data.recent_runs.map((row) => (
                <RunRow key={row.id} row={row} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
