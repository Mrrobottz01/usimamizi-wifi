import React, { useState } from 'react';
import { ApiError, Voucher } from '../../types';
import { apiClient } from '../../lib/api-client';

interface ReserveVoucherModalProps {
  isOpen: boolean;
  onClose: () => void;
  voucher: Voucher | null;
  onSuccess: () => void;
}

export const ReserveVoucherModal: React.FC<ReserveVoucherModalProps> = ({
  isOpen,
  onClose,
  voucher,
  onSuccess,
}) => {
  const [recipientPhone, setRecipientPhone] = useState(voucher?.recipient_phone || '');
  const [distributionState, setDistributionState] = useState<string>('SOLD');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (voucher) {
      setRecipientPhone(voucher.recipient_phone || '');
      setDistributionState(voucher.distribution_state === 'UNSOLD' ? 'SOLD' : voucher.distribution_state);
    }
  }, [voucher]);

  if (!isOpen || !voucher) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await apiClient.post(`/api/v1/vouchers/${voucher.id}/reserve/`, {
        recipient_phone: recipientPhone.trim(),
        distribution_state: distributionState,
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail || 'Failed to reserve voucher.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-1">
          Reserve Voucher
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Allocate voucher to a customer and tag distribution state.
        </p>

        {error && (
          <div className="mb-4 rounded-lg bg-rose-50 p-3 text-xs text-rose-600 dark:bg-rose-950/40 dark:text-rose-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 dark:bg-slate-800/50 dark:border-slate-700">
            <div className="text-[11px] text-slate-500 font-medium">Voucher Details:</div>
            <div className="mt-1 flex items-center justify-between">
              <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                {voucher.display_code}
              </span>
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                {voucher.plan_name}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Customer Mobile Phone (Optional)
            </label>
            <input
              type="text"
              value={recipientPhone}
              onChange={(e) => setRecipientPhone(e.target.value)}
              placeholder="e.g. 0712345678"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Distribution State
            </label>
            <select
              value={distributionState}
              onChange={(e) => setDistributionState(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            >
              <option value="SOLD">Sold (Cash / POS / Retail)</option>
              <option value="GIVEN_FREE">Given Free (Courtesy Pass)</option>
              <option value="PROMOTIONAL">Promotional Campaign</option>
              <option value="INTERNAL_TEST">Internal QA / Testing</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {loading ? 'Reserving...' : 'Confirm Reservation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
