/**
 * StepSpinner — rotating ⟳ CSS animation (1s, --purple) → ✓ on complete.
 * Purely CSS-driven, no JS timers.
 */

interface Props {
  done?: boolean;
  size?: number;
}

export function StepSpinner({ done = false, size = 14 }: Props) {
  if (done) {
    return (
      <span
        className="inline-flex items-center justify-center rounded-full text-[var(--purple)]"
        style={{ width: size, height: size, fontSize: size * 0.9 }}
        aria-label="Xong"
      >
        ✓
      </span>
    );
  }

  return (
      <svg
        className="inline-block animate-spin text-[var(--purple)]"
        style={{ width: size, height: size }}
        viewBox="0 0 24 24"
        fill="none"
        aria-label="Đang xử lý"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
  );
}
