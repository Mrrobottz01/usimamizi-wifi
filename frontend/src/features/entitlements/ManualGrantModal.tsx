import { useEffect, useState } from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Plan } from '../../types';
import { apiClient } from '../../lib/api-client';
import { X, Key, AlertCircle } from 'lucide-react';

interface ManualGrantModalProps {
  isOpen: boolean;
  companyId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function ManualGrantModal({ isOpen, companyId, onClose, onSuccess }: ManualGrantModalProps) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !companyId) return;
    setLoading(true);
    setError(null);
    setReason('');
    setSelectedPlanId('');

    apiClient.get<Plan[]>(`/plans/?company_id=${companyId}`)
      .then((res) => {
        setPlans(res.data);
        if (res.data.length > 0) {
          setSelectedPlanId(res.data[0].id);
        }
      })
      .catch(() => {
        setError('Failed to load plans for manual grant.');
      })
      .finally(() => setLoading(false));
  }, [isOpen, companyId]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanId) {
      setError('Please select an internet plan.');
      return;
    }
    if (!reason.trim() || reason.trim().length < 3) {
      setError('Please provide a valid reason (minimum 3 characters).');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await apiClient.post('/entitlements/manual-grant/', {
        company_id: companyId,
        plan_id: selectedPlanId,
        reason: reason.trim(),
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr?.detail || 'Failed to grant access entitlement.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-xl border border-border bg-card shadow-2xl text-card-foreground p-6">
        <div className="flex items-center justify-between border-b border-border pb-4 mb-5">
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Key className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Grant Access Entitlement</h3>
              <p className="text-xs text-muted-foreground">Complimentary or administrative access authorization</p>
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

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5">
              Select Internet Plan <span className="text-destructive">*</span>
            </label>
            {loading ? (
              <div className="text-xs text-muted-foreground py-2">Loading available plans...</div>
            ) : plans.length === 0 ? (
              <div className="text-xs text-destructive py-2">No plans available for this tenant. Create a plan first.</div>
            ) : (
              <select
                value={selectedPlanId}
                onChange={(e) => setSelectedPlanId(e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                required
              >
                {plans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.duration_value} {p.duration_unit.toLowerCase()}) — {p.price} {p.currency}
                  </option>
                ))}
              </select>
            )}
            <p className="text-[11px] text-muted-foreground mt-1">
              Commercial properties and bandwidth shaping limits are snapshotted automatically from the plan.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-foreground mb-1.5">
              Grant Reason / Justification <span className="text-destructive">*</span>
            </label>
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. VIP guest access, management approval, support compensation..."
              className="text-xs"
              required
              minLength={3}
            />
            <p className="text-[11px] text-muted-foreground mt-1">
              Required for compliance and operator audit trails.
            </p>
          </div>

          <div className="flex items-center justify-end space-x-2 pt-4 border-t border-border mt-6">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={submitting || plans.length === 0}
              className="bg-primary text-primary-foreground"
            >
              {submitting ? 'Granting...' : 'Grant Access'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
