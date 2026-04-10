type ErrorBannerProps = {
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
};

export function ErrorBanner({ message, onRetry, retryLabel = "Thử lại" }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-sm text-[var(--danger)]">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="min-h-[44px] shrink-0 rounded-lg bg-[var(--purple)] px-4 text-sm font-medium text-white transition-opacity duration-[120ms] hover:opacity-90"
        >
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}
