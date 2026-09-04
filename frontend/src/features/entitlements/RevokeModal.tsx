import { useState } from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { apiClient } from '../../lib/api-client';
import { X, ShieldAlert, AlertCircle } from 'lucide-react';
import { AccessEntitlement } from '../../types';

interface RevokeModalProps {
  item: AccessEntitlement | null;
  companyId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function RevokeModal({ item, companyId, isOpen, onClose, onSuccess }: RevokeModalProps) {
  const [reason, setReason] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen || !item) return null;

  const handleRevoke = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim() || reason.trim().length < 3) {
      setError('A valid revocation reason is required (minimum 3 characters).');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await apiClient.post(`/entitlements/${item.id}/revoke/`, {
        company_id: companyId,
        reason: reason.trim(),
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr?.detail || 'Failed to revoke access entitlement.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md rounded-xl border border-destructive/40 bg-card shadow-2xl text-card-foreground p-6">
        <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Permanently Revoke Access</h3>
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

        <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 mb-4 text-xs text-destructive">
          <p className="font-semibold">Destructive Action Warning</p>
          <p className="mt-1 opacity-90">
            Revoking access permanently terminates authorization for this customer/device. This action cannot be undone or resumed.
          </p>
        </div>

        <form onSubmit={handleRevoke} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5">
              Revocation Reason <span className="text-destructive">*</span>
            </label>
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Terms of service violation, fraudulent payment, abuse..."
              className="text-xs"
              required
              minLength={3}
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
              className="bg-destructive text-destructive-foreground"
            >
              {submitting ? 'Revoking...' : 'Revoke Access'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
