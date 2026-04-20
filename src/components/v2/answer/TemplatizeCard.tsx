import { Btn } from "@/components/v2/Btn";
import { logUsage } from "@/lib/logUsage";

/** Phase C.1.3 — dark rail card (SaveCard → TemplatizeCard per phase-c-plan). */
export function TemplatizeCard({ sessionId }: { sessionId: string | null }) {
  return (
    <div className="rounded-lg border border-[var(--gv-ink)] bg-[var(--gv-ink)] p-4 text-[var(--gv-canvas)]">
      <p className="font-mono text-[10px] uppercase tracking-wide opacity-80">Lưu nghiên cứu</p>
      <p className="mt-1 text-sm">Biến báo cáo này thành template cho các tuần sau.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Btn
          variant="secondary"
          size="sm"
          type="button"
          disabled={!sessionId}
          onClick={() =>
            logUsage("templatize_click", { surface: "answer_shell", session_id: sessionId })
          }
        >
          Lưu
        </Btn>
        <Btn variant="ghost" size="sm" type="button" className="text-[var(--gv-canvas)]">
          Chia sẻ
        </Btn>
      </div>
    </div>
  );
}
