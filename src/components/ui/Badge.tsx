import { type ReactNode } from 'react';

/**
 * The `purple` variant is deprecated as of Phase D.4.1.a. Call sites
 * will swap to the `default` variant across D.4.1.b–f before D.4.2
 * drops this shim entirely. Keeping the value in the type union so
 * existing consumers continue to typecheck during the sweep; the
 * runtime warning is suppressed in production so end-users never see
 * it, but dev / CI environments get a clear signal on every render.
 */
type BadgeVariant = 'default' | 'purple' | 'accent' | 'success' | 'danger';

interface BadgeProps {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

function warnDeprecatedPurple(): void {
  if (typeof console === 'undefined' || process.env.NODE_ENV === 'production') return;
  console.warn(
    "[Badge] the `purple` variant is deprecated (Phase D.4). " +
      "Use the `default` or `accent` variant instead.",
  );
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  if (variant === 'purple') warnDeprecatedPurple();

  const variants: Record<BadgeVariant, string> = {
    default: 'bg-[color:var(--surface-alt)] text-[color:var(--gv-ink-3)]',
    // Shim: render `purple` with `default` styles until all call sites migrate.
    purple: 'bg-[color:var(--surface-alt)] text-[color:var(--gv-ink-3)]',
    accent:
      'bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent)] border border-[color:var(--gv-rule)]',
    success: 'bg-[color:var(--success)]/10 text-[color:var(--success)]',
    danger: 'bg-[color:var(--danger)]/10 text-[color:var(--danger)]',
  };

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
