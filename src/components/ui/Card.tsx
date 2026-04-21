import { type ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({ children, className = '', hover, onClick }: CardProps) {
  const baseStyles = 'bg-[color:var(--surface)] border border-[color:var(--border)] rounded-xl p-4';
  const hoverStyles = hover
    ? 'cursor-pointer transition-all duration-[120ms] hover:border-[color:var(--gv-accent)] hover:bg-[color:var(--gv-accent-soft)]'
    : '';

  return (
    <div className={`${baseStyles} ${hoverStyles} ${className}`} onClick={onClick}>
      {children}
    </div>
  );
}
