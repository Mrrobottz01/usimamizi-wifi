import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Repeat,
  Search,
  RefreshCw,
} from 'lucide-react';
import { Subscription, SubscriptionStatus } from '../../types';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';

export const SubscriptionsListPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchSubscriptions = useCallback(async () => {
    if (!selectedCompany) return;
    setLoading(true);
    try {
      let url = `/api/v1/subscriptions/?company_id=${selectedCompany.id}`;
      if (searchQuery.trim()) url += `&q=${encodeURIComponent(searchQuery.trim())}`;
      if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;

      const res = await apiClient.get<Subscription[]>(url);
      setSubscriptions(res.data);
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to load subscriptions', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [selectedCompany, searchQuery, statusFilter, toast]);

  useEffect(() => {
    fetchSubscriptions();
  }, [fetchSubscriptions]);

  const handleRenew = async (sub: Subscription) => {
    try {
      await apiClient.post(`/api/v1/subscriptions/${sub.id}/renew/`);
      toast({ title: `Subscription for ${sub.customer_phone} renewed (lossless period extension)!`, type: 'success' });
      fetchSubscriptions();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Renewal failed', type: 'error' });
    }
  };

  const handleSuspend = async (sub: Subscription) => {
    try {
      await apiClient.post(`/api/v1/subscriptions/${sub.id}/suspend/`, { reason: 'Admin manual suspension' });
      toast({ title: 'Subscription suspended and active sessions disconnected', type: 'success' });
      fetchSubscriptions();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Suspension failed', type: 'error' });
    }
  };

  const handleReactivate = async (sub: Subscription) => {
    try {
      await apiClient.post(`/api/v1/subscriptions/${sub.id}/reactivate/`);
      toast({ title: 'Subscription reactivated', type: 'success' });
      fetchSubscriptions();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Reactivation failed', type: 'error' });
    }
  };

  const getStatusBadge = (status: SubscriptionStatus) => {
    switch (status) {
      case 'ACTIVE':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">Active</span>;
      case 'GRACE':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">Grace Period</span>;
      case 'SUSPENDED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/20">Suspended</span>;
      case 'EXPIRED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground">Expired</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-muted text-muted-foreground">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Repeat className="h-6 w-6 text-primary" />
            Recurring Subscriptions
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track customer recurring access periods, lossless manual renewals, and grace window enforcement.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchSubscriptions()}
            disabled={loading}
            className="inline-flex items-center justify-center p-2 rounded-lg border border-border bg-card text-foreground hover:bg-accent transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by customer phone or plan name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="GRACE">Grace</option>
          <option value="SUSPENDED">Suspended</option>
          <option value="EXPIRED">Expired</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Customer</th>
                <th className="py-3.5 px-4">Plan</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Period Validity</th>
                <th className="py-3.5 px-4">Remaining</th>
                <th className="py-3.5 px-4">Mode / Source</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted-foreground">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                    Loading subscriptions...
                  </td>
                </tr>
              ) : subscriptions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted-foreground">
                    No subscriptions found.
                  </td>
                </tr>
              ) : (
                subscriptions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-accent/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <button
                        onClick={() => navigate(`/customers/${sub.customer_id}`)}
                        className="font-semibold text-foreground hover:text-primary transition-colors text-left"
                      >
                        {sub.customer_name || 'Guest User'}
                      </button>
                      <div className="text-xs text-muted-foreground font-mono">
                        {sub.customer_phone}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-foreground">{sub.plan_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {sub.plan_currency} {Number(sub.plan_price).toLocaleString()}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">{getStatusBadge(sub.status)}</td>

                    <td className="py-3.5 px-4 text-xs font-mono text-muted-foreground">
                      <div>{sub.current_period_start ? new Date(sub.current_period_start).toLocaleDateString() : '—'}</div>
                      <div className="text-[11px] text-muted-foreground/80">
                        → {sub.current_period_end ? new Date(sub.current_period_end).toLocaleString() : '—'}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      {sub.remaining_seconds > 0 ? (
                        <span className="font-mono font-bold text-xs text-emerald-500">
                          {Math.floor(sub.remaining_seconds / 3600)}h {Math.floor((sub.remaining_seconds % 3600) / 60)}m
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">0h 0m</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-xs">
                      <div className="text-foreground font-medium">{sub.renewal_mode}</div>
                      <div className="text-muted-foreground text-[11px]">{sub.source}</div>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleRenew(sub)}
                          className="px-2.5 py-1 text-xs font-semibold rounded border border-border text-primary hover:bg-primary/10 transition-colors"
                          title="Lossless Renewal (Extends period without cutting remaining time)"
                        >
                          Renew
                        </button>
                        {sub.status === 'ACTIVE' ? (
                          <button
                            onClick={() => handleSuspend(sub)}
                            className="px-2 py-1 text-xs font-medium rounded border border-border text-amber-500 hover:bg-amber-500/10 transition-colors"
                          >
                            Suspend
                          </button>
                        ) : sub.status === 'SUSPENDED' ? (
                          <button
                            onClick={() => handleReactivate(sub)}
                            className="px-2 py-1 text-xs font-medium rounded border border-border text-emerald-500 hover:bg-emerald-500/10 transition-colors"
                          >
                            Reactivate
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
