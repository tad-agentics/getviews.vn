/**
 * Layer0Panel — hashtag-discovery health for the admin console.
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
      <span className="gv-uc text-[10px] font-semibold text-[color:var(--gv-ink-4)]">{label}</span>
      <span className="gv-bignum text-[color:var(--gv-ink)] tabular-nums">{display}</span>
      {sub ? (
        <span className="gv-mono text-[11px] text-[color:var(--gv-ink-3)] tabular-nums">{sub}</span>
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
        "inline-flex items-center rounded-full px-2.5 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] " +
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
      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] bg-[color:var(--gv-canvas-2)] text-[color:var(--gv-ink-4)]">
        Tươi
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] bg-[color:var(--gv-neg-soft)] text-[color:var(--gv-neg-deep)]">
      {count} stale
    </span>
  );
}

function NicheRow({ row }: { row: Layer0NicheFreshness }) {
  const name = row.name_vn || row.name_en || `niche ${row.niche_id}`;
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 text-[13px] text-[color:var(--gv-ink)]">{name}</td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {row.signal_count}
      </td>
      <td className="py-2.5 pr-4">
        <StaleChip count={row.stale_count} />
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
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
      <td className="py-2.5 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
        {row.discovery_date ?? "—"}
      </td>
    </tr>
  );
}

function RunRow({ row }: { row: Layer0Run }) {
  return (
    <tr className="border-b border-[color:var(--gv-rule)] last:border-0">
      <td className="py-2.5 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
        {relativeAge(row.started_at)}
      </td>
      <td className="py-2.5 pr-4">
        <StatusChip status={row.status} />
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[12px] tabular-nums text-[color:var(--gv-ink)]">
        {formatDurationMs(row.duration_ms)}
      </td>
      <td className="py-2.5 pr-4 gv-mono text-[11px] text-[color:var(--gv-ink-3)] line-clamp-1">
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
      <p className="text-[13px] text-[color:var(--gv-neg-deep)]">
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
          sub={`/${formatVN(summary.hashtag_map_size)} đã ánh xạ`}
        />
        <Bignum
          label="Niche signal stale"
          value={summary.niches_with_stale_signals}
          sub={`/${summary.niches_total} niche`}
        />
        <Bignum
          label="Thời lượng lần chạy"
          value={formatDurationMs(summary.last_run_duration_ms)}
        />
      </div>

      {/* Niche freshness */}
      <div>
        <p className="gv-uc mb-2.5 text-[10px] font-semibold text-[color:var(--gv-ink-4)]">
          Niche freshness · top 10 stale-first
        </p>
        {topStaleNiches.length === 0 ? (
          <p className="text-[13px] text-[color:var(--gv-ink-3)]">
            Không có niche nào — kiểm tra niche_taxonomy.
          </p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Niche
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Signals
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Stale
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Refresh gần nhất
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
        <p className="gv-uc mb-2.5 text-[10px] font-semibold text-[color:var(--gv-ink-4)]">
          Hashtag chờ duyệt · top 20 theo occurrences
        </p>
        {data.pending_candidates.length === 0 ? (
          <p className="text-[13px] text-[color:var(--gv-ink-3)]">
            Không còn candidate nào trong hàng đợi.
          </p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Hashtag
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Occurrences
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Avg views
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
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
        <p className="gv-uc mb-2.5 text-[10px] font-semibold text-[color:var(--gv-ink-4)]">
          5 lần chạy gần nhất · batch/layer0
        </p>
        {data.recent_runs.length === 0 ? (
          <p className="text-[13px] text-[color:var(--gv-ink-3)]">
            Chưa có lần chạy nào — kiểm tra cron-batch-layer0 trong cron.job.
          </p>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[color:var(--gv-rule)]">
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Khi
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Status
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Thời lượng
                </th>
                <th className="py-2 pr-4 text-left gv-uc text-[9px] font-semibold text-[color:var(--gv-ink-4)]">
                  Summary / error
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
