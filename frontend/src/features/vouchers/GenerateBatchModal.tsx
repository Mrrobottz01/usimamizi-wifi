import React, { useEffect, useState } from 'react';
import { ApiError, Plan } from '../../types';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';

interface GenerateBatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const GenerateBatchModal: React.FC<GenerateBatchModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { selectedCompany } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string>('');
  const [quantity, setQuantity] = useState<number>(10);
  const [label, setLabel] = useState<string>('');
  const [distributionMode, setDistributionMode] = useState<'CENTRAL_SAAS' | 'LOCAL_FALLBACK'>('CENTRAL_SAAS');
  const [notes, setNotes] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && selectedCompany) {
      apiClient.get<Plan[]>(`/api/v1/plans/?company_id=${selectedCompany.id}`)
        .then((res: { data: Plan[] }) => {
          setPlans(res.data);
          if (res.data.length > 0) {
            setSelectedPlanId(res.data[0].id);
          }
        })
        .catch(() => setError('Failed to load plans.'));
    }
  }, [isOpen, selectedCompany]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompany || !selectedPlanId) return;

    setLoading(true);
    setError(null);

    try {
      await apiClient.post('/api/v1/voucher-batches/', {
        company_id: selectedCompany.id,
        plan_id: selectedPlanId,
        quantity,
        label,
        distribution_mode: distributionMode,
        notes,
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail || 'Failed to generate batch.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-4">Generate Voucher Batch</h2>

        {error && (
          <div className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-600 dark:bg-rose-950/40 dark:text-rose-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Select Access Plan</label>
            <select
              required
              value={selectedPlanId}
              onChange={(e) => setSelectedPlanId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.price} {p.currency})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Quantity (1 - 5,000)</label>
            <input
              type="number"
              min="1"
              max="5000"
              required
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Distribution Mode</label>
            <select
              value={distributionMode}
              onChange={(e) => setDistributionMode(e.target.value as 'CENTRAL_SAAS' | 'LOCAL_FALLBACK')}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="CENTRAL_SAAS">Central SaaS (Primary — Cloud AAA & Captive Portal)</option>
              <option value="LOCAL_FALLBACK">Local Fallback (Emergency Offline RouterOS)</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">
              {distributionMode === 'CENTRAL_SAAS'
                ? 'Vouchers authenticate via FreeRADIUS / Captive Portal with full accounting.'
                : 'Intended for local router import in case of cloud uplink outage.'}
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Batch Label / Tag (Optional)</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Batch Lab 01"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Notes (Optional)</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Printed for Zinga sales kiosk"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !selectedPlanId}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {loading ? 'Generating...' : 'Generate Vouchers'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
