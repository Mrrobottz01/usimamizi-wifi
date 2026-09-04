import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ApiError, VoucherBatch, Voucher } from '../../types';
import { apiClient } from '../../lib/api-client';
import { PrintableVoucherModal } from './PrintableVoucherModal';
import { VoucherTimelineModal } from './VoucherTimelineModal';
import { SendVoucherSMSModal } from './SendVoucherSMSModal';
import { ReserveVoucherModal } from './ReserveVoucherModal';

export const VoucherBatchDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [batch, setBatch] = useState<VoucherBatch | null>(null);
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isPrintOpen, setIsPrintOpen] = useState(false);
  const [timelineVoucher, setTimelineVoucher] = useState<Voucher | null>(null);
  const [smsVoucher, setSmsVoucher] = useState<Voucher | null>(null);
  const [reserveVoucher, setReserveVoucher] = useState<Voucher | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<{ batch: VoucherBatch; vouchers: Voucher[] }>(`/api/v1/voucher-batches/${id}/`);
      setBatch(res.data.batch);
      setVouchers(res.data.vouchers);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setError(apiErr?.detail || 'Failed to load batch detail.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleRevoke = async (voucher: Voucher) => {
    const reason = prompt(`Revoke voucher ${voucher.display_code}? Reason (optional):`, 'Customer cancellation');
    if (reason === null) return;
    try {
      await apiClient.post(`/api/v1/vouchers/${voucher.id}/revoke/`, { reason });
      fetchDetail();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      alert(apiErr?.detail || 'Failed to revoke voucher.');
    }
  };

  const handleDownloadRouterOS = async () => {
    if (!batch) return;
    try {
      const res = await apiClient.get(`/api/v1/voucher-batches/${batch.id}/export-routeros/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data as unknown as BlobPart]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${batch.reference}.rsc`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      fetchDetail();
    } catch {
      alert('Failed to download RouterOS script.');
    }
  };

  const handleDownloadCSV = async () => {
    if (!batch) return;
    try {
      const res = await apiClient.get(`/api/v1/voucher-batches/${batch.id}/export-csv/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data as unknown as BlobPart]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${batch.reference}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Failed to download CSV export.');
    }
  };

  if (loading) return <div className="py-12 text-center text-slate-500">Loading batch details...</div>;
  if (error || !batch) return <div className="py-12 text-center text-rose-500">{error || 'Batch not found.'}</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <button
            onClick={() => navigate('/vouchers')}
            className="text-xs text-emerald-600 dark:text-emerald-400 hover:underline mb-1 inline-block"
          >
            ← Back to Voucher Hub
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{batch.reference}</h1>
            <span
              className={`rounded px-2 py-0.5 text-xs font-semibold ${
                batch.distribution_mode === 'LOCAL_FALLBACK'
                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400'
                  : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
              }`}
            >
              {batch.distribution_mode === 'LOCAL_FALLBACK' ? 'RouterOS Fallback' : 'Central SaaS AAA'}
            </span>
            <span
              className={`rounded px-2 py-0.5 text-xs font-semibold ${
                batch.export_status === 'EXPORTED_ROUTEROS'
                  ? 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-400'
                  : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
              }`}
            >
              {batch.export_status === 'EXPORTED_ROUTEROS' ? 'Exported (.rsc)' : 'Active Cloud'}
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Plan: <span className="font-semibold text-slate-700 dark:text-slate-300">{batch.plan?.name}</span> ({batch.plan?.price} {batch.plan?.currency}) | Total: {batch.quantity} | Available: {batch.available_count} | Redeemed: {batch.redeemed_count}
          </p>
          {batch.notes && (
            <p className="text-xs text-slate-400 italic mt-0.5">Note: {batch.notes}</p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setIsPrintOpen(true)}
            className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 shadow-sm flex items-center gap-1.5"
          >
            🖨 Print Voucher Sheet (A4)
          </button>
          <button
            onClick={handleDownloadCSV}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Export CSV
          </button>
          <button
            onClick={handleDownloadRouterOS}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            Export RouterOS (.rsc)
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left text-sm text-slate-600 dark:text-slate-400">
          <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
            <tr>
              <th className="px-6 py-3">Voucher Code</th>
              <th className="px-6 py-3">Status</th>
              <th className="px-6 py-3">Distribution State</th>
              <th className="px-6 py-3">Export</th>
              <th className="px-6 py-3">Recipient Phone</th>
              <th className="px-6 py-3">Redeemed At</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {vouchers.map((v) => (
              <tr key={v.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                <td className="px-6 py-4 font-mono font-bold text-slate-900 dark:text-slate-100 select-all">
                  {v.display_code}
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      v.status === 'AVAILABLE'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                        : v.status === 'RESERVED'
                        ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400'
                        : v.status === 'REDEEMED'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-400'
                        : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-400'
                    }`}
                  >
                    {v.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {v.distribution_state}
                </td>
                <td className="px-6 py-4 text-xs">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                      v.export_status === 'EXPORTED_ROUTEROS'
                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300'
                        : 'bg-slate-100 text-slate-500 dark:bg-slate-800'
                    }`}
                  >
                    {v.export_status === 'EXPORTED_ROUTEROS' ? 'RouterOS' : 'Cloud AAA'}
                  </span>
                </td>
                <td className="px-6 py-4 text-xs font-mono">{v.recipient_phone || '—'}</td>
                <td className="px-6 py-4 text-xs text-slate-400">
                  {v.redeemed_at ? new Date(v.redeemed_at).toLocaleString() : '—'}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-1.5">
                    {/* SMS */}
                    <button
                      onClick={() => setSmsVoucher(v)}
                      title="Send Voucher via SMS"
                      className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      ✉️ SMS
                    </button>

                    {/* Reserve */}
                    {v.status === 'AVAILABLE' && (
                      <button
                        onClick={() => setReserveVoucher(v)}
                        title="Reserve Voucher"
                        className="rounded border border-amber-200 px-2 py-1 text-xs text-amber-700 hover:bg-amber-50 dark:border-amber-900/50 dark:text-amber-400 dark:hover:bg-amber-950/30"
                      >
                        Reserve
                      </button>
                    )}

                    {/* Revoke */}
                    {v.status !== 'REVOKED' && v.status !== 'EXPIRED' && (
                      <button
                        onClick={() => handleRevoke(v)}
                        title="Revoke Voucher & Disconnect Session"
                        className="rounded border border-rose-200 px-2 py-1 text-xs text-rose-600 hover:bg-rose-50 dark:border-rose-900/50 dark:text-rose-400 dark:hover:bg-rose-950/30"
                      >
                        Revoke
                      </button>
                    )}

                    {/* Timeline */}
                    <button
                      onClick={() => setTimelineVoucher(v)}
                      title="View Lifecycle Timeline"
                      className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                    >
                      ⏱
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Modals */}
      {batch && (
        <PrintableVoucherModal
          isOpen={isPrintOpen}
          onClose={() => setIsPrintOpen(false)}
          batchId={batch.id}
          batchReference={batch.reference}
        />
      )}

      <VoucherTimelineModal
        isOpen={!!timelineVoucher}
        onClose={() => setTimelineVoucher(null)}
        voucher={timelineVoucher}
      />

      <SendVoucherSMSModal
        isOpen={!!smsVoucher}
        onClose={() => setSmsVoucher(null)}
        voucher={smsVoucher}
        onSuccess={fetchDetail}
      />

      <ReserveVoucherModal
        isOpen={!!reserveVoucher}
        onClose={() => setReserveVoucher(null)}
        voucher={reserveVoucher}
        onSuccess={fetchDetail}
      />
    </div>
  );
};
