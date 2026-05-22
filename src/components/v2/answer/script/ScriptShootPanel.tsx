/**
 * Wave 2 — in-session shoot panel (migrated from ShootScreen).
 */
import { Loader2 } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import { ShotReferenceStrip } from "@/components/v2/ShotReferenceStrip";
import { useScriptDraft } from "@/hooks/useScriptSave";
import type { ScriptShot } from "@/lib/api-types";
import { overlayStyleVi } from "@/lib/constants/enum-labels-vi";

export function ScriptShootPanel({
  draftId,
  onClose,
}: {
  draftId: string;
  onClose: () => void;
}) {
  const { data, isPending, isError, error } = useScriptDraft(draftId);
  const draft = data?.draft ?? null;

  if (isPending) {
    return (
      <div
        className="flex min-h-[32vh] items-center justify-center gap-3 rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6"
        role="status"
        aria-label="Đang tải kịch bản"
      >
        <Loader2 className="h-5 w-5 animate-spin text-[color:var(--gv-accent)]" strokeWidth={1.5} />
        <span className="gv-mono text-[13px] text-[color:var(--gv-ink-3)]">Đang tải kịch bản…</span>
      </div>
    );
  }

  if (isError || !draft) {
    return (
      <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
        <p className="gv-tight m-0 text-lg text-[color:var(--gv-neg-deep)]">Không mở được kịch bản</p>
        <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">
          {error?.message ?? "Bản nháp không còn tồn tại hoặc không thuộc quyền truy cập của bạn."}
        </p>
        <Btn className="mt-4" type="button" variant="ghost" onClick={onClose}>
          Đóng chế độ quay
        </Btn>
      </div>
    );
  }

  return (
    <section
      className="rounded-[var(--gv-radius-md)] border-2 border-[color:var(--gv-ink)] bg-[color:var(--gv-paper)] p-4"
      aria-label="Chế độ quay"
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-[color:var(--gv-rule)] pb-3">
        <p className="gv-mono m-0 text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--gv-accent)]">
          CHẾ ĐỘ QUAY
        </p>
        <Btn variant="ghost" size="sm" type="button" onClick={onClose}>
          Đóng
        </Btn>
      </div>
      <header className="border-b-2 border-[color:var(--gv-ink)] pb-4">
        <div className="gv-mono gv-uc mb-1.5 text-[10px] font-semibold tracking-[0.18em] text-[color:var(--gv-accent)]">
          HOOK · {draft.tone} · {draft.duration_sec}s
        </div>
        <h2 className="gv-serif m-0 text-[clamp(22px,3.4vw,30px)] leading-[1.2] text-[color:var(--gv-ink)]">
          {draft.hook}
        </h2>
      </header>
      <ol className="mt-4 flex flex-col gap-4 p-0">
        {(draft.shots ?? []).map((s, i) => (
          <ShootShotBlock key={i} shot={s} index={i} />
        ))}
      </ol>
    </section>
  );
}

function ShootShotBlock({ shot, index }: { shot: ScriptShot; index: number }) {
  const t0 = Math.round(shot.t0);
  const t1 = Math.round(shot.t1);
  const timePrefix = `${String(t0).padStart(2, "0")}-${String(t1).padStart(2, "0")}s`;
  const overlay = (shot.overlay ?? "NONE").trim();
  const refs = shot.references ?? [];
  return (
    <li className="list-none overflow-hidden rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-canvas-2)]">
      <div className="p-4">
        <div className="gv-mono mb-2 text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)]">
          Cảnh {index + 1} · {timePrefix} · {shot.cam}
        </div>
        <p className="gv-serif m-0 text-[18px] leading-[1.35] text-[color:var(--gv-ink)]">
          {shot.voice || "(không có voice)"}
        </p>
        {shot.viz ? (
          <p className="gv-mono mt-3 text-[12px] leading-[1.45] text-[color:var(--gv-ink-3)]">
            <span className="gv-uc mr-2 text-[10px] tracking-[0.12em] text-[color:var(--gv-ink-4)]">
              Viz
            </span>
            {shot.viz}
          </p>
        ) : null}
        {overlay && overlay !== "NONE" ? (
          <p className="gv-mono mt-1.5 text-[12px] leading-[1.45] text-[color:var(--gv-ink-3)]">
            <span className="gv-uc mr-2 text-[10px] tracking-[0.12em] text-[color:var(--gv-ink-4)]">
              Overlay
            </span>
            {overlayStyleVi(overlay, overlay)}
          </p>
        ) : null}
      </div>
      <ShotReferenceStrip refs={refs} density="block" />
    </li>
  );
}
