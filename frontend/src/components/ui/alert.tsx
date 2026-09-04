import React from 'react';
import { cn } from '../../lib/utils';
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react';

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'success' | 'warning' | 'destructive';
  title?: string;
}

export function Alert({ className, variant = 'info', title, children, ...props }: AlertProps) {
  const variants = {
    info: 'bg-blue-500/10 border-blue-500/20 text-blue-700 dark:text-blue-400 icon:text-blue-500',
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-700 dark:text-emerald-400 icon:text-emerald-500',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-700 dark:text-amber-400 icon:text-amber-500',
    destructive: 'bg-destructive/10 border-destructive/20 text-destructive dark:text-destructive icon:text-destructive',
  };

  const icons = {
    info: Info,
    success: CheckCircle2,
    warning: AlertTriangle,
    destructive: AlertCircle,
  };

  const Icon = icons[variant];

  return (
    <div
      role="alert"
      className={cn('relative w-full rounded-lg border p-4 text-sm flex gap-3', variants[variant], className)}
      {...props}
    >
      <Icon className="h-5 w-5 shrink-0" />
      <div>
        {title && <h5 className="font-medium leading-none tracking-tight mb-1">{title}</h5>}
        <div className="text-sm opacity-90">{children}</div>
      </div>
    </div>
  );
}
