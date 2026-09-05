import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Search,
  Plus,
  ShieldCheck,
  Ban,
  Clock,
  Smartphone,
  CreditCard,
  ChevronRight,
  RefreshCw,
  X,
} from 'lucide-react';
import { Customer, CustomerStatus } from '../../types';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';

interface CustomersResponse {
  metrics: {
    total_customers: number;
    active_subscribers: number;
    expired_subscribers: number;
    suspended_count: number;
    new_today: number;
  };
  results: Customer[];
}

export const CustomersListPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [metrics, setMetrics] = useState<CustomersResponse['metrics']>({
    total_customers: 0,
    active_subscribers: 0,
    expired_subscribers: 0,
    suspended_count: 0,
    new_today: 0,
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Create Customer Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({
    phone: '',
    first_name: '',
    last_name: '',
    email: '',
    language: 'EN' as 'EN' | 'SW',
    notes: '',
  });

  const fetchCustomers = useCallback(async () => {
    if (!selectedCompany) return;
    setLoading(true);
    try {
      let url = `/api/v1/customers/?company_id=${selectedCompany.id}`;
      if (searchQuery.trim()) url += `&q=${encodeURIComponent(searchQuery.trim())}`;
      if (statusFilter) url += `&status=${encodeURIComponent(statusFilter)}`;

      const res = await apiClient.get<CustomersResponse>(url);
      setCustomers(res.data.results);
      setMetrics(res.data.metrics);
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to load customers', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [selectedCompany, searchQuery, statusFilter, toast]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const handleCreateCustomer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompany || !formData.phone.trim()) return;

    setCreating(true);
    try {
      await apiClient.post('/api/v1/customers/', {
        company_id: selectedCompany.id,
        ...formData,
      });
      toast({ title: 'Customer created successfully', type: 'success' });
      setIsCreateOpen(false);
      setFormData({ phone: '', first_name: '', last_name: '', email: '', language: 'EN', notes: '' });
      fetchCustomers();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to create customer', type: 'error' });
    } finally {
      setCreating(false);
    }
  };

  const handleStatusAction = async (customer: Customer, action: 'suspend' | 'reactivate' | 'block') => {
    try {
      await apiClient.post(`/api/v1/customers/${customer.id}/${action}/`, {
        reason: `Admin manual action: ${action}`,
      });
      toast({ title: `Customer ${action}ed successfully`, type: 'success' });
      fetchCustomers();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || `Failed to ${action} customer`, type: 'error' });
    }
  };

  const getStatusBadge = (status: CustomerStatus) => {
    switch (status) {
      case 'ACTIVE':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">Active</span>;
      case 'SUSPENDED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20">Suspended</span>;
      case 'BLOCKED':
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-500 border border-rose-500/20">Blocked</span>;
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
            <Users className="h-6 w-6 text-primary" />
            Customers & Subscriptions
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage persistent customer identities, devices, and recurring internet subscriptions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchCustomers()}
            disabled={loading}
            className="inline-flex items-center justify-center p-2 rounded-lg border border-border bg-card text-foreground hover:bg-accent transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="h-4 w-4" />
            Add Customer
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium mb-2">
            <span>Total Customers</span>
            <Users className="h-4 w-4 text-primary" />
          </div>
          <div className="text-2xl font-bold text-foreground">{metrics.total_customers}</div>
          <div className="text-xs text-muted-foreground mt-1">
            +{metrics.new_today} registered today
          </div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium mb-2">
            <span>Active Subscribers</span>
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-500">{metrics.active_subscribers}</div>
          <div className="text-xs text-muted-foreground mt-1">Currently connected or in grace</div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium mb-2">
            <span>Expired</span>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-500">{metrics.expired_subscribers}</div>
          <div className="text-xs text-muted-foreground mt-1">Pending plan renewal</div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium mb-2">
            <span>Suspended/Blocked</span>
            <Ban className="h-4 w-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-500">{metrics.suspended_count}</div>
          <div className="text-xs text-muted-foreground mt-1">Restricted access</div>
        </div>

        <div className="p-4 rounded-xl border border-border bg-card shadow-sm col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium mb-2">
            <span>Quick Nav</span>
            <CreditCard className="h-4 w-4 text-blue-500" />
          </div>
          <button
            onClick={() => navigate('/subscriptions')}
            className="text-xs font-semibold text-primary hover:underline flex items-center gap-1 mt-2"
          >
            View All Subscriptions <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by phone, name, email, or device MAC..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 text-sm rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="SUSPENDED">Suspended</option>
          <option value="BLOCKED">Blocked</option>
        </select>
      </div>

      {/* Customers Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Customer</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Active Subscription</th>
                <th className="py-3.5 px-4">Devices</th>
                <th className="py-3.5 px-4">Total Spent</th>
                <th className="py-3.5 px-4">Last Seen</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted-foreground">
                    <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-primary" />
                    Loading customers...
                  </td>
                </tr>
              ) : customers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted-foreground">
                    <Users className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                    No customers found matching the criteria.
                  </td>
                </tr>
              ) : (
                customers.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/customers/${c.id}`)}
                    className="hover:bg-accent/40 cursor-pointer transition-colors group"
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-foreground group-hover:text-primary transition-colors">
                        {c.full_name || 'Guest User'}
                      </div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {c.normalized_phone || c.phone}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">{getStatusBadge(c.status)}</td>

                    <td className="py-3.5 px-4">
                      {c.active_subscription ? (
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary">
                            {c.active_subscription.plan_name}
                          </span>
                          <span className="text-xs text-muted-foreground font-mono">
                            {Math.ceil(c.active_subscription.remaining_seconds / 3600)}h left
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground italic">No active plan</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5 text-muted-foreground">
                        <Smartphone className="h-3.5 w-3.5" />
                        <span>{c.devices_count}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-mono font-medium text-foreground">
                      TZS {Number(c.total_spent).toLocaleString()}
                    </td>

                    <td className="py-3.5 px-4 text-xs text-muted-foreground">
                      {c.last_seen_at ? new Date(c.last_seen_at).toLocaleDateString() : 'Never'}
                    </td>

                    <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        {c.status === 'ACTIVE' ? (
                          <button
                            onClick={() => handleStatusAction(c, 'suspend')}
                            className="px-2 py-1 text-xs font-medium rounded border border-border text-amber-500 hover:bg-amber-500/10 transition-colors"
                            title="Suspend Access"
                          >
                            Suspend
                          </button>
                        ) : (
                          <button
                            onClick={() => handleStatusAction(c, 'reactivate')}
                            className="px-2 py-1 text-xs font-medium rounded border border-border text-emerald-500 hover:bg-emerald-500/10 transition-colors"
                            title="Reactivate Access"
                          >
                            Reactivate
                          </button>
                        )}
                        <button
                          onClick={() => navigate(`/customers/${c.id}`)}
                          className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Customer Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <Users className="h-5 w-5 text-primary" />
                Add New Customer
              </h2>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCustomer} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Phone Number (Tanzanian) <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 0712345678 or +255712345678"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">First Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Juma"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Last Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Rashid"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Email Address</label>
                <input
                  type="email"
                  placeholder="e.g. customer@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1">Language</label>
                  <select
                    value={formData.language}
                    onChange={(e) => setFormData({ ...formData, language: e.target.value as any })}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  >
                    <option value="EN">English</option>
                    <option value="SW">Kiswahili</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Internal Notes</label>
                <textarea
                  rows={2}
                  placeholder="Add optional notes about this customer..."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-foreground hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create Customer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
