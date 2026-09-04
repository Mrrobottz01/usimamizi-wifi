import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, Plan, Voucher, VoucherBatch, VoucherMetrics } from '../../types';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';
import { GenerateBatchModal } from './GenerateBatchModal';
import { PrintableVoucherModal } from './PrintableVoucherModal';
import { VoucherTimelineModal } from './VoucherTimelineModal';
import { SendVoucherSMSModal } from './SendVoucherSMSModal';
import { ReserveVoucherModal } from './ReserveVoucherModal';

export const VoucherBatchesListPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const navigate = useNavigate();

  // Active Tab: 'batches' | 'all-vouchers'
  const [activeTab, setActiveTab] = useState<'batches' | 'all-vouchers'>('batches');

  // Metrics
  const [metrics, setMetrics] = useState<VoucherMetrics | null>(null);

  // Batches State
  const [batches, setBatches] = useState<VoucherBatch[]>([]);
  const [batchesLoading, setBatchesLoading] = useState(true);
  const [batchesError, setBatchesError] = useState<string | null>(null);

  // All Vouchers State
  const [vouchers, setVouchers] = useState<Voucher[]>([]);
  const [vouchersLoading, setVouchersLoading] = useState(false);
  const [vouchersError, setVouchersError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [distFilter, setDistFilter] = useState('');
  const [exportFilter, setExportFilter] = useState('');
  const [planFilter, setPlanFilter] = useState('');
  const [plans, setPlans] = useState<Plan[]>([]);

  // Modals
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [printBatch, setPrintBatch] = useState<{ id: string; reference: string } | null>(null);
  const [timelineVoucher, setTimelineVoucher] = useState<Voucher | null>(null);
  const [smsVoucher, setSmsVoucher] = useState<Voucher | null>(null);
  const [reserveVoucher, setReserveVoucher] = useState<Voucher | null>(null);

  // 1. Fetch Metrics
  const fetchMetrics = useCallback(async () => {
    if (!selectedCompany) return;
    try {
      const res = await apiClient.get<VoucherMetrics>(`/api/v1/vouchers/metrics/?company_id=${selectedCompany.id}`);
      setMetrics(res.data);
    } catch {
      // Non-critical, fallback to null
    }
  }, [selectedCompany]);

  // 2. Fetch Batches
  const fetchBatches = useCallback(async () => {
    if (!selectedCompany) return;
    setBatchesLoading(true);
    setBatchesError(null);
    try {
      const res = await apiClient.get<VoucherBatch[]>(`/api/v1/voucher-batches/?company_id=${selectedCompany.id}`);
      setBatches(res.data);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setBatchesError(apiErr?.detail || 'Failed to load voucher batches.');
    } finally {
      setBatchesLoading(false);
    }
  }, [selectedCompany]);

  // 3. Fetch Plans for filtering
  useEffect(() => {
    if (selectedCompany) {
      apiClient
        .get<Plan[]>(`/api/v1/plans/?company_id=${selectedCompany.id}`)
        .then((res: { data: Plan[] }) => setPlans(res.data))
        .catch(() => {});
    }
  }, [selectedCompany]);

  // 4. Fetch All Vouchers Flat List
  const fetchVouchers = useCallback(async () => {
    if (!selectedCompany) return;
    setVouchersLoading(true);
    setVouchersError(null);
    try {
      const params = new URLSearchParams({
        company_id: selectedCompany.id,
      });
      if (searchQuery.trim()) params.append('q', searchQuery.trim());
      if (statusFilter) params.append('status', statusFilter);
      if (distFilter) params.append('distribution_state', distFilter);
      if (exportFilter) params.append('export_status', exportFilter);
      if (planFilter) params.append('plan_id', planFilter);

      const res = await apiClient.get<Voucher[]>(`/api/v1/vouchers/?${params.toString()}`);
      setVouchers(res.data);
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setVouchersError(apiErr?.detail || 'Failed to load vouchers.');
    } finally {
      setVouchersLoading(false);
    }
  }, [selectedCompany, searchQuery, statusFilter, distFilter, exportFilter, planFilter]);

  // Initial loads and reloads
  useEffect(() => {
    fetchMetrics();
    fetchBatches();
  }, [fetchMetrics, fetchBatches]);

  useEffect(() => {
    if (activeTab === 'all-vouchers') {
      fetchVouchers();
    }
  }, [activeTab, fetchVouchers]);

  const refreshAll = () => {
    fetchMetrics();
    fetchBatches();
    if (activeTab === 'all-vouchers') {
      fetchVouchers();
    }
  };

  // Export handlers
  const handleDownloadRouterOS = async (e: React.MouseEvent, batchId: string, reference: string) => {
    e.stopPropagation();
    try {
      const res = await apiClient.get(`/api/v1/voucher-batches/${batchId}/export-routeros/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data as unknown as BlobPart]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${reference}.rsc`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      refreshAll();
    } catch {
      alert('Failed to download RouterOS script.');
    }
  };

  const handleDownloadCSV = async (e: React.MouseEvent, batchId: string, reference: string) => {
    e.stopPropagation();
    try {
      const res = await apiClient.get(`/api/v1/voucher-batches/${batchId}/export-csv/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data as unknown as BlobPart]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${reference}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Failed to download CSV export.');
    }
  };

  const handleRevokeVoucher = async (voucher: Voucher) => {
    const reason = prompt(`Revoke voucher ${voucher.display_code}? Reason (optional):`, 'Customer cancellation');
    if (reason === null) return;
    try {
      await apiClient.post(`/api/v1/vouchers/${voucher.id}/revoke/`, { reason });
      refreshAll();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      alert(apiErr?.detail || 'Failed to revoke voucher.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Vouchers & Pass Management
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            SaaS lifecycle control: generate batches, print A4 cards, dispatch via SMS, and export offline fallback.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refreshAll()}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            ↻ Refresh
          </button>
          <button
            onClick={() => setIsGenerateOpen(true)}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition shadow-sm"
          >
            + Generate Voucher Batch
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Vouchers</div>
            <div className="mt-1 text-2xl font-black text-slate-900 dark:text-slate-100">{metrics.total}</div>
            <div className="mt-1 text-[10px] text-slate-400">All generated</div>
          </div>

          <div className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4 shadow-sm dark:border-emerald-950 dark:bg-emerald-950/20">
            <div className="text-[11px] font-semibold text-emerald-800 dark:text-emerald-400 uppercase tracking-wider">Available</div>
            <div className="mt-1 text-2xl font-black text-emerald-700 dark:text-emerald-400">{metrics.available}</div>
            <div className="mt-1 text-[10px] text-emerald-600/80">Ready for use</div>
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 shadow-sm dark:border-amber-950 dark:bg-amber-950/20">
            <div className="text-[11px] font-semibold text-amber-800 dark:text-amber-400 uppercase tracking-wider">Reserved</div>
            <div className="mt-1 text-2xl font-black text-amber-700 dark:text-amber-400">{metrics.reserved}</div>
            <div className="mt-1 text-[10px] text-amber-600/80">Allocated to customer</div>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50/40 p-4 shadow-sm dark:border-blue-950 dark:bg-blue-950/20">
            <div className="text-[11px] font-semibold text-blue-800 dark:text-blue-400 uppercase tracking-wider">Redeemed</div>
            <div className="mt-1 text-2xl font-black text-blue-700 dark:text-blue-400">{metrics.redeemed}</div>
            <div className="mt-1 text-[10px] text-blue-600/80">{metrics.redemption_rate}% conversion</div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">SMS Dispatched</div>
            <div className="mt-1 text-2xl font-black text-slate-900 dark:text-slate-100">{metrics.sent_sms}</div>
            <div className="mt-1 text-[10px] text-slate-400">Sent via RafikiSMS</div>
          </div>

          <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-4 shadow-sm dark:border-rose-950 dark:bg-rose-950/20">
            <div className="text-[11px] font-semibold text-rose-800 dark:text-rose-400 uppercase tracking-wider">Revoked</div>
            <div className="mt-1 text-2xl font-black text-rose-700 dark:text-rose-400">{metrics.revoked}</div>
            <div className="mt-1 text-[10px] text-rose-600/80">Terminated sessions</div>
          </div>
        </div>
      )}

      {/* Tabs Switcher */}
      <div className="flex border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => setActiveTab('batches')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition ${
            activeTab === 'batches'
              ? 'border-emerald-600 text-emerald-600 dark:border-emerald-400 dark:text-emerald-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          📦 Voucher Batches ({batches.length})
        </button>
        <button
          onClick={() => setActiveTab('all-vouchers')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition ${
            activeTab === 'all-vouchers'
              ? 'border-emerald-600 text-emerald-600 dark:border-emerald-400 dark:text-emerald-400'
              : 'border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          🔍 All Vouchers Explorer
        </button>
      </div>

      {/* TAB 1: BATCHES */}
      {activeTab === 'batches' && (
        <div className="space-y-4">
          {batchesError && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-600 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-400">
              {batchesError}
            </div>
          )}

          {batchesLoading ? (
            <div className="py-12 text-center text-slate-500">Loading voucher batches...</div>
          ) : batches.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center dark:border-slate-800">
              <p className="text-slate-500 dark:text-slate-400 mb-4">No voucher batches generated yet.</p>
              <button
                onClick={() => setIsGenerateOpen(true)}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              >
                Generate First Batch
              </button>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <table className="w-full text-left text-sm text-slate-600 dark:text-slate-400">
                <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
                  <tr>
                    <th className="px-6 py-3">Batch Reference</th>
                    <th className="px-6 py-3">Plan / Price</th>
                    <th className="px-6 py-3">Distribution & Mode</th>
                    <th className="px-6 py-3">Redemption Status</th>
                    <th className="px-6 py-3">Created</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {batches.map((batch) => (
                    <tr
                      key={batch.id}
                      onClick={() => navigate(`/vouchers/batches/${batch.id}`)}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 cursor-pointer transition"
                    >
                      <td className="px-6 py-4">
                        <div className="font-bold text-slate-900 dark:text-slate-100">{batch.reference}</div>
                        {batch.label && (
                          <div className="text-xs text-slate-400">{batch.label}</div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium text-slate-800 dark:text-slate-200">{batch.plan?.name}</div>
                        <div className="text-xs text-slate-400">
                          {batch.plan?.price} {batch.plan?.currency}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col gap-1 items-start">
                          <span
                            className={`inline-block rounded px-2 py-0.5 text-[10px] font-semibold ${
                              batch.distribution_mode === 'LOCAL_FALLBACK'
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-400'
                                : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                            }`}
                          >
                            {batch.distribution_mode === 'LOCAL_FALLBACK' ? 'RouterOS Fallback' : 'Central SaaS AAA'}
                          </span>
                          <span
                            className={`inline-block rounded px-2 py-0.5 text-[10px] font-semibold ${
                              batch.export_status === 'EXPORTED_ROUTEROS'
                                ? 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-400'
                                : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                            }`}
                          >
                            {batch.export_status === 'EXPORTED_ROUTEROS' ? 'Exported (.rsc)' : 'Active Cloud'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-slate-200 h-2 rounded-full overflow-hidden dark:bg-slate-700">
                            <div
                              className="bg-emerald-500 h-full rounded-full"
                              style={{
                                width: `${batch.quantity ? Math.round((batch.redeemed_count / batch.quantity) * 100) : 0}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            {batch.redeemed_count} / {batch.quantity}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          {batch.available_count} available, {batch.revoked_count} revoked
                        </div>
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-400">
                        {new Date(batch.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => setPrintBatch({ id: batch.id, reference: batch.reference })}
                            title="Print A4 Voucher Sheet"
                            className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 dark:border-slate-700 dark:bg-slate-800 dark:text-emerald-400 dark:hover:bg-slate-700"
                          >
                            🖨 Print Cards
                          </button>
                          <button
                            onClick={(e) => handleDownloadCSV(e, batch.id, batch.reference)}
                            title="Export CSV"
                            className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                          >
                            CSV
                          </button>
                          <button
                            onClick={(e) => handleDownloadRouterOS(e, batch.id, batch.reference)}
                            title="Export RouterOS .rsc"
                            className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                          >
                            .rsc
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: ALL VOUCHERS EXPLORER */}
      {activeTab === 'all-vouchers' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
              <div className="col-span-1 sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Search Code, Phone, or Batch Ref
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g. ABCD-7XQ9 or 0712345678"
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Lifecycle Status
                </label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                >
                  <option value="">All Statuses</option>
                  <option value="AVAILABLE">AVAILABLE</option>
                  <option value="RESERVED">RESERVED</option>
                  <option value="REDEEMED">REDEEMED</option>
                  <option value="EXPIRED">EXPIRED</option>
                  <option value="REVOKED">REVOKED</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Distribution State
                </label>
                <select
                  value={distFilter}
                  onChange={(e) => setDistFilter(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                >
                  <option value="">All States</option>
                  <option value="UNSOLD">UNSOLD</option>
                  <option value="SOLD">SOLD</option>
                  <option value="GIVEN_FREE">GIVEN_FREE</option>
                  <option value="PROMOTIONAL">PROMOTIONAL</option>
                  <option value="INTERNAL_TEST">INTERNAL_TEST</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Access Plan
                </label>
                <select
                  value={planFilter}
                  onChange={(e) => setPlanFilter(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                >
                  <option value="">All Plans</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Export Status
                </label>
                <select
                  value={exportFilter}
                  onChange={(e) => setExportFilter(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                >
                  <option value="">All Exports</option>
                  <option value="NOT_EXPORTED">Central SaaS Only</option>
                  <option value="EXPORTED_ROUTEROS">Exported RouterOS</option>
                </select>
              </div>
            </div>
          </div>

          {vouchersError && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-600 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-400">
              {vouchersError}
            </div>
          )}

          {vouchersLoading ? (
            <div className="py-12 text-center text-slate-500">Searching vouchers...</div>
          ) : vouchers.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center dark:border-slate-800 text-slate-500">
              No vouchers match the active filters.
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <table className="w-full text-left text-sm text-slate-600 dark:text-slate-400">
                <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
                  <tr>
                    <th className="px-4 py-3">Voucher Code</th>
                    <th className="px-4 py-3">Plan</th>
                    <th className="px-4 py-3">Batch</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Distribution</th>
                    <th className="px-4 py-3">Export</th>
                    <th className="px-4 py-3">Phone / Redeemed</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {vouchers.map((v) => (
                    <tr key={v.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3 font-mono font-bold text-slate-900 dark:text-slate-100 select-all">
                        {v.display_code}
                      </td>
                      <td className="px-4 py-3 text-xs font-medium text-slate-800 dark:text-slate-200">
                        {v.plan_name}
                      </td>
                      <td className="px-4 py-3 text-xs font-mono text-slate-500">
                        {v.batch_reference}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${
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
                      <td className="px-4 py-3 text-xs">
                        <span className="font-semibold text-slate-700 dark:text-slate-300">
                          {v.distribution_state}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[11px]">
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
                      <td className="px-4 py-3 text-xs">
                        <div>{v.recipient_phone ? <span className="font-mono">{v.recipient_phone}</span> : '—'}</div>
                        {v.redeemed_at && (
                          <div className="text-[10px] text-slate-400">
                            {new Date(v.redeemed_at).toLocaleString()}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Send SMS */}
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
                              onClick={() => handleRevokeVoucher(v)}
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
          )}
        </div>
      )}

      {/* Modals */}
      <GenerateBatchModal
        isOpen={isGenerateOpen}
        onClose={() => setIsGenerateOpen(false)}
        onSuccess={refreshAll}
      />

      {printBatch && (
        <PrintableVoucherModal
          isOpen={!!printBatch}
          onClose={() => setPrintBatch(null)}
          batchId={printBatch.id}
          batchReference={printBatch.reference}
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
        onSuccess={refreshAll}
      />

      <ReserveVoucherModal
        isOpen={!!reserveVoucher}
        onClose={() => setReserveVoucher(null)}
        voucher={reserveVoucher}
        onSuccess={refreshAll}
      />
    </div>
  );
};
