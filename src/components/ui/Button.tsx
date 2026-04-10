import { ButtonHTMLAttributes, forwardRef } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outlined' | 'danger';
  fullWidth?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, variant = 'primary', fullWidth, className = '', ...props }, ref) => {
    const baseStyles = 'px-6 py-3 rounded-lg font-medium transition-all duration-[120ms] ease-out active:scale-95';

    const variants = {
      primary: 'gradient-cta hover:opacity-90 disabled:opacity-50',
      secondary: 'bg-[var(--surface)] border border-[var(--border)] text-[var(--ink)] hover:bg-[var(--surface-alt)] hover:border-[var(--border-active)]',
      outlined: 'bg-transparent border border-[var(--border)] text-[var(--ink)] hover:bg-[var(--surface-alt)] hover:border-[var(--border-active)]',
      danger: 'bg-[var(--danger)] text-white hover:opacity-90',
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