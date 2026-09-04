import { useCallback, useEffect, useState } from 'react';
import { Card, CardHeader, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import {
  Search,
  RefreshCw,
  Plus,
  CheckCircle2,
  Clock,
  PauseCircle,
  XCircle,
  Eye,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  PlayCircle,
  Ticket
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { apiClient } from '../../lib/api-client';
import {
  AccessEntitlement,
  AccessEntitlementDetail,
  EntitlementSummaryMetrics,
} from '../../types';
import { ManualGrantModal } from './ManualGrantModal';
import { SuspendModal } from './SuspendModal';
import { RevokeModal } from './RevokeModal';
import { EntitlementDetailView } from './EntitlementDetailView';

export function EntitlementsListPage() {
  const { selectedCompany } = useAuth();

  // State
  const [items, setItems] = useState<AccessEntitlement[]>([]);
  const [summary, setSummary] = useState<EntitlementSummaryMetrics>({
    total_entitlements: 0,
    active: 0,
    expiring_soon: 0,
    suspended: 0,
    expired: 0,
    revoked: 0,
    pending: 0,
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [quickFilter, setQuickFilter] = useState<string>('ALL');

  // Modals
  const [detailItem, setDetailItem] = useState<AccessEntitlementDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState<boolean>(false);
  const [manualGrantOpen, setManualGrantOpen] = useState<boolean>(false);
  const [suspendTarget, setSuspendTarget] = useState<AccessEntitlement | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<AccessEntitlement | null>(null);

  const fetchEntitlements = useCallback(async () => {
    if (!selectedCompany) return;
    setLoading(true);

    try {
      const params = new URLSearchParams({
        company_id: selectedCompany.id,
        page: page.toString(),
        page_size: '15',
      });

      if (search) params.append('search', search);
      if (sourceFilter) params.append('source_type', sourceFilter);

      if (quickFilter === 'EXPIRING_SOON') {
        const now = new Date();
        const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
        params.append('status', 'ACTIVE');
        params.append('expires_after', now.toISOString());
        params.append('expires_before', tomorrow.toISOString());
      } else if (quickFilter !== 'ALL') {
        params.append('status', quickFilter);
      }

      const res = await apiClient.get<{
        results: AccessEntitlement[];
        count: number;
        page: number;
        total_pages: number;
        summary: EntitlementSummaryMetrics;
      }>(`/entitlements/?${params.toString()}`);

      setItems(res.data.results);
      setTotalCount(res.data.count);
      setTotalPages(res.data.total_pages);
      if (res.data.summary) {
        setSummary(res.data.summary);
      }
    } catch {
      // Handled gracefully
    } finally {
      setLoading(false);
    }
  }, [selectedCompany, page, search, sourceFilter, quickFilter]);

  useEffect(() => {
    fetchEntitlements();
  }, [fetchEntitlements]);

  const handleOpenDetail = async (id: string) => {
    if (!selectedCompany) return;
    try {
      const res = await apiClient.get<AccessEntitlementDetail>(
        `/entitlements/${id}/?company_id=${selectedCompany.id}`
      );
      setDetailItem(res.data);
      setDetailOpen(true);
    } catch {
      alert('Failed to load entitlement details.');
    }
  };

  const handleResume = async (item: AccessEntitlement | AccessEntitlementDetail) => {
    if (!selectedCompany) return;
    try {
      await apiClient.post(`/entitlements/${item.id}/resume/`, {
        company_id: selectedCompany.id,
      });
      fetchEntitlements();
      if (detailOpen && detailItem?.id === item.id) {
        handleOpenDetail(item.id);
      }
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      alert(apiErr?.detail || 'Failed to resume entitlement.');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return <Badge variant="success">Active</Badge>;
      case 'SUSPENDED':
        return <Badge variant="warning">Suspended</Badge>;
      case 'EXPIRED':
        return <Badge variant="secondary">Expired</Badge>;
      case 'REVOKED':
        return <Badge variant="destructive">Revoked</Badge>;
      case 'PENDING':
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  const formatBytes = (bytes?: number | null) => {
    if (bytes === undefined || bytes === null) return 'Unlimited';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
    return `${mb.toFixed(0)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Access Entitlements</h1>
          <p className="text-sm text-muted-foreground">
            Manage customer access rights, plan rate shaping snapshots, and lifecycle authorization states.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setManualGrantOpen(true)}
            className="bg-primary text-primary-foreground"
          >
            <Plus className="mr-1.5 h-4 w-4" /> Grant Access
          </Button>
          <Button variant="outline" size="sm" onClick={fetchEntitlements} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </div>
      </div>

      {/* Summary Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-4 bg-emerald-50/30 dark:bg-emerald-950/20 border-emerald-200/50 dark:border-emerald-900/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 uppercase">Active</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 mt-2">{summary.active}</div>
        </Card>

        <Card className="p-4 bg-amber-50/30 dark:bg-amber-950/20 border-amber-200/50 dark:border-amber-900/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-800 dark:text-amber-300 uppercase">Expiring (24h)</span>
            <Clock className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-700 dark:text-amber-300 mt-2">{summary.expiring_soon}</div>
        </Card>

        <Card className="p-4 bg-card/60">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Suspended</span>
            <PauseCircle className="h-4 w-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-foreground mt-2">{summary.suspended}</div>
        </Card>

        <Card className="p-4 bg-muted/40">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase">Expired / Revoked</span>
            <XCircle className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="text-2xl font-bold text-muted-foreground mt-2">{summary.expired + summary.revoked}</div>
        </Card>
      </div>

      {/* Main Filter & Table Card */}
      <Card>
        <CardHeader className="pb-3 border-b border-border">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            {/* Quick Filter Tabs */}
            <div className="flex items-center gap-1 bg-muted p-1 rounded-lg overflow-x-auto">
              {[
                { id: 'ALL', label: 'All' },
                { id: 'ACTIVE', label: 'Active' },
                { id: 'EXPIRING_SOON', label: 'Expiring Soon' },
                { id: 'SUSPENDED', label: 'Suspended' },
                { id: 'EXPIRED', label: 'Expired' },
                { id: 'REVOKED', label: 'Revoked' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setQuickFilter(tab.id);
                    setPage(1);
                  }}
                  className={`px-3 py-1 text-xs font-semibold rounded-md transition whitespace-nowrap ${
                    quickFilter === tab.id
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative w-full md:w-72">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search reference, voucher, plan..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-9 text-xs"
              />
            </div>
          </div>

          {/* Secondary Filter: Source Type */}
          <div className="flex items-center gap-3 pt-3">
            <div className="w-48">
              <label className="block text-[11px] font-medium text-muted-foreground mb-1">Source Type</label>
              <select
                value={sourceFilter}
                onChange={(e) => {
                  setSourceFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
              >
                <option value="">All Sources</option>
                <option value="VOUCHER">Voucher Token</option>
                <option value="MANUAL">Manual Grant</option>
                <option value="PAYMENT">Direct Payment</option>
                <option value="PROMOTION">Promotion</option>
                <option value="ADMIN">Administrator</option>
              </select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {/* Desktop Table View */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-muted/30 text-xs font-semibold uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">Reference</th>
                  <th className="px-4 py-3">Plan</th>
                  <th className="px-4 py-3">Voucher</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Bandwidth</th>
                  <th className="px-4 py-3">Data Limit</th>
                  <th className="px-4 py-3">Expires</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-muted-foreground">
                      <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-primary" />
                      Loading access entitlements...
                    </td>
                  </tr>
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-muted-foreground">
                      No access entitlements found matching your filters.
                    </td>
                  </tr>
                ) : (
                  items.map((item) => (
                    <tr
                      key={item.id}
                      onClick={() => handleOpenDetail(item.id)}
                      className="cursor-pointer hover:bg-accent/40 transition"
                    >
                      <td className="px-4 py-3 font-mono font-bold text-xs text-foreground">
                        {item.reference}
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-xs text-foreground">{item.plan_name}</div>
                        <div className="text-[11px] text-muted-foreground font-mono">{item.plan_code}</div>
                      </td>
                      <td className="px-4 py-3">
                        {item.voucher_code ? (
                          <span className="font-mono text-xs font-bold text-primary flex items-center gap-1">
                            <Ticket className="h-3 w-3" /> {item.voucher_code}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline" className="text-[10px] font-semibold">
                          {item.source_type}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">{getStatusBadge(item.status)}</td>
                      <td className="px-4 py-3 text-xs text-foreground font-mono">
                        {item.download_speed_kbps ? `${item.download_speed_kbps / 1024}M / ${item.upload_speed_kbps ? item.upload_speed_kbps / 1024 : 0}M` : 'Unlimited'}
                      </td>
                      <td className="px-4 py-3 text-xs text-foreground font-mono">
                        {formatBytes(item.data_limit_bytes)}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground font-mono whitespace-nowrap">
                        {item.expires_at ? new Date(item.expires_at).toLocaleString() : 'Never'}
                      </td>
                      <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end space-x-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenDetail(item.id)}
                            className="h-8 w-8 p-0"
                            title="View Details"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          {item.status === 'ACTIVE' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSuspendTarget(item)}
                              className="h-8 w-8 p-0 text-amber-600 hover:text-amber-700"
                              title="Suspend Access"
                            >
                              <PauseCircle className="h-4 w-4" />
                            </Button>
                          )}
                          {item.status === 'SUSPENDED' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleResume(item)}
                              className="h-8 w-8 p-0 text-emerald-600 hover:text-emerald-700"
                              title="Resume Access"
                            >
                              <PlayCircle className="h-4 w-4" />
                            </Button>
                          )}
                          {['PENDING', 'ACTIVE', 'SUSPENDED'].includes(item.status) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setRevokeTarget(item)}
                              className="h-8 w-8 p-0 text-destructive hover:text-destructive/80"
                              title="Revoke Access"
                            >
                              <ShieldAlert className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
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
                Loading entitlements...
              </div>
            ) : items.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground text-xs">
                No access entitlements found.
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleOpenDetail(item.id)}
                  className="p-3.5 space-y-2 hover:bg-accent/40 transition cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-foreground">{item.reference}</span>
                    {getStatusBadge(item.status)}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground">{item.plan_name}</span>
                    <span className="uppercase text-[10px]">{item.source_type}</span>
                  </div>
                  {item.voucher_code && (
                    <div className="text-xs font-mono font-bold text-primary flex items-center gap-1">
                      Voucher: {item.voucher_code}
                    </div>
                  )}
                  <div className="text-[11px] text-muted-foreground flex items-center justify-between pt-1">
                    <span>Quota: {formatBytes(item.data_limit_bytes)}</span>
                    <span>Expires: {item.expires_at ? new Date(item.expires_at).toLocaleDateString() : 'Never'}</span>
                  </div>
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

      {/* Modals */}
      {selectedCompany && (
        <>
          <ManualGrantModal
            isOpen={manualGrantOpen}
            companyId={selectedCompany.id}
            onClose={() => setManualGrantOpen(false)}
            onSuccess={() => fetchEntitlements()}
          />
          <SuspendModal
            item={suspendTarget}
            companyId={selectedCompany.id}
            isOpen={!!suspendTarget}
            onClose={() => setSuspendTarget(null)}
            onSuccess={() => fetchEntitlements()}
          />
          <RevokeModal
            item={revokeTarget}
            companyId={selectedCompany.id}
            isOpen={!!revokeTarget}
            onClose={() => setRevokeTarget(null)}
            onSuccess={() => fetchEntitlements()}
          />
          <EntitlementDetailView
            item={detailItem}
            isOpen={detailOpen}
            onClose={() => {
              setDetailOpen(false);
              setDetailItem(null);
            }}
            onSuspend={(item) => {
              setDetailOpen(false);
              setSuspendTarget(item);
            }}
            onResume={handleResume}
            onRevoke={(item) => {
              setDetailOpen(false);
              setRevokeTarget(item);
            }}
          />
        </>
      )}
    </div>
  );
}
