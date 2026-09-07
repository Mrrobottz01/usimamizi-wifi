import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiClient } from '../../lib/api-client';
import { Button } from '../../components/ui/button';
import {
  ShieldCheck,
  ShieldAlert,
  Shield,
  RefreshCw,
  Sliders,
  Smartphone,
  Laptop,
  CheckCircle2,
  AlertTriangle,
  Info,
  RotateCcw,
  Activity,
  Layers,
  Zap,
} from 'lucide-react';
import {
  AntiTetheringPolicy,
  AntiTetheringRouterStatus,
  AntiTetheringCounters,
} from '../../types';

function formatBytes(bytes?: number): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

interface AntiTetheringSettingsProps {
  hotspotId?: string;
}

export const AntiTetheringSettings: React.FC<AntiTetheringSettingsProps> = ({ hotspotId }) => {
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.id;
  const basePath = hotspotId ? `/api/v1/hotspots/${hotspotId}/anti-tethering` : `/api/v1/hotspots/default/anti-tethering`;

  const [policy, setPolicy] = useState<AntiTetheringPolicy | null>(null);
  const [routerStatus, setRouterStatus] = useState<AntiTetheringRouterStatus | null>(null);
  const [counters, setCounters] = useState<AntiTetheringCounters | null>(null);

  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [refreshingCounters, setRefreshingCounters] = useState(false);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Modals
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [showRestoreModal, setShowRestoreModal] = useState(false);

  const fetchPolicyAndStatus = useCallback(async () => {
    if (!companyId) return;
    try {
      setLoading(true);
      setErrorMsg('');
      const res = await apiClient.get<AntiTetheringPolicy & { router_status?: AntiTetheringRouterStatus }>(
        `${basePath}/?company_id=${companyId}`
      );
      if (res.data) {
        setPolicy(res.data);
        if (res.data.router_status) {
          setRouterStatus(res.data.router_status);
        }
      }
    } catch (err: unknown) {
      console.error('Failed to load anti-tethering policy', err);
      setErrorMsg('Failed to load anti-tethering settings.');
    } finally {
      setLoading(false);
    }
  }, [companyId, basePath]);

  const fetchCounters = useCallback(async () => {
    if (!companyId) return;
    try {
      setRefreshingCounters(true);
      const res = await apiClient.get<AntiTetheringCounters>(
        `${basePath}/counters/?company_id=${companyId}`
      );
      if (res.data) {
        setCounters(res.data);
      }
    } catch (err) {
      console.error('Failed to load counters', err);
    } finally {
      setRefreshingCounters(false);
    }
  }, [companyId, basePath]);

  useEffect(() => {
    fetchPolicyAndStatus();
    fetchCounters();
  }, [fetchPolicyAndStatus, fetchCounters]);

  const handleSyncToRouter = async () => {
    if (!companyId || syncing) return;
    try {
      setSyncing(true);
      setErrorMsg('');
      const res = await apiClient.post<{ success: boolean; live_status?: AntiTetheringRouterStatus }>(
        `${basePath}/sync/?company_id=${companyId}`
      );
      if (res.data && res.data.live_status) {
        setRouterStatus(res.data.live_status);
        if (policy) {
          setPolicy({
            ...policy,
            last_synced_at: new Date().toISOString(),
          });
        }
        fetchCounters();
        setSaveSuccessMsg('Policy successfully reconciled and synchronized with RouterOS.');
        setTimeout(() => setSaveSuccessMsg(''), 4000);
      }
    } catch (err: unknown) {
      console.error('Sync failed', err);
      let msg = 'Router synchronization failed. Ensure RouterOS is reachable.';
      if (err && typeof err === 'object' && 'response' in err) {
        const r = (err as { response?: { data?: { message?: string; detail?: string } } }).response;
        msg = r?.data?.message || r?.data?.detail || msg;
      }
      setErrorMsg(msg);
    } finally {
      setSyncing(false);
    }
  };

  const handleUpdatePolicy = async (updates: Partial<AntiTetheringPolicy>, autoSync = true) => {
    if (!companyId || !policy || savingPolicy) return;
    try {
      setSavingPolicy(true);
      setErrorMsg('');
      const res = await apiClient.patch<AntiTetheringPolicy & { router_status?: AntiTetheringRouterStatus }>(
        `${basePath}/?company_id=${companyId}&sync=${autoSync}`,
        updates
      );
      if (res.data) {
        setPolicy(res.data);
        if (res.data.router_status) {
          setRouterStatus(res.data.router_status);
        }
        fetchCounters();
        setSaveSuccessMsg('Anti-tethering policy saved.');
        setTimeout(() => setSaveSuccessMsg(''), 3000);
      }
    } catch (err: unknown) {
      console.error('Policy update failed', err);
      setErrorMsg('Failed to update anti-tethering policy.');
    } finally {
      setSavingPolicy(false);
    }
  };

  const handleRestoreDefaults = async () => {
    if (!companyId) return;
    try {
      setSyncing(true);
      setErrorMsg('');
      setShowRestoreModal(false);
      const res = await apiClient.post(
        `${basePath}/restore-defaults/?company_id=${companyId}`
      );
      if (res.data) {
        fetchPolicyAndStatus();
        fetchCounters();
        setSaveSuccessMsg('Recommended baseline policy restored and synced to RouterOS.');
        setTimeout(() => setSaveSuccessMsg(''), 4000);
      }
    } catch (err) {
      console.error('Restore defaults failed', err);
      setErrorMsg('Failed to restore recommended baseline policy.');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-muted-foreground">
        <RefreshCw className="h-8 w-8 animate-spin text-primary mb-3" />
        <p className="text-sm font-medium">Loading Anti-Tethering Policy & Router State…</p>
      </div>
    );
  }

  const currentStatus = routerStatus?.status || 'UNKNOWN';

  const getStatusBadge = () => {
    switch (currentStatus) {
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            <CheckCircle2 className="h-3.5 w-3.5" />
            ACTIVE — FULLY ENFORCED
          </span>
        );
      case 'PARTIALLY_ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-500 border border-amber-500/20">
            <AlertTriangle className="h-3.5 w-3.5" />
            PARTIALLY ACTIVE
          </span>
        );
      case 'OUT_OF_SYNC':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <RefreshCw className="h-3.5 w-3.5" />
            OUT OF SYNC
          </span>
        );
      case 'DISABLED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <Shield className="h-3.5 w-3.5" />
            DISABLED
          </span>
        );
      case 'ROUTER_UNREACHABLE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <AlertTriangle className="h-3.5 w-3.5" />
            ROUTER UNREACHABLE
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-muted text-muted-foreground">
            UNKNOWN
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Notifications */}
      {errorMsg && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs font-medium text-rose-400 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
      {saveSuccessMsg && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-xs font-medium text-emerald-400 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* Hero / Status Card */}
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-foreground">Anti-Tethering & Hotspot Sharing Prevention</h2>
                <p className="text-xs text-muted-foreground">
                  Prevent unauthorized Wi-Fi sharing so each connected device requires its own voucher.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {getStatusBadge()}

            <Button
              variant="outline"
              size="sm"
              onClick={handleSyncToRouter}
              disabled={syncing}
              className="text-xs font-semibold gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin text-primary' : ''}`} />
              <span>{syncing ? 'Syncing…' : 'Sync to Router'}</span>
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowRestoreModal(true)}
              className="text-xs text-muted-foreground hover:text-foreground gap-1.5"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Restore Defaults</span>
            </Button>
          </div>
        </div>

        {/* Master Protection Switch */}
        <div className="pt-4 border-t border-border flex items-center justify-between">
          <div className="space-y-0.5">
            <span className="text-sm font-bold text-foreground">Master Protection Switch</span>
            <p className="text-xs text-muted-foreground">
              When enabled, MikroTik blocks downstream packet forwarding and drops unauthorized client packets.
            </p>
          </div>

          <button
            type="button"
            disabled={savingPolicy}
            onClick={() => {
              if (policy?.enabled) {
                setShowDisableModal(true);
              } else {
                handleUpdatePolicy({ enabled: true });
              }
            }}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              policy?.enabled ? 'bg-primary' : 'bg-muted'
            }`}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                policy?.enabled ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Grid: 2 Column Settings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: IPv4 & Device Policies */}
        <div className="space-y-6">
          {/* Layer 1: Commercial AAA & Device Limits */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-bold text-foreground">
              <Layers className="h-4 w-4 text-primary" />
              <span>Layer 1: Central AAA & Simultaneous Sessions</span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="p-3 rounded-xl bg-muted/40 border border-border/60">
                <span className="text-muted-foreground">Max Devices per Voucher</span>
                <p className="text-base font-bold text-foreground mt-1">1 Device</p>
              </div>
              <div className="p-3 rounded-xl bg-muted/40 border border-border/60">
                <span className="text-muted-foreground">Concurrent Sessions</span>
                <p className="text-base font-bold text-foreground mt-1">1 Session</p>
              </div>
            </div>

            <div className="flex items-start gap-2 p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-300 leading-relaxed">
              <Info className="h-4 w-4 shrink-0 text-blue-400 mt-0.5" />
              <span>
                Device limits are strictly enforced by Internet Plan policies and FreeRADIUS AAA. Second devices entering the same voucher receive <code>DEVICE_LIMIT_REACHED</code>.
              </span>
            </div>
          </div>

          {/* Layer 2: IPv4 Downstream TTL Lock */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-foreground">
                <Zap className="h-4 w-4 text-emerald-500" />
                <span>Layer 2: IPv4 Downstream TTL Lock (set:1)</span>
              </div>

              <button
                type="button"
                disabled={savingPolicy || !policy?.enabled}
                onClick={() => handleUpdatePolicy({ ttl_lock_enabled: !policy?.ttl_lock_enabled })}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                  policy?.ttl_lock_enabled && policy?.enabled ? 'bg-primary' : 'bg-muted'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                    policy?.ttl_lock_enabled && policy?.enabled ? 'translate-x-4' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Forces <code>new-ttl=set:1</code> on outgoing packets to hotspot clients. The primary phone receives data normally. If the phone tries to forward packets to tethered friends, TTL decrements to 0 and the phone drops the packet.
            </p>

            <div className="pt-2 flex items-center justify-between text-xs">
              <span className="font-medium text-foreground">Target TTL Value</span>
              <span className="font-mono px-2.5 py-1 rounded bg-muted font-bold text-foreground border border-border">
                {policy?.ttl_lock_value || 1}
              </span>
            </div>
          </div>

          {/* Layer 3: Forwarded Traffic Detection */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-bold text-foreground">
              <ShieldAlert className="h-4 w-4 text-amber-500" />
              <span>Layer 3: Forwarded Traffic Detection</span>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Drops upstream packets arriving with decremented TTLs originating from secondary clients connected behind a phone bridge.
            </p>

            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between p-3 rounded-xl bg-muted/40 border border-border/60">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <Smartphone className="h-3.5 w-3.5 text-blue-400" />
                    <span>Drop Forwarded TTL 63 (Android / iOS / macOS)</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground">Original TTL 64 drops to 63 after phone hop.</p>
                </div>
                <button
                  type="button"
                  disabled={savingPolicy || !policy?.enabled}
                  onClick={() => handleUpdatePolicy({ detect_ttl_63: !policy?.detect_ttl_63 })}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    policy?.detect_ttl_63 && policy?.enabled ? 'bg-primary' : 'bg-muted'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                      policy?.detect_ttl_63 && policy?.enabled ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-muted/40 border border-border/60">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <Laptop className="h-3.5 w-3.5 text-purple-400" />
                    <span>Drop Forwarded TTL 127 (Windows OS)</span>
                  </div>
                  <p className="text-[11px] text-muted-foreground">Original TTL 128 drops to 127 after laptop hop.</p>
                </div>
                <button
                  type="button"
                  disabled={savingPolicy || !policy?.enabled}
                  onClick={() => handleUpdatePolicy({ detect_ttl_127: !policy?.detect_ttl_127 })}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    policy?.detect_ttl_127 && policy?.enabled ? 'bg-primary' : 'bg-muted'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                      policy?.detect_ttl_127 && policy?.enabled ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Live Counters & Advanced */}
        <div className="space-y-6">
          {/* Live Router Counters */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-foreground">
                <Activity className="h-4 w-4 text-emerald-400" />
                <span>Live RouterOS Firewall Counters</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchCounters}
                disabled={refreshingCounters}
                className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground gap-1"
              >
                <RefreshCw className={`h-3 w-3 ${refreshingCounters ? 'animate-spin text-primary' : ''}`} />
                <span>Refresh</span>
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3.5 rounded-xl bg-muted/40 border border-border/60 space-y-1">
                <span className="text-[11px] text-muted-foreground font-medium">TTL Lock (Mangle)</span>
                <p className="text-base font-bold text-foreground font-mono">
                  {counters?.ttl_lock.packets.toLocaleString() || '0'} <span className="text-xs font-normal text-muted-foreground">pkts</span>
                </p>
                <p className="text-[11px] font-mono text-muted-foreground">
                  {formatBytes(counters?.ttl_lock.bytes)}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-muted/40 border border-border/60 space-y-1">
                <span className="text-[11px] text-muted-foreground font-medium">Total Blocked Traffic</span>
                <p className="text-base font-bold text-rose-500 font-mono">
                  {counters?.total_blocked_packets.toLocaleString() || '0'} <span className="text-xs font-normal text-muted-foreground">drops</span>
                </p>
                <p className="text-[11px] font-mono text-muted-foreground">
                  {formatBytes(counters?.total_blocked_bytes)}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-muted/40 border border-border/60 space-y-1">
                <span className="text-[11px] text-muted-foreground font-medium">TTL 63 Drops (Mobile)</span>
                <p className="text-sm font-bold text-foreground font-mono">
                  {counters?.ttl_63.packets.toLocaleString() || '0'} <span className="text-xs font-normal text-muted-foreground">pkts</span>
                </p>
                <p className="text-[11px] font-mono text-muted-foreground">
                  {formatBytes(counters?.ttl_63.bytes)}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-muted/40 border border-border/60 space-y-1">
                <span className="text-[11px] text-muted-foreground font-medium">TTL 127 Drops (Windows)</span>
                <p className="text-sm font-bold text-foreground font-mono">
                  {counters?.ttl_127.packets.toLocaleString() || '0'} <span className="text-xs font-normal text-muted-foreground">pkts</span>
                </p>
                <p className="text-[11px] font-mono text-muted-foreground">
                  {formatBytes(counters?.ttl_127.bytes)}
                </p>
              </div>
            </div>
          </div>

          {/* Advanced & Protocol Settings */}
          <div className="rounded-2xl border border-border bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-bold text-foreground">
              <Sliders className="h-4 w-4 text-primary" />
              <span>Advanced Protocol & Scope</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border/60">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-1.5 font-semibold text-foreground">
                    <span>Strict Enforcement Mode</span>
                    <span className="text-[10px] uppercase font-bold text-amber-500 bg-amber-500/10 px-1.5 py-0.2 rounded border border-amber-500/20">
                      Experimental
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground">Aggressive packet inspection (leaves default OFF).</p>
                </div>
                <button
                  type="button"
                  disabled={savingPolicy || !policy?.enabled}
                  onClick={() => handleUpdatePolicy({ strict_mode: !policy?.strict_mode })}
                  className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                    policy?.strict_mode ? 'bg-primary' : 'bg-muted'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                      policy?.strict_mode ? 'translate-x-4' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-muted/30 border border-border/60">
                <div className="space-y-0.5">
                  <span className="font-semibold text-foreground">IPv6 Protection Status</span>
                  <p className="text-[11px] text-muted-foreground">Hotspot clients operate strictly over IPv4.</p>
                </div>
                <span className="text-[11px] font-bold text-slate-400 bg-slate-500/10 px-2 py-0.5 rounded border border-slate-500/20">
                  NOT CONFIGURED
                </span>
              </div>
            </div>

            {/* Technical Notice / Limitations */}
            <div className="p-3.5 rounded-xl bg-muted/40 border border-border/60 text-[11px] text-muted-foreground leading-relaxed space-y-1">
              <span className="font-bold text-foreground">Commercial Scope & Limitations:</span>
              <p>
                This feature prevents common phone hotspot-sharing and Wi-Fi bridge tethering using device limits and TTL-based forwarding detection. Encrypted VPN tunnels or custom TTL-rewriting apps may require specialized DPI controls.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal: Disable Anti-Tethering */}
      {showDisableModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full rounded-2xl bg-card border border-border p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-rose-500/10 text-rose-500 flex items-center justify-center shrink-0">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">Disable Anti-Tethering?</h3>
                <p className="text-xs text-muted-foreground">This will remove MikroTik TTL firewall rules.</p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Connected customers with Android devices or laptops will be able to share their Wi-Fi connection via Personal Hotspot with friends.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDisableModal(false)}
                className="text-xs font-semibold"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  setShowDisableModal(false);
                  handleUpdatePolicy({ enabled: false });
                }}
                className="text-xs font-semibold"
              >
                Confirm Disable
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal: Restore Defaults */}
      {showRestoreModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full rounded-2xl bg-card border border-border p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
                <RotateCcw className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">Restore Recommended Baseline?</h3>
                <p className="text-xs text-muted-foreground">Reset all anti-tethering settings to defaults.</p>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              This will re-enable downstream TTL Lock (set:1), TTL 63 detection (Android/iOS), TTL 127 detection (Windows), and synchronize with RouterOS.
            </p>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRestoreModal(false)}
                className="text-xs font-semibold"
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleRestoreDefaults}
                className="text-xs font-semibold"
              >
                Restore & Sync
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
