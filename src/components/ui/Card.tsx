import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function Card({ children, className = '', hover, onClick }: CardProps) {
  const baseStyles = 'bg-[var(--surface)] border border-[var(--border)] rounded-xl p-4';
  const hoverStyles = hover
    ? 'cursor-pointer transition-all duration-[120ms] hover:border-[var(--purple)] hover:bg-[var(--purple-light)]'
    : '';

  return (
    <div className={`${baseStyles} ${hoverStyles} ${className}`} onClick={onClick}>
      {children}
    </div>
  );
}
