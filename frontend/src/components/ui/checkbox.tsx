import React from 'react';
import { cn } from '../../lib/utils';

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, ...props }, ref) => {
    return (
      <label className="inline-flex items-center space-x-2 cursor-pointer text-sm font-medium text-foreground">
        <input
          type="checkbox"
          ref={ref}
          className={cn(
            'h-4 w-4 rounded border-input text-primary focus:ring-ring focus:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
            className
          )}
          {...props}
        />
        {label && <span>{label}</span>}
      </label>
    );
  }
);
Checkbox.displayName = 'Checkbox';
