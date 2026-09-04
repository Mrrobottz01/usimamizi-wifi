import { useCallback, useEffect, useState } from 'react';
import { Card, CardHeader, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import {
  MessageSquare,
  Search,
  RefreshCw,
  Download,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  ChevronLeft,
  ChevronRight,
  TrendingUp
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { apiClient } from '../../lib/api-client';
import { SMSHistoryDetail, SMSHistoryItem, SMSHistorySummary } from '../../types';
import { SMSDetailModal } from './SMSDetailModal';

export function SMSHistoryPage() {
  const { selectedCompany } = useAuth();

  // State
  const [items, setItems] = useState<SMSHistoryItem[]>([]);
  const [summary, setSummary] = useState<SMSHistorySummary>({
    total_messages: 0,
    delivered: 0,
    sent: 0,
    failed: 0,
    queued: 0,
    sending: 0,
    delivery_rate: 0,
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [quickFilter, setQuickFilter] = useState<'ALL' | 'DELIVERED' | 'FAILED' | 'PENDING'>('ALL');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');

  // Detail Modal
  const [detailItem, setDetailItem] = useState<SMSHistoryDetail | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);

  const fetchHistory = useCallback(async () => {
    if (!selectedCompany) return;
    setLoading(true);

    try {
      const params = new URLSearchParams({
        company_id: selectedCompany.id,
        page: page.toString(),
        page_size: '15',
      });

      if (search) params.append('search', search);
      if (providerFilter) params.append('provider', providerFilter);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);

      if (quickFilter === 'DELIVERED') {
        params.append('delivered_only', 'true');
      } else if (quickFilter === 'FAILED') {
        params.append('failed_only', 'true');
      } else if (statusFilter) {
        params.append('status', statusFilter);
      }

      const res = await apiClient.get<{
        results: SMSHistoryItem[];
        count: number;
        page: number;
        total_pages: number;
        summary: SMSHistorySummary;
      }>(`/notifications/sms/history/?${params.toString()}`);

      setItems(res.data.results);
      setTotalCount(res.data.count);
      setTotalPages(res.data.total_pages);
      if (res.data.summary) {
        setSummary(res.data.summary);
      }
    } catch {
      // Handled silently
    } finally {
      setLoading(false);
    }
  }, [selectedCompany, page, search, statusFilter, providerFilter, quickFilter, dateFrom, dateTo]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleOpenDetail = async (id: string) => {
    if (!selectedCompany) return;
    setModalOpen(true);

    try {
      const res = await apiClient.get<SMSHistoryDetail>(
        `/notifications/sms/history/${id}/?company_id=${selectedCompany.id}`
      );
      setDetailItem(res.data);
    } catch {
      alert('Failed to load SMS details.');
      setModalOpen(false);
    }
  };

  const handleRetry = async (id: string) => {
    if (!selectedCompany) return;
    try {
      const res = await apiClient.post<SMSHistoryDetail>(
        `/notifications/sms/history/${id}/retry/`,
        { company_id: selectedCompany.id }
      );
      setDetailItem(res.data);
      await fetchHistory();
      alert('SMS successfully queued for retry.');
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      alert(apiErr?.detail || 'Failed to retry SMS.');
    }
  };

  const handleExportCSV = async () => {
    if (!selectedCompany) return;
    setExporting(true);
    try {
      const params = new URLSearchParams({
        company_id: selectedCompany.id,
      });
      if (search) params.append('search', search);
      if (statusFilter) params.append('status', statusFilter);
      if (providerFilter) params.append('provider', providerFilter);

      const blob = await apiClient.get<Blob>(`/notifications/sms/history/export/?${params.toString()}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([blob.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `sms_delivery_logs_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Failed to export CSV.');
    } finally {
      setExporting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DELIVERED':
        return <Badge variant="success">Delivered</Badge>;
      case 'SENT':
        return <Badge variant="secondary">Sent</Badge>;
      case 'SENDING':
        return <Badge variant="warning">Sending</Badge>;
      case 'FAILED':
        return <Badge variant="destructive">Failed</Badge>;
      case 'QUEUED':
      default:
        return <Badge variant="outline">Queued</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">SMS Delivery Logs</h1>
          <p className="text-sm text-muted-foreground">
            Track operational SMS dispatches, multi-provider failovers, and delivery receipts.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportCSV} disabled={exporting || items.length === 0}>
            <Download className="mr-2 h-4 w-4" />
            {exporting ? 'Exporting...' : 'Export CSV'}
          </Button>
          <Button variant="outline" size="sm" onClick={fetchHistory} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {/* Summary Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <Card className="p-4 bg-card/60">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Total SMS</span>
            <MessageSquare className="h-4 w-4 text-primary" />
          </div>
          <div className="text-2xl font-bold text-foreground mt-2">{summary.total_messages}</div>
        </Card>

        <Card className="p-4 bg-emerald-50/30 dark:bg-emerald-950/20 border-emerald-200/50 dark:border-emerald-900/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 uppercase">Delivered</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 mt-2">{summary.delivered}</div>
        </Card>

        <Card className="p-4 bg-rose-50/30 dark:bg-rose-950/20 border-rose-200/50 dark:border-rose-900/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-rose-800 dark:text-rose-300 uppercase">Failed</span>
            <XCircle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-700 dark:text-rose-300 mt-2">{summary.failed}</div>
        </Card>

        <Card className="p-4 bg-amber-50/30 dark:bg-amber-950/20 border-amber-200/50 dark:border-amber-900/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-800 dark:text-amber-300 uppercase">Queued / Sent</span>
            <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-700 dark:text-amber-300 mt-2">{summary.sent + summary.queued + summary.sending}</div>
        </Card>

        <Card className="p-4 bg-primary/5 border-primary/20 col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-primary uppercase">Delivery Rate</span>
            <TrendingUp className="h-4 w-4 text-primary" />
          </div>
          <div className="text-2xl font-bold text-primary mt-2">
            {summary.delivery_rate !== null ? `${summary.delivery_rate}%` : '—'}
          </div>
        </Card>
      </div>

      {/* Main Filter & Table Card */}
      <Card>
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            {/* Quick Filter Tabs */}
            <div className="flex items-center gap-1 bg-muted p-1 rounded-lg">
              {(['ALL', 'DELIVERED', 'FAILED', 'PENDING'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setQuickFilter(tab);
                    setPage(1);
                  }}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition ${
                    quickFilter === tab
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {tab === 'ALL' ? 'All Messages' : tab.charAt(0) + tab.slice(1).toLowerCase()}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative w-full md:w-72">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search phone, voucher, ref..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-9 text-xs"
              />
            </div>
          </div>

          {/* Secondary Filters Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-3">
            <div>
              <label className="block text-[11px] font-medium text-muted-foreground mb-1">Provider</label>
              <select
                value={providerFilter}
                onChange={(e) => {
                  setProviderFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
              >
                <option value="">All Providers</option>
                <option value="rafikisms">RafikiSMS</option>
                <option value="beem">Beem Africa</option>
                <option value="nextsms">NextSMS Tanzania</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-muted-foreground mb-1">Status</label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
              >
                <option value="">All Statuses</option>
                <option value="DELIVERED">Delivered</option>
                <option value="SENT">Sent</option>
                <option value="SENDING">Sending</option>
                <option value="FAILED">Failed</option>
                <option value="QUEUED">Queued</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-muted-foreground mb-1">Date From</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(1);
                }}
                className="text-xs py-1"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-muted-foreground mb-1">Date To</label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPage(1);
                }}
                className="text-xs py-1"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {/* Desktop Table View */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-muted/30 text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Recipient</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Provider</th>
                  <th className="px-4 py-3">Sender ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Attempts</th>
                  <th className="px-4 py-3">Voucher</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-muted-foreground">
                      <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-primary" />
                      Loading delivery logs...
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-muted-foreground">
                      No SMS delivery records found matching your filters.
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => handleOpenDetail(item.id)}
                      className="cursor-pointer hover:bg-accent/40 transition"
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-muted-foreground font-mono">
                        {new Date(item.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-foreground">
                        {item.recipient_masked}
                      </td>
                      <td className="px-4 py-3 text-xs font-semibold text-muted-foreground">
                        {item.message_type}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-bold text-xs uppercase text-foreground">
                          {item.provider_used || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-foreground">
                        {item.sender_id || '-'}
                      </td>
                      <td className="px-4 py-3">{getStatusBadge(item.status)}</td>
                      <td className="px-4 py-3 text-xs font-bold text-foreground">
                        <span className={`px-2 py-0.5 rounded-full text-[11px] ${item.attempt_count > 1 ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' : 'bg-muted'}`}>
                          {item.attempt_count} attempt{item.attempt_count > 1 ? 's' : ''}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs font-bold text-primary">
                        {item.voucher_code || '-'}
                      </td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenDetail(item.id)}
                          className="h-8 w-8 p-0"
                          title="View Details"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Card List View (<= 390px responsive) */}
          <div className="block md:hidden divide-y divide-border">
            {loading ? (
              <div className="py-8 text-center text-muted-foreground">
                <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-primary" />
                Loading logs...
              </div>
            ) : items.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground text-xs">
                No SMS records found.
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleOpenDetail(item.id)}
                  className="p-3.5 space-y-2 hover:bg-accent/40 transition cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-foreground">{item.recipient_masked}</span>
                    {getStatusBadge(item.status)}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="uppercase font-semibold text-[11px]">{item.provider_used || 'SMS'} ({item.sender_id || 'DEFAULT'})</span>
                    <span className="font-mono text-[11px]">{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                  {item.voucher_code && (
                    <div className="text-xs font-mono font-bold text-primary flex items-center gap-1">
                      Voucher: {item.voucher_code}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-4 py-3 text-xs text-muted-foreground">
              <div>
                Showing page <span className="font-semibold text-foreground">{page}</span> of{' '}
                <span className="font-semibold text-foreground">{totalPages}</span> ({totalCount} items)
              </div>
              <div className="flex items-center space-x-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="h-8 w-8 p-0"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="h-8 w-8 p-0"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail & Failover Timeline Modal */}
      <SMSDetailModal
        item={detailItem}
        isOpen={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setDetailItem(null);
        }}
        onRetry={handleRetry}
      />
    </div>
  );
}
