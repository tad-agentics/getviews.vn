/**
 * Wave 2 — save / shoot / export actions for Answer script turns.
 */
import { useState } from "react";
import { Download, Film, Loader2, Save } from "lucide-react";

import { Btn } from "@/components/v2/Btn";
import { ScriptExportModal } from "@/routes/_app/script/ScriptExportModal";
import { useScriptExport, useScriptSave } from "@/hooks/useScriptSave";
import type { ScriptExportFormat, ScriptReportPayload, ScriptShot, ScriptTone } from "@/lib/api-types";

function reportToSaveBody(report: ScriptReportPayload, sessionId: string | null) {
  return {
    topic: report.topic,
    hook: report.hook,
    hook_delay_ms: report.hook_delay_ms,
    duration_sec: report.duration,
    tone: report.tone as ScriptTone,
    shots: report.shots as ScriptShot[],
    source_session_id: sessionId,
  };
}

export function ScriptActionsBar({
  report,
  sessionId,
  onShoot,
  onDraftSaved,
  savedDraftId,
}: {
  report: ScriptReportPayload;
  sessionId: string | null;
  onShoot: (draftId: string) => void;
  onDraftSaved?: (draftId: string) => void;
  savedDraftId: string | null;
}) {
  const save = useScriptSave();
  const exportDraft = useScriptExport();
  const [exportOpen, setExportOpen] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const draftId = savedDraftId ?? save.data?.draft_id ?? null;

  const handleSave = () => {
    save.mutate(reportToSaveBody(report, sessionId), {
      onSuccess: (res) => {
        setBanner("Đã lưu bản nháp ✓");
        onDraftSaved?.(res.draft_id);
      },
      onError: (e) => setBanner(e.message || "Không lưu được bản nháp"),
    });
  };

  const handleExport = (format: ScriptExportFormat) => {
    if (!draftId) {
      setBanner("Lưu bản nháp trước khi xuất file.");
      return;
    }
    exportDraft.mutate(
      { draftId, format },
      {
        onSuccess: (res) => {
          const blob = new Blob([res.text], { type: res.mimeType });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `kich-ban${res.fileExt}`;
          a.click();
          URL.revokeObjectURL(url);
          setExportOpen(false);
          setBanner("Đã tải file ✓");
        },
        onError: (e) => setBanner(e.message || "Xuất file thất bại"),
      },
    );
  };

  return (
    <div className="flex flex-col gap-2 border-t border-[color:var(--gv-rule)] pt-4">
      <div className="flex flex-wrap gap-2">
        <Btn
          variant="ghost"
          size="sm"
          type="button"
          className="min-h-[44px] gap-1.5"
          disabled={save.isPending}
          onClick={handleSave}
        >
          {save.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={2} aria-hidden />
          ) : (
            <Save className="h-4 w-4" strokeWidth={2} aria-hidden />
          )}
          Lưu bản nháp
        </Btn>
        {draftId ? (
          <>
            <Btn
              variant="ink"
              size="sm"
              type="button"
              className="min-h-[44px] gap-1.5"
              onClick={() => onShoot(draftId)}
            >
              <Film className="h-4 w-4" strokeWidth={2} aria-hidden />
              Chế độ quay
            </Btn>
            <Btn
              variant="ghost"
              size="sm"
              type="button"
              className="min-h-[44px] gap-1.5"
              onClick={() => setExportOpen(true)}
            >
              <Download className="h-4 w-4" strokeWidth={2} aria-hidden />
              Xuất file
            </Btn>
          </>
        ) : null}
      </div>
      {banner ? (
        <p className="gv-mono m-0 text-[11px] text-[color:var(--gv-ink-3)]">{banner}</p>
      ) : null}
      <ScriptExportModal
        open={exportOpen}
        busy={exportDraft.isPending}
        onClose={() => setExportOpen(false)}
        onExport={handleExport}
      />
    </div>
  );
}
