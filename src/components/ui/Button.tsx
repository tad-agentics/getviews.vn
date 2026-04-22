import { type ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outlined' | 'danger';
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, variant = 'primary', fullWidth, className = '', ...props }, ref) => {
    const baseStyles = 'px-6 py-3 rounded-lg font-medium transition-all duration-[120ms] ease-out active:scale-95';

    const variants = {
      primary:
        'bg-[color:var(--gv-accent)] text-white hover:bg-[color:var(--gv-accent-deep)] disabled:opacity-50',
      secondary:
        'bg-[color:var(--surface)] border border-[color:var(--border)] text-[color:var(--ink)] hover:bg-[color:var(--surface-alt)] hover:border-[color:var(--gv-ink)]',
      outlined:
        'bg-[color:var(--gv-canvas-2)] border border-[color:var(--gv-rule)] text-[color:var(--gv-ink)] hover:bg-[color:var(--gv-rule-2)]',
      danger: 'bg-[color:var(--danger)] text-white hover:opacity-90',
    };

    const widthClass = fullWidth ? 'w-full' : '';

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${widthClass} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';