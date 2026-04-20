import { type ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'purple' | 'accent' | 'success' | 'danger';
  className?: string;
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  const variants = {
    default: 'bg-[var(--surface-alt)] text-[var(--ink-soft)]',
    purple: 'bg-[var(--purple-light)] text-[var(--purple)]',
    accent:
      'bg-[color:var(--gv-accent-soft)] text-[color:var(--gv-accent)] border border-[color:var(--gv-rule)]',
    success: 'bg-[var(--success)]/10 text-[var(--success)]',
    danger: 'bg-[var(--danger)]/10 text-[var(--danger)]',
  };

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
