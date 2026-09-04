import React, { useEffect, useState } from 'react';
import { ApiError, Voucher, VoucherTimelineEvent } from '../../types';
import { apiClient } from '../../lib/api-client';

interface VoucherTimelineModalProps {
  isOpen: boolean;
  onClose: () => void;
  voucher: Voucher | null;
}

export const VoucherTimelineModal: React.FC<VoucherTimelineModalProps> = ({
  isOpen,
  onClose,
  voucher,
}) => {
  const [timeline, setTimeline] = useState<VoucherTimelineEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && voucher) {
      setLoading(true);
      setError(null);
      apiClient
        .get<VoucherTimelineEvent[]>(`/api/v1/vouchers/${voucher.id}/timeline/`)
        .then((res: { data: VoucherTimelineEvent[] }) => {
          setTimeline(res.data);
        })
        .catch((err: unknown) => {
          const apiErr = err as ApiError;
          setError(apiErr?.detail || 'Failed to load voucher timeline.');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [isOpen, voucher]);

  if (!isOpen || !voucher) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              Voucher Lifecycle Timeline
            </h2>
            <p className="text-xs font-mono font-semibold text-emerald-600 dark:text-emerald-400">
              {voucher.display_code} ({voucher.plan_name})
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto py-4">
          {error && (
            <div className="mb-4 rounded-lg bg-rose-50 p-3 text-xs text-rose-600 dark:bg-rose-950/40 dark:text-rose-400">
              {error}
            </div>
          )}

          {loading ? (
            <div className="py-12 text-center text-xs text-slate-500">Loading lifecycle events...</div>
          ) : timeline.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">No events recorded.</div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
              {timeline.map((event, idx) => {
                const getBadgeColor = (status: string) => {
                  switch (status) {
                    case 'success':
                      return 'bg-emerald-500 ring-emerald-100 dark:ring-emerald-950';
                    case 'warning':
                      return 'bg-amber-500 ring-amber-100 dark:ring-amber-950';
                    case 'error':
                      return 'bg-rose-500 ring-rose-100 dark:ring-rose-950';
                    default:
                      return 'bg-blue-500 ring-blue-100 dark:ring-blue-950';
                  }
                };

                return (
                  <div key={idx} className="relative">
                    {/* Node Dot */}
                    <div
                      className={`absolute -left-6 top-1 h-3 w-3 rounded-full ring-4 ${getBadgeColor(
                        event.status
                      )}`}
                    />
                    <div className="flex flex-col">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100">
                          {event.title}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {new Date(event.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-600 dark:text-slate-300">
                        {event.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-slate-100 pt-3 flex justify-end dark:border-slate-800">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
