// Renders inline in the chat thread when the user hits their monthly analysis limit.
// Never a modal. Never disables the text input.
interface AnalysisLimitCardProps {
  onNavigatePricing: () => void;
}

export function AnalysisLimitCard({ onNavigatePricing }: AnalysisLimitCardProps) {
  return (
    <div
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
      role="status"
      aria-live="polite"
    >
      <p className="mb-1 text-sm font-medium text-[var(--ink)]">
        Bạn đã dùng hết phân tích tháng này.
      </p>
      <p className="mb-3 text-xs text-[var(--ink-soft)]">
        Nâng cấp hoặc mở thêm phân tích để tiếp tục — browse và câu hỏi thường vẫn miễn phí.
      </p>
      <button
        type="button"
        onClick={onNavigatePricing}
        className="inline-flex text-sm font-semibold text-[var(--purple)] hover:underline"
      >
        Mở thêm phân tích →
      </button>
    </div>
  );
}
