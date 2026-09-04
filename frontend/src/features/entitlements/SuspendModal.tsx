import { useState } from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { apiClient } from '../../lib/api-client';
import { X, PauseCircle, AlertCircle } from 'lucide-react';
import { AccessEntitlement } from '../../types';

interface SuspendModalProps {
  item: AccessEntitlement | null;
  companyId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function SuspendModal({ item, companyId, isOpen, onClose, onSuccess }: SuspendModalProps) {
  const [reason, setReason] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !item) return null;

  const handleSuspend = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await apiClient.post(`/entitlements/${item.id}/suspend/`, {
        company_id: companyId,
        reason: reason.trim(),
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr?.detail || 'Failed to suspend access entitlement.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card shadow-2xl text-card-foreground p-6">
        <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <PauseCircle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Suspend Access</h3>
              <p className="text-xs font-mono text-muted-foreground">{item.reference}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-muted-foreground hover:bg-accent hover:text-foreground transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <p className="text-xs text-muted-foreground mb-4">
          Suspending access blocks active and future network authorizations. Note that continuous plan validity clocks continue while suspended.
        </p>

        <form onSubmit={handleSuspend} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5">
              Suspension Reason (Optional)
            </label>
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Investigation, billing dispute, customer request..."
              className="text-xs"
            />
          </div>

          <div className="flex items-center justify-end space-x-2 pt-3 border-t border-border mt-5">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              size="sm"
              disabled={submitting}
              className="bg-amber-600 hover:bg-amber-700 text-white"
            >
              {submitting ? 'Suspending...' : 'Suspend Access'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
