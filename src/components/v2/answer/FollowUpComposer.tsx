import { useMemo } from "react";
import { Sparkles } from "lucide-react";
import { QueryComposer } from "@/components/v2/QueryComposer";

const FOLLOW_UP_PILL =
  "inline-flex max-w-full items-center gap-1.5 rounded-full border border-[color:var(--gv-rule)] bg-[color:var(--gv-paper)] px-3 py-1.5 text-left text-[11px] font-medium leading-snug text-[color:var(--gv-ink-2)] transition-colors hover:border-[color:var(--gv-ink)] hover:bg-[color:var(--gv-canvas-2)] disabled:pointer-events-none disabled:opacity-40";

const DEFAULT_FOLLOW_UPS = [
  "Thời điểm đăng nào tốt nhất cho các hook này?",
  "Creator nào dùng pattern này thành công nhất?",
  "Viết kịch bản 30s với hook đang thắng",
] as const;

function mergeFollowUpPrompts(suggested: string[] | undefined): string[] {
  const fromReport = (suggested ?? []).map((s) => s.trim()).filter(Boolean);
  const out: string[] = [];
  const seen = new Set<string>();
  for (const q of fromReport) {
    if (seen.has(q) || out.length >= 3) continue;
    seen.add(q);
    out.push(q);
  }
  for (const q of DEFAULT_FOLLOW_UPS) {
    if (out.length >= 3) break;
    if (!seen.has(q)) {
      seen.add(q);
      out.push(q);
    }
  }
  return out;
}

/** Phase C.1.3 — follow-up: composer + pill gợi ý (ref: không dán link/handle/mic). */
export function FollowUpComposer({
  value,
  onChange,
  onSubmit,
  disabled,
  suggestedPrompts,
  placeholder = "Hỏi thêm về kết quả này…",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  /** `related_questions` từ báo cáo — ưu tiên hiển thị, bổ sung bằng gợi ý mặc định. */
  suggestedPrompts?: string[];
  placeholder?: string;
}) {
  const prompts = useMemo(() => mergeFollowUpPrompts(suggestedPrompts), [suggestedPrompts]);

  return (
    <div className="mt-10">
      <p className="mb-3 font-mono text-[10px] uppercase tracking-wide text-[var(--gv-ink-4)]">
        Tiếp tục nghiên cứu
      </p>
      <QueryComposer
        value={value}
        onChange={onChange}
        onSubmit={onSubmit}
        placeholder={placeholder}
        showNicheCaption={false}
        disabled={disabled}
        followUpSlot={
          <>
            {prompts.map((p) => (
              <button
                key={p}
                type="button"
                disabled={disabled}
                className={FOLLOW_UP_PILL}
                onClick={() => onChange(p)}
              >
                <Sparkles className="h-3 w-3 shrink-0 text-[color:var(--gv-accent)]" aria-hidden />
                <span className="min-w-0">{p}</span>
              </button>
            ))}
          </>
        }
      />
    </div>
  );
}
