import { QueryComposer } from "@/components/v2/QueryComposer";

/** Phase C.1.3 — follow-up slot: kicker + brutal composer (answer.jsx FollowUpComposer). */
export function FollowUpComposer({
  value,
  onChange,
  onSubmit,
  nicheLabel,
  disabled,
  placeholder = "Câu hỏi tiếp theo…",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  nicheLabel?: string;
  disabled?: boolean;
  placeholder?: string;
}) {
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
        nicheLabel={nicheLabel}
        disabled={disabled}
      />
    </div>
  );
}
