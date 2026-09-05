import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Smartphone,
  CreditCard,
  History,
  Clock,
  Plus,
  RefreshCw,
  Repeat,
  X,
  Laptop,
} from 'lucide-react';
import {
  Customer,
  CustomerDevice,
  CustomerTimelineItem,
  Plan,
  Subscription,
} from '../../types';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';

export const CustomerDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { selectedCompany } = useAuth();
  const { toast } = useToast();

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'subscriptions' | 'devices' | 'timeline'>('overview');

  // Sub-data states
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [devices, setDevices] = useState<CustomerDevice[]>([]);
  const [timeline, setTimeline] = useState<CustomerTimelineItem[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);

  // Modals
  const [isAddDeviceOpen, setIsAddDeviceOpen] = useState(false);
  const [newDeviceMac, setNewDeviceMac] = useState('');
  const [newDeviceName, setNewDeviceName] = useState('');
  const [newDeviceType, setNewDeviceType] = useState<'MOBILE' | 'LAPTOP' | 'TABLET' | 'OTHER'>('MOBILE');

  const [isNewSubOpen, setIsNewSubOpen] = useState(false);
  const [selectedPlanId, setSelectedPlanId] = useState('');

  const fetchCustomer = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await apiClient.get<Customer>(`/api/v1/customers/${id}/`);
      setCustomer(res.data);
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Customer not found', type: 'error' });
      navigate('/customers');
    } finally {
      setLoading(false);
    }
  }, [id, navigate, toast]);

  const fetchSubscriptions = useCallback(async () => {
    if (!id) return;
    try {
      const res = await apiClient.get<Subscription[]>(`/api/v1/customers/${id}/subscriptions/`);
      setSubscriptions(res.data);
    } catch (err) {
      console.error('Failed to load subscriptions', err);
    }
  }, [id]);

  const fetchDevices = useCallback(async () => {
    if (!id) return;
    try {
      const res = await apiClient.get<CustomerDevice[]>(`/api/v1/customers/${id}/devices/`);
      setDevices(res.data);
    } catch (err) {
      console.error('Failed to load devices', err);
    }
  }, [id]);

  const fetchTimeline = useCallback(async () => {
    if (!id) return;
    try {
      const res = await apiClient.get<CustomerTimelineItem[]>(`/api/v1/customers/${id}/timeline/`);
      setTimeline(res.data);
    } catch (err) {
      console.error('Failed to load timeline', err);
    }
  }, [id]);

  const fetchPlans = useCallback(async () => {
    if (!selectedCompany) return;
    try {
      const res = await apiClient.get<{ results: Plan[] }>(`/api/v1/plans/?company_id=${selectedCompany.id}&is_active=true`);
      setPlans(res.data.results || []);
    } catch (err) {
      console.error('Failed to load plans', err);
    }
  }, [selectedCompany]);

  useEffect(() => {
    fetchCustomer();
    fetchSubscriptions();
    fetchDevices();
    fetchTimeline();
    fetchPlans();
  }, [fetchCustomer, fetchSubscriptions, fetchDevices, fetchTimeline, fetchPlans]);

  const handleStatusAction = async (action: 'suspend' | 'reactivate' | 'block') => {
    if (!customer) return;
    try {
      await apiClient.post(`/api/v1/customers/${customer.id}/${action}/`, {
        reason: `Admin requested ${action}`,
      });
      toast({ title: `Customer ${action}ed successfully`, type: 'success' });
      fetchCustomer();
      fetchSubscriptions();
      fetchTimeline();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || `Failed to ${action} customer`, type: 'error' });
    }
  };

  const handleRenewSubscription = async (subId: string) => {
    try {
      await apiClient.post(`/api/v1/subscriptions/${subId}/renew/`);
      toast({ title: 'Subscription renewed successfully (lossless period extension)!', type: 'success' });
      fetchCustomer();
      fetchSubscriptions();
      fetchTimeline();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to renew subscription', type: 'error' });
    }
  };

  const handleCreateSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customer || !selectedPlanId) return;

    try {
      await apiClient.post('/api/v1/subscriptions/', {
        company_id: customer.company_id,
        customer_id: customer.id,
        plan_id: selectedPlanId,
      });
      toast({ title: 'Subscription granted and activated successfully', type: 'success' });
      setIsNewSubOpen(false);
      setSelectedPlanId('');
      fetchCustomer();
      fetchSubscriptions();
      fetchTimeline();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to create subscription', type: 'error' });
    }
  };

  const handleAddDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customer || !newDeviceMac.trim()) return;

    try {
      await apiClient.post(`/api/v1/customers/${customer.id}/devices/`, {
        mac_address: newDeviceMac.trim(),
        device_name: newDeviceName.trim(),
        device_type: newDeviceType,
      });
      toast({ title: 'Device added successfully', type: 'success' });
      setIsAddDeviceOpen(false);
      setNewDeviceMac('');
      setNewDeviceName('');
      fetchDevices();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to add device', type: 'error' });
    }
  };

  const handleDeviceAction = async (deviceId: string, action: 'toggle-trust' | 'toggle-block') => {
    if (!customer) return;
    try {
      await apiClient.post(`/api/v1/customers/${customer.id}/devices/${deviceId}/${action}/`);
      toast({ title: 'Device updated successfully', type: 'success' });
      fetchDevices();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to update device', type: 'error' });
    }
  };

  if (loading || !customer) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const activeSub = subscriptions.find((s) => s.status === 'ACTIVE' || s.status === 'GRACE');

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <button
          onClick={() => navigate('/customers')}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Customers
        </button>

        <div className="flex items-center gap-2">
          {customer.status === 'ACTIVE' ? (
            <button
              onClick={() => handleStatusAction('suspend')}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-amber-500/30 text-amber-500 hover:bg-amber-500/10 transition-colors"
            >
              Suspend Customer
            </button>
          ) : (
            <button
              onClick={() => handleStatusAction('reactivate')}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10 transition-colors"
            >
              Reactivate Customer
            </button>
          )}

          {customer.status !== 'BLOCKED' && (
            <button
              onClick={() => handleStatusAction('block')}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-rose-500/30 text-rose-500 hover:bg-rose-500/10 transition-colors"
            >
              Block
            </button>
          )}

          <button
            onClick={() => setIsNewSubOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            Grant Subscription
          </button>
        </div>
      </div>

      {/* Profile Header Card */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="h-14 w-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-bold text-xl border border-primary/20">
            {customer.first_name ? customer.first_name[0].toUpperCase() : 'U'}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-foreground">
                {customer.full_name || 'Guest User'}
              </h1>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                customer.status === 'ACTIVE'
                  ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                  : customer.status === 'SUSPENDED'
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                  : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
              }`}>
                {customer.status}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground font-mono">
              <span>{customer.normalized_phone}</span>
              {customer.email && (
                <>
                  <span>•</span>
                  <span>{customer.email}</span>
                </>
              )}
              <span>•</span>
              <span className="font-sans text-xs">Lang: {customer.language}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 border-t md:border-t-0 md:border-l border-border pt-4 md:pt-0 md:pl-6 text-sm">
          <div>
            <div className="text-xs text-muted-foreground font-medium">Total Spend</div>
            <div className="text-lg font-bold text-foreground font-mono mt-0.5">
              TZS {Number(customer.total_spent).toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Devices</div>
            <div className="text-lg font-bold text-foreground font-mono mt-0.5">
              {devices.length}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground font-medium">Member Since</div>
            <div className="text-xs text-muted-foreground mt-1">
              {new Date(customer.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border flex items-center gap-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'overview'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <CreditCard className="h-4 w-4" />
          Overview & Active Plan
        </button>
        <button
          onClick={() => setActiveTab('subscriptions')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'subscriptions'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Repeat className="h-4 w-4" />
          Subscriptions ({subscriptions.length})
        </button>
        <button
          onClick={() => setActiveTab('devices')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'devices'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Smartphone className="h-4 w-4" />
          Devices ({devices.length})
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'timeline'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <History className="h-4 w-4" />
          Activity Timeline ({timeline.length})
        </button>
      </div>

      {/* Tab 1: Overview & Active Subscription */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            {/* Active Subscription Banner */}
            <div className="p-6 rounded-xl border border-border bg-card shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-primary" />
                  Active Subscription
                </h2>
                {activeSub && (
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                    activeSub.status === 'ACTIVE'
                      ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                  }`}>
                    {activeSub.status}
                  </span>
                )}
              </div>

              {activeSub ? (
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 rounded-lg bg-muted/40 border border-border gap-4">
                    <div>
                      <div className="text-xl font-bold text-foreground">{activeSub.plan_name}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Valid: {activeSub.current_period_start ? new Date(activeSub.current_period_start).toLocaleString() : 'Now'} →{' '}
                        {activeSub.current_period_end ? new Date(activeSub.current_period_end).toLocaleString() : 'Indefinite'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-black text-primary font-mono">
                        {Math.floor(activeSub.remaining_seconds / 3600)}h {Math.floor((activeSub.remaining_seconds % 3600) / 60)}m
                      </div>
                      <div className="text-xs text-muted-foreground">Remaining Paid Time</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <div className="text-xs text-muted-foreground">
                      Mode: <span className="font-semibold text-foreground">{activeSub.renewal_mode}</span>
                    </div>
                    <button
                      onClick={() => handleRenewSubscription(activeSub.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 transition-colors shadow-sm"
                    >
                      <Repeat className="h-3.5 w-3.5" />
                      Extend / Renew Now (+1 Period)
                    </button>
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">No active subscription currently active.</p>
                  <button
                    onClick={() => setIsNewSubOpen(true)}
                    className="mt-3 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                  >
                    Grant Plan Now
                  </button>
                </div>
              )}
            </div>

            {/* Internal Notes */}
            <div className="p-6 rounded-xl border border-border bg-card shadow-sm">
              <h2 className="text-base font-bold text-foreground mb-3">Customer Notes</h2>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {customer.notes || 'No customer notes added yet.'}
              </p>
            </div>
          </div>

          {/* Quick Info Sidebar */}
          <div className="space-y-6">
            <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
              <h2 className="text-sm font-bold text-foreground uppercase tracking-wider text-muted-foreground">
                Account Details
              </h2>
              <div className="text-sm space-y-2.5">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Customer ID:</span>
                  <span className="font-mono text-xs text-foreground truncate max-w-[150px]">{customer.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Normalized Phone:</span>
                  <span className="font-mono font-semibold text-foreground">{customer.normalized_phone}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Language:</span>
                  <span className="font-medium text-foreground">{customer.language === 'SW' ? 'Kiswahili' : 'English'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="font-semibold text-foreground">{customer.status}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Seen:</span>
                  <span className="text-xs text-muted-foreground">
                    {customer.last_seen_at ? new Date(customer.last_seen_at).toLocaleString() : 'Never'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Subscriptions Table */}
      {activeTab === 'subscriptions' && (
        <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground text-xs font-semibold uppercase tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Plan</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Period Start</th>
                <th className="py-3.5 px-4">Period End</th>
                <th className="py-3.5 px-4">Source</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {subscriptions.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted-foreground">
                    No subscriptions found for this customer.
                  </td>
                </tr>
              ) : (
                subscriptions.map((sub) => (
                  <tr key={sub.id} className="hover:bg-accent/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-foreground">{sub.plan_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {sub.plan_currency} {Number(sub.plan_price).toLocaleString()}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                        sub.status === 'ACTIVE'
                          ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                          : sub.status === 'GRACE'
                          ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                          : 'bg-muted text-muted-foreground'
                      }`}>
                        {sub.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs font-mono text-muted-foreground">
                      {sub.current_period_start ? new Date(sub.current_period_start).toLocaleString() : '—'}
                    </td>
                    <td className="py-3.5 px-4 text-xs font-mono text-muted-foreground">
                      {sub.current_period_end ? new Date(sub.current_period_end).toLocaleString() : '—'}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-muted-foreground">{sub.source}</td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleRenewSubscription(sub.id)}
                        className="px-2.5 py-1 text-xs font-semibold rounded border border-border text-primary hover:bg-primary/10 transition-colors"
                      >
                        Renew
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 3: Devices Table */}
      {activeTab === 'devices' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-foreground">Registered Devices</h2>
            <button
              onClick={() => setIsAddDeviceOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Device
            </button>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Device</th>
                  <th className="py-3.5 px-4">MAC Address</th>
                  <th className="py-3.5 px-4">Trust Status</th>
                  <th className="py-3.5 px-4">Access Status</th>
                  <th className="py-3.5 px-4">First Seen</th>
                  <th className="py-3.5 px-4">Last Seen</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {devices.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-muted-foreground">
                      No devices observed or registered for this customer yet.
                    </td>
                  </tr>
                ) : (
                  devices.map((dev) => (
                    <tr key={dev.id} className="hover:bg-accent/40 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          {dev.device_type === 'LAPTOP' ? (
                            <Laptop className="h-4 w-4 text-primary" />
                          ) : (
                            <Smartphone className="h-4 w-4 text-primary" />
                          )}
                          <span className="font-semibold text-foreground">
                            {dev.device_name || dev.device_type}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-xs font-semibold text-foreground">
                        {dev.mac_address}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          dev.is_trusted ? 'bg-emerald-500/10 text-emerald-500' : 'bg-muted text-muted-foreground'
                        }`}>
                          {dev.is_trusted ? 'Trusted' : 'Standard'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          dev.is_blocked ? 'bg-rose-500/10 text-rose-500' : 'bg-emerald-500/10 text-emerald-500'
                        }`}>
                          {dev.is_blocked ? 'Blocked' : 'Allowed'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-xs text-muted-foreground">
                        {new Date(dev.first_seen_at).toLocaleDateString()}
                      </td>
                      <td className="py-3.5 px-4 text-xs text-muted-foreground">
                        {dev.last_seen_at ? new Date(dev.last_seen_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleDeviceAction(dev.id, 'toggle-trust')}
                            className="px-2 py-1 text-xs rounded border border-border text-muted-foreground hover:text-foreground"
                          >
                            {dev.is_trusted ? 'Untrust' : 'Trust'}
                          </button>
                          <button
                            onClick={() => handleDeviceAction(dev.id, 'toggle-block')}
                            className={`px-2 py-1 text-xs rounded border ${
                              dev.is_blocked
                                ? 'border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10'
                                : 'border-rose-500/30 text-rose-500 hover:bg-rose-500/10'
                            }`}
                          >
                            {dev.is_blocked ? 'Unblock' : 'Block'}
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
      )}

      {/* Tab 4: Unified Timeline */}
      {activeTab === 'timeline' && (
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-6">
          <h2 className="text-base font-bold text-foreground flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Unified Chronological Activity
          </h2>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
            {timeline.length === 0 ? (
              <p className="text-sm text-muted-foreground">No activity recorded for this customer yet.</p>
            ) : (
              timeline.map((item, idx) => (
                <div key={idx} className="relative group">
                  <div className={`absolute -left-6 top-1 h-3.5 w-3.5 rounded-full border-2 border-card ${
                    item.type === 'SUBSCRIPTION_EVENT'
                      ? 'bg-primary'
                      : item.type === 'PAYMENT'
                      ? 'bg-emerald-500'
                      : item.type === 'HOTSPOT_SESSION'
                      ? 'bg-blue-500'
                      : 'bg-amber-500'
                  }`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-foreground">{item.title}</span>
                      <span className="text-[11px] text-muted-foreground font-mono">
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Grant Subscription Modal */}
      {isNewSubOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-base font-bold text-foreground">Grant Subscription</h2>
              <button onClick={() => setIsNewSubOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleCreateSubscription} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  Choose Plan <span className="text-rose-500">*</span>
                </label>
                <select
                  required
                  value={selectedPlanId}
                  onChange={(e) => setSelectedPlanId(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                >
                  <option value="">Select an internet plan...</option>
                  {plans.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} — {p.currency} {Number(p.price).toLocaleString()} ({p.duration_value} {p.duration_unit})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsNewSubOpen(false)}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-foreground hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
                >
                  Grant & Activate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Device Modal */}
      {isAddDeviceOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <h2 className="text-base font-bold text-foreground">Add Customer Device</h2>
              <button onClick={() => setIsAddDeviceOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={handleAddDevice} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">
                  MAC Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. AA:BB:CC:DD:EE:FF"
                  value={newDeviceMac}
                  onChange={(e) => setNewDeviceMac(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Device Name</label>
                <input
                  type="text"
                  placeholder="e.g. Samsung Galaxy A52"
                  value={newDeviceName}
                  onChange={(e) => setNewDeviceName(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1">Device Type</label>
                <select
                  value={newDeviceType}
                  onChange={(e) => setNewDeviceType(e.target.value as any)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                >
                  <option value="MOBILE">Mobile Phone</option>
                  <option value="LAPTOP">Laptop / PC</option>
                  <option value="TABLET">Tablet</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsAddDeviceOpen(false)}
                  className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-foreground hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
                >
                  Save Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
