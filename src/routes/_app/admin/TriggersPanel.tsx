/**
 * Phase D.6.3 — Manual trigger buttons (UIUX reference-aligned).
 *
 * Uses the shared Btn component for ink / ghost / accent variants and
 * the gv-kicker + chip palette from the reference. Each job is a card
 * with a confirm flow gated by a dialog-style inline block (not a
 * global modal — the reference keeps destructive confirmations inline
 * per screen so ops never loses context).
 */
import { useEffect, useState } from "react";
import { Btn } from "@/components/v2/Btn";
import {
  useAdminJobPoll,
  useAdminTrigger,
  useAdminTriggerCatalog,
  type AdminTriggerJob,
  type AdminTriggerResult,
} from "@/hooks/useAdminTriggers";

type DialogState =
  | { kind: "closed" }
  | { kind: "confirm"; job: AdminTriggerJob; body: Record<string, unknown> }
  // `polling` — backend accepted the job and returned a job_id; we're
  // waiting on the /admin/jobs/:id poll loop.
  | { kind: "polling"; job: AdminTriggerJob; jobId: string }
  | { kind: "result"; job: AdminTriggerJob; result: AdminTriggerResult }
  | { kind: "error"; job: AdminTriggerJob; message: string };

function parseCsvInts(raw: string): number[] | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const parts = trimmed.split(",").map((s) => s.trim()).filter(Boolean);
  const nums: number[] = [];
  for (const p of parts) {
    const n = Number(p);
    if (!Number.isFinite(n) || n <= 0 || !Number.isInteger(n)) return null;
    nums.push(n);
  }
  return nums.length > 0 ? nums : null;
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="gv-uc text-[10px] font-semibold text-[color:var(--gv-ink-4)]">
      {children}
    </span>
  );
}

function IngestForm({
  onConfirm,
  onCancel,
}: {
  onConfirm: (body: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [nicheCsv, setNicheCsv] = useState("");
  const [deepPool, setDeepPool] = useState(false);
  const [csvError, setCsvError] = useState<string | null>(null);

  const submit = () => {
    const niches = nicheCsv.trim() === "" ? null : parseCsvInts(nicheCsv);
    if (nicheCsv.trim() !== "" && niches === null) {
      setCsvError("Chỉ nhập các ID số dương, cách nhau bằng dấu phẩy.");
      return;
    }
    setCsvError(null);
    onConfirm({ niche_ids: niches, deep_pool: deepPool });
  };

  return (
    <div className="flex flex-col gap-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4">
      <label className="flex flex-col gap-1.5">
        <FieldLabel>niche_ids (bỏ trống = tất cả)</FieldLabel>
        <input
          type="text"
          value={nicheCsv}
          onChange={(e) => setNicheCsv(e.target.value)}
          placeholder="1, 3, 7"
          className="rounded-[var(--gv-radius-sm)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-[14px] text-[color:var(--gv-ink)] placeholder:text-[color:var(--gv-ink-4)] gv-focus"
        />
        {csvError ? (
          <span className="text-[12px] text-[color:var(--gv-danger)]">{csvError}</span>
        ) : null}
      </label>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={deepPool}
          onChange={(e) => setDeepPool(e.target.checked)}
          className="accent-[color:var(--gv-accent)]"
        />
        <span className="text-[12px] text-[color:var(--gv-ink-3)]">
          <span className="gv-mono">deep_pool</span> — widen keyword pagination. Dùng khi muốn re-overlap pool cũ sau outage.
        </span>
      </label>
      <div className="flex justify-end gap-2">
        <Btn variant="ghost" size="sm" onClick={onCancel}>Hủy</Btn>
        <Btn variant="accent" size="sm" onClick={submit}>Chạy ingest</Btn>
      </div>
    </div>
  );
}

function ConfirmBlock({
  job,
  body,
  onConfirm,
  onCancel,
}: {
  job: AdminTriggerJob;
  body: Record<string, unknown>;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4">
      <p className="text-[13px] text-[color:var(--gv-ink)]">
        Chạy <span className="font-semibold">{job.label}</span>?
      </p>
      {job.heavy ? (
        <p className="text-[12px] leading-relaxed text-[color:var(--gv-ink-3)]">
          Job này tốn Gemini / EnsembleData credits và có thể chạy vài phút. Không thể hủy giữa chừng.
        </p>
      ) : null}
      {Object.keys(body).length > 0 ? (
        <pre className="overflow-x-auto rounded-[var(--gv-radius-sm)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
          {JSON.stringify(body, null, 2)}
        </pre>
      ) : null}
      <div className="flex justify-end gap-2">
        <Btn variant="ghost" size="sm" onClick={onCancel}>Hủy</Btn>
        <Btn variant="ink" size="sm" onClick={onConfirm}>Xác nhận chạy</Btn>
      </div>
    </div>
  );
}

function ResultBlock({
  result,
  onClose,
}: {
  result: AdminTriggerResult;
  onClose: () => void;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-pos-soft)] p-4">
      <p className="gv-kicker gv-kicker--dot gv-kicker--pos">Xong — kết quả</p>
      <pre className="max-h-64 overflow-auto rounded-[var(--gv-radius-sm)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-2 gv-mono text-[10px] text-[color:var(--gv-ink-3)]">
        {JSON.stringify(result, null, 2)}
      </pre>
      <div className="flex justify-end">
        <Btn variant="ghost" size="sm" onClick={onClose}>Đóng</Btn>
      </div>
    </div>
  );
}

function JobRow({ job }: { job: AdminTriggerJob }) {
  const [dialog, setDialog] = useState<DialogState>({ kind: "closed" });
  const [showForm, setShowForm] = useState(false);
  const trigger = useAdminTrigger();

  // Pull polling state only when we're in the polling dialog state.
  // The hook fires a query with enabled=false when jobId is null so
  // we don't waste network for idle rows.
  const pollingId = dialog.kind === "polling" ? dialog.jobId : null;
  const poll = useAdminJobPoll(pollingId);

  // Transition out of polling when the backend row lands on a terminal
  // status. Running this in a useEffect (not directly in render) keeps
  // the state machine legal — React can't setState during render.
  useEffect(() => {
    if (dialog.kind !== "polling") return;
    const row = poll.data?.job;
    if (!row) return;
    if (row.result_status === "ok") {
      setDialog({
        kind: "result",
        job: dialog.job,
        result: (row.result_json ?? { ok: true }) as AdminTriggerResult,
      });
    } else if (row.result_status === "error") {
      setDialog({
        kind: "error",
        job: dialog.job,
        message: row.error_message ?? "unknown_error",
      });
    }
    // queued / running keep us in the polling state.
  }, [dialog, poll.data]);

  const startWith = (body: Record<string, unknown>) => {
    setShowForm(false);
    setDialog({ kind: "confirm", job, body });
  };

  const confirmRun = async () => {
    if (dialog.kind !== "confirm") return;
    const { body } = dialog;
    try {
      const res = await trigger.mutateAsync({ job: job.id, body });
      if (res.job_id) {
        // Normal async path — hand off to the poll loop.
        setDialog({ kind: "polling", job, jobId: res.job_id });
      } else if (res.status === "ok" && res.result) {
        // Backend audit insert failed; it ran sync and returned the
        // payload inline.
        setDialog({ kind: "result", job, result: res.result });
      } else {
        setDialog({ kind: "error", job, message: "unexpected_response" });
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "unknown";
      setDialog({ kind: "error", job, message });
    }
  };

  const hasParams = Object.keys(job.body_schema).length > 0;

  return (
    <article className="flex flex-col gap-3 rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="gv-serif text-[15px] text-[color:var(--gv-ink)]">{job.label}</p>
          {hasParams ? (
            <p className="mt-1 gv-mono text-[11px] text-[color:var(--gv-ink-4)]">
              params · {Object.keys(job.body_schema).join(", ")}
            </p>
          ) : null}
          {job.heavy ? (
            <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-full bg-[color:var(--gv-accent-soft)] px-2 py-0.5 gv-mono text-[10px] font-semibold uppercase tracking-[0.08em] text-[color:var(--gv-accent-deep)]">
              heavy
            </span>
          ) : null}
        </div>
        {dialog.kind === "closed" && !showForm ? (
          <Btn
            variant="ghost"
            size="sm"
            onClick={() => (hasParams ? setShowForm(true) : startWith({}))}
          >
            Run
          </Btn>
        ) : null}
      </div>

      {showForm && job.id === "ingest" ? (
        <IngestForm onConfirm={startWith} onCancel={() => setShowForm(false)} />
      ) : null}

      {dialog.kind === "confirm" ? (
        <ConfirmBlock
          job={job}
          body={dialog.body}
          onConfirm={() => void confirmRun()}
          onCancel={() => setDialog({ kind: "closed" })}
        />
      ) : null}

      {dialog.kind === "polling" ? (
        <div className="flex flex-col gap-1.5 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] px-4 py-3">
          <div className="flex items-center gap-2">
            <div
              className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-[color:var(--gv-accent)] border-t-transparent"
              aria-hidden
            />
            <span className="gv-mono text-[12px] text-[color:var(--gv-ink-3)]">
              {poll.data?.job?.result_status === "running"
                ? "Đang chạy — có thể đóng tab, kết quả sẽ xuất hiện ở Action log."
                : "Đã nhận — đang chờ worker pick up…"}
            </span>
          </div>
          <span className="gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
            job_id · {dialog.jobId.slice(0, 8)}… · poll mỗi 3s
          </span>
        </div>
      ) : null}

      {dialog.kind === "result" ? (
        <ResultBlock result={dialog.result} onClose={() => setDialog({ kind: "closed" })} />
      ) : null}

      {dialog.kind === "error" ? (
        <div className="flex items-center justify-between gap-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-4">
          <p className="gv-mono text-[12px] text-[color:var(--gv-danger)]">
            Lỗi · {dialog.message}
          </p>
          <Btn variant="ghost" size="sm" onClick={() => setDialog({ kind: "closed" })}>
            Đóng
          </Btn>
        </div>
      ) : null}
    </article>
  );
}

export function TriggersPanel() {
  const catalog = useAdminTriggerCatalog();

  if (catalog.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải trigger catalog"
        className="h-40 animate-pulse rounded-[var(--gv-radius-lg)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (catalog.isError) {
    const msg = catalog.error instanceof Error ? catalog.error.message : "unknown";
    return (
      <p className="text-[13px] text-[color:var(--gv-danger)]">
        Không tải được trigger catalog ({msg}).
      </p>
    );
  }
  if (!catalog.data) return null;

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {catalog.data.map((job) => (
        <JobRow key={job.id} job={job} />
      ))}
    </div>
  );
}
