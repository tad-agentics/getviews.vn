/**
 * Phase D.6.3 — Manual trigger buttons.
 *
 * Lists the job catalog from `/admin/triggers` and renders one button per
 * job. Heavy jobs (every job currently in the catalog) go through a
 * confirm dialog — these hit Gemini + EnsembleData and cost real money,
 * so a misclick on "Run corpus ingest" can't be allowed to proceed
 * without a second tap. After a successful run the panel shows a small
 * collapsible with the response JSON so the operator can eyeball
 * inserted/skipped/errored counts without leaving the dashboard.
 *
 * The `ingest` job has a tiny inline form (CSV niche_ids + deep_pool
 * checkbox) because it's the only one with meaningful parameters an
 * operator wants to tune per-run. The others are parameter-less for
 * now; when a new job lands in the catalog with non-trivial body_schema
 * it'll need a matching form block here.
 */
import { useState } from "react";
import {
  useAdminTrigger,
  useAdminTriggerCatalog,
  type AdminTriggerJob,
  type AdminTriggerResult,
} from "@/hooks/useAdminTriggers";

type DialogState =
  | { kind: "closed" }
  | { kind: "confirm"; job: AdminTriggerJob; body: Record<string, unknown> }
  | { kind: "running"; job: AdminTriggerJob }
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
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-1">
        <span className="gv-mono text-[10px] uppercase tracking-widest text-[color:var(--gv-ink-4)]">
          niche_ids (bỏ trống = tất cả)
        </span>
        <input
          type="text"
          value={nicheCsv}
          onChange={(e) => setNicheCsv(e.target.value)}
          placeholder="1, 3, 7"
          className="rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-2 text-[14px] text-[color:var(--gv-ink)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[color:var(--gv-accent)]"
        />
        {csvError ? (
          <span className="text-[11px] text-[color:var(--gv-danger)]">{csvError}</span>
        ) : null}
      </label>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={deepPool}
          onChange={(e) => setDeepPool(e.target.checked)}
        />
        <span className="text-[12px] text-[color:var(--gv-ink-3)]">
          deep_pool (widen keyword pagination — dùng khi muốn re-overlap pool cũ sau outage)
        </span>
      </label>
      <div className="flex justify-end gap-2 pt-1">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-[color:var(--gv-rule)] px-3 py-1.5 gv-mono text-[11px] text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-canvas-2)]"
        >
          Hủy
        </button>
        <button
          type="button"
          onClick={submit}
          className="rounded-md bg-[color:var(--gv-accent)] px-3 py-1.5 gv-mono text-[11px] text-white hover:opacity-90"
        >
          Chạy ingest
        </button>
      </div>
    </div>
  );
}

function ConfirmDialog({
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
    <div className="flex flex-col gap-3">
      <p className="text-[13px] text-[color:var(--gv-ink)]">
        Chạy <span className="font-semibold">{job.label}</span>?
      </p>
      {job.heavy ? (
        <p className="text-[12px] text-[color:var(--gv-ink-3)]">
          Job này tốn Gemini / EnsembleData credits và có thể chạy vài phút. Không thể hủy giữa chừng.
        </p>
      ) : null}
      {Object.keys(body).length > 0 ? (
        <pre className="overflow-x-auto rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-2 gv-mono text-[11px] text-[color:var(--gv-ink-3)]">
          {JSON.stringify(body, null, 2)}
        </pre>
      ) : null}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-[color:var(--gv-rule)] px-3 py-1.5 gv-mono text-[11px] text-[color:var(--gv-ink-3)] hover:bg-[color:var(--gv-canvas-2)]"
        >
          Hủy
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="rounded-md bg-[color:var(--gv-accent)] px-3 py-1.5 gv-mono text-[11px] text-white hover:opacity-90"
        >
          Xác nhận chạy
        </button>
      </div>
    </div>
  );
}

function JobRow({ job }: { job: AdminTriggerJob }) {
  const [dialog, setDialog] = useState<DialogState>({ kind: "closed" });
  const [showForm, setShowForm] = useState(false);
  const trigger = useAdminTrigger();

  const startWith = (body: Record<string, unknown>) => {
    setShowForm(false);
    setDialog({ kind: "confirm", job, body });
  };

  const confirmRun = async () => {
    if (dialog.kind !== "confirm") return;
    const { body } = dialog;
    setDialog({ kind: "running", job });
    try {
      const result = await trigger.mutateAsync({ job: job.id, body });
      setDialog({ kind: "result", job, result });
    } catch (e) {
      const message = e instanceof Error ? e.message : "unknown";
      setDialog({ kind: "error", job, message });
    }
  };

  const hasParams = Object.keys(job.body_schema).length > 0;

  return (
    <div className="flex flex-col gap-2 rounded-md border border-[color:var(--gv-rule)] p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-medium text-[color:var(--gv-ink)]">{job.label}</p>
          {hasParams ? (
            <p className="mt-0.5 gv-mono text-[10px] text-[color:var(--gv-ink-4)]">
              params: {Object.keys(job.body_schema).join(", ")}
            </p>
          ) : null}
        </div>
        {dialog.kind === "closed" && !showForm ? (
          <button
            type="button"
            onClick={() => (hasParams ? setShowForm(true) : startWith({}))}
            className="shrink-0 rounded-md border border-[color:var(--gv-rule)] px-3 py-1.5 gv-mono text-[11px] text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)]"
          >
            Run
          </button>
        ) : null}
      </div>

      {showForm && job.id === "ingest" ? (
        <IngestForm onConfirm={startWith} onCancel={() => setShowForm(false)} />
      ) : null}

      {dialog.kind === "confirm" ? (
        <ConfirmDialog
          job={job}
          body={dialog.body}
          onConfirm={() => void confirmRun()}
          onCancel={() => setDialog({ kind: "closed" })}
        />
      ) : null}

      {dialog.kind === "running" ? (
        <div className="flex items-center gap-2 text-[12px] text-[color:var(--gv-ink-3)]">
          <div
            className="h-3 w-3 animate-spin rounded-full border-2 border-[color:var(--gv-accent)] border-t-transparent"
            aria-hidden
          />
          <span>Đang chạy — có thể mất vài phút, đừng đóng tab…</span>
        </div>
      ) : null}

      {dialog.kind === "result" ? (
        <div className="flex flex-col gap-1.5">
          <p className="text-[12px] text-[color:var(--gv-pos)]">Xong ✓</p>
          <pre className="max-h-64 overflow-auto rounded-md border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)] p-2 gv-mono text-[10px] text-[color:var(--gv-ink-3)]">
            {JSON.stringify(dialog.result, null, 2)}
          </pre>
          <button
            type="button"
            onClick={() => setDialog({ kind: "closed" })}
            className="self-end gv-mono text-[10px] text-[color:var(--gv-accent)] underline"
          >
            Đóng
          </button>
        </div>
      ) : null}

      {dialog.kind === "error" ? (
        <div className="flex flex-col gap-1.5">
          <p className="text-[12px] text-[color:var(--gv-danger)]">
            Lỗi: {dialog.message}
          </p>
          <button
            type="button"
            onClick={() => setDialog({ kind: "closed" })}
            className="self-end gv-mono text-[10px] text-[color:var(--gv-accent)] underline"
          >
            Đóng
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function TriggersPanel() {
  const catalog = useAdminTriggerCatalog();

  if (catalog.isLoading) {
    return (
      <div
        role="status"
        aria-label="Đang tải trigger catalog"
        className="h-32 animate-pulse rounded-md bg-[color:var(--gv-canvas-2)]"
      />
    );
  }
  if (catalog.isError) {
    const msg = catalog.error instanceof Error ? catalog.error.message : "unknown";
    return (
      <p className="text-[12px] text-[color:var(--gv-danger)]">
        Không tải được trigger catalog ({msg}).
      </p>
    );
  }
  if (!catalog.data) return null;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[12px] text-[color:var(--gv-ink-3)]">
        Chạy thủ công các pipeline định kỳ. Mỗi job có confirm dialog trước khi fire.
      </p>
      <div className="flex flex-col gap-2">
        {catalog.data.map((job) => (
          <JobRow key={job.id} job={job} />
        ))}
      </div>
    </div>
  );
}
