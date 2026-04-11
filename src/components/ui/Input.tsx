import { type InputHTMLAttributes, forwardRef, type TextareaHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', error, ...props }, ref) => {
    const baseStyles = 'w-full px-4 py-3 rounded-lg border bg-[var(--surface)] text-[var(--ink)] placeholder:text-[var(--faint)] transition-all duration-[120ms]';
    const stateStyles = error
      ? 'border-[var(--danger)]'
      : 'border-[var(--border)] focus:border-[var(--purple)] focus:outline-none focus:ring-1 focus:ring-[var(--purple)]';

    return (
      <input
        ref={ref}
        className={`${baseStyles} ${stateStyles} ${className}`}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = '', error, ...props }, ref) => {
    const baseStyles = 'w-full px-4 py-3 rounded-lg border bg-[var(--surface)] text-[var(--ink)] placeholder:text-[var(--faint)] transition-all duration-[120ms] resize-none';
    const stateStyles = error
      ? 'border-[var(--danger)]'
      : 'border-[var(--border)] focus:border-[var(--purple)] focus:outline-none focus:ring-1 focus:ring-[var(--purple)]';

    return (
      <textarea
        ref={ref}
        className={`${baseStyles} ${stateStyles} ${className}`}
        {...props}
      />
    );
  }
);

Textarea.displayName = 'Textarea';
