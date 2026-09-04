import React, { createContext, useState } from 'react';
import { cn } from '../../lib/utils';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type?: 'success' | 'error' | 'info';
  title: string;
  description?: string;
}

interface ToastContextType {
  toast: (message: Omit<ToastMessage, 'id'>) => void;
}

export const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const toast = (message: Omit<ToastMessage, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast = { ...message, id };
    setToasts((prev) => [...prev, newToast]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-md w-full px-4 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              'pointer-events-auto flex items-start space-x-3 rounded-lg border p-4 shadow-md backdrop-blur-sm transition-all animate-in slide-in-from-bottom-5',
              t.type === 'success' && 'bg-emerald-500/10 border-emerald-500/20 text-emerald-900 dark:text-emerald-300',
              t.type === 'error' && 'bg-destructive/10 border-destructive/20 text-destructive',
              (!t.type || t.type === 'info') && 'bg-card border-border text-card-foreground'
            )}
          >
            {t.type === 'success' && <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />}
            {t.type === 'error' && <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />}
            {(!t.type || t.type === 'info') && <Info className="h-5 w-5 text-primary shrink-0 mt-0.5" />}
            <div className="flex-1 text-sm">
              <h5 className="font-semibold">{t.title}</h5>
              {t.description && <p className="text-xs opacity-90 mt-0.5">{t.description}</p>}
            </div>
            <button
              onClick={() => setToasts((prev) => prev.filter((item) => item.id !== t.id))}
              className="opacity-70 hover:opacity-100"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}


