import { ArrowLeft, Loader2 } from "lucide-react";
import { useNavigate, useParams } from "react-router";

import { AppLayout } from "@/components/AppLayout";
import { Btn } from "@/components/v2/Btn";
import { ShotReferenceStrip } from "@/components/v2/ShotReferenceStrip";
import { TopBar } from "@/components/v2/TopBar";
import { useScriptDraft } from "@/hooks/useScriptSave";
import type { ScriptShot } from "@/lib/api-types";
import { overlayStyleVi } from "@/lib/constants/enum-labels-vi";

/**
 * Phase D.1.1 — "Chế độ quay" read-only view. Optimised for phone-in-tripod
 * reading while filming: large serif voice line, mono time prefix, no
 * controls that could be bumped during a take. Keeps total LOC minimal to
 * avoid dragging ScriptScreen's bundle through the lazy boundary.
 */
export default function ShootScreen() {
  const { draftId } = useParams<{ draftId: string }>();
  const navigate = useNavigate();
  const { data, isPending, isError, error } = useScriptDraft(draftId);

  const draft = data?.draft ?? null;

  return (
    <AppLayout enableMobileSidebar>
      <TopBar
        kicker="CHẾ ĐỘ QUAY"
        title={draft?.topic || "Kịch bản"}
        right={
          <Btn variant="ghost" size="sm" type="button" onClick={() => navigate("/app/script")}>
            <ArrowLeft className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            Quay lại
          </Btn>
        }
      />
      <main className="gv-route-main gv-route-main--720 mx-auto w-full max-w-[720px] px-4">
        {isPending ? (
          <div
            className="flex min-h-[40vh] items-center justify-center gap-3 text-[color:var(--gv-ink-3)]"
            role="status"
            aria-label="Đang tải kịch bản"
          >
            <Loader2 className="h-5 w-5 animate-spin text-[color:var(--gv-accent)]" strokeWidth={1.5} />
            <span className="gv-mono text-[13px]">Đang tải kịch bản…</span>
          </div>
        ) : isError || !draft ? (
          <div className="rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] p-6">
            <p className="gv-tight m-0 text-lg text-[color:var(--gv-neg-deep)]">
              Không mở được kịch bản
            </p>
            <p className="mt-2 text-sm text-[color:var(--gv-ink-3)]">
              {error?.message ?? "Kịch bản không còn tồn tại hoặc không thuộc quyền truy cập của bạn."}
            </p>
            <Btn
              className="mt-4"
              type="button"
              variant="ghost"
              onClick={() => navigate("/app/script")}
            >
              Về Xưởng Viết
            </Btn>
          </div>
        ) : (
          <article className="flex flex-col gap-5 py-6">
            <header className="border-b-2 border-[color:var(--gv-ink)] pb-4">
              <div className="gv-mono gv-uc mb-1.5 text-[10px] font-semibold tracking-[0.18em] text-[color:var(--gv-accent)]">
                HOOK · {draft.tone} · {draft.duration_sec}s
              </div>
              <h1 className="gv-serif m-0 text-[clamp(22px,3.4vw,30px)] leading-[1.2] text-[color:var(--gv-ink)]">
                {draft.hook}
              </h1>
            </header>
            <ol className="flex flex-col gap-4 p-0">
              {(draft.shots ?? []).map((s, i) => (
                <ShotBlock key={i} shot={s} index={i} />
              ))}
            </ol>
          </article>
        )}
      </main>
    </AppLayout>
  );
}

function ShotBlock({ shot, index }: { shot: ScriptShot; index: number }) {
  const t0 = Math.round(shot.t0);
  const t1 = Math.round(shot.t1);
  const timePrefix = `${String(t0).padStart(2, "0")}-${String(t1).padStart(2, "0")}s`;
  const overlay = (shot.overlay ?? "NONE").trim();
  const refs = shot.references ?? [];
  return (
    <li className="list-none overflow-hidden rounded-[var(--gv-radius-md)] border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)]">
      <div className="p-4">
        <div className="gv-mono mb-2 text-[11px] uppercase tracking-[0.1em] text-[color:var(--gv-ink-3)]">
          Shot {index + 1} · {timePrefix} · {shot.cam}
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
