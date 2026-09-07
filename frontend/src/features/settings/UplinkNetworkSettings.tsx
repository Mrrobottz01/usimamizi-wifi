import React, { useState, useEffect, useCallback } from 'react';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  Plus,
  Trash2,
  CheckCircle2,
  ArrowRightLeft,
  Globe,
  Activity,
  Eye,
  EyeOff,
  Signal,
  Radio,
  Home
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { apiFetch } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';

interface UplinkStatus {
  connected: boolean;
  ssid: string;
  signal_strength: string;
  wan_ip: string;
  gateway: string;
  internet_online: boolean;
  latency_ms: string | null;
  interface_name: string;
  mode: string;
  error?: string | null;
}

interface SavedProfile {
  id: string;
  name: string;
  ssid: string;
  is_active: boolean;
  created_at: string;
  has_password: boolean;
}

interface ScannedNetwork {
  ssid: string;
  signal: string;
  band: string;
  frequency: string;
}

interface UplinkResponse {
  status: UplinkStatus;
  profiles: SavedProfile[];
}

interface UplinkNetworkSettingsProps {
  routerId?: string;
  routerIp?: string;
}

export function UplinkNetworkSettings({ routerId, routerIp }: UplinkNetworkSettingsProps = {}) {
  const { selectedCompany } = useAuth();
  const [status, setStatus] = useState<UplinkStatus | null>(null);
  const [profiles, setProfiles] = useState<SavedProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [switchingId, setSwitchingId] = useState<string | null>(null);
  const [restoringHome, setRestoringHome] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Scanner state
  const [scanning, setScanning] = useState(false);
  const [scannedNetworks, setScannedNetworks] = useState<ScannedNetwork[]>([]);
  const [scanPerformed, setScanPerformed] = useState(false);

  // New Network Form
  const [newLabel, setNewLabel] = useState('');
  const [newSsid, setNewSsid] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [connectingNew, setConnectingNew] = useState(false);

  const fetchStatus = useCallback(async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const params = new URLSearchParams();
      if (selectedCompany?.id) params.set('company_id', selectedCompany.id);
      if (routerId) params.set('router_id', routerId);
      if (routerIp) params.set('router_ip', routerIp);
      const query = params.toString() ? `?${params.toString()}` : '';
      const data = await apiFetch<UplinkResponse>(`/companies/uplink/status/${query}`);
      if (data) {
        setStatus(data.status);
        setProfiles(data.profiles || []);
      }
    } catch (err: any) {
      console.error('Failed to fetch uplink status', err);
    } finally {
      setLoading(false);
      if (isManual) setRefreshing(false);
    }
  }, [selectedCompany?.id, routerId, routerIp]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => {
      fetchStatus();
    }, 12000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleScan = async () => {
    setScanning(true);
    setActionError(null);
    try {
      const params = new URLSearchParams();
      if (selectedCompany?.id) params.set('company_id', selectedCompany.id);
      if (routerId) params.set('router_id', routerId);
      if (routerIp) params.set('router_ip', routerIp);
      const query = params.toString() ? `?${params.toString()}` : '';
      const networks = await apiFetch<ScannedNetwork[]>(`/companies/uplink/scan/${query}`);
      setScannedNetworks(networks || []);
      setScanPerformed(true);
      if (networks && networks.length > 0) {
        setActionSuccess(`Discovered ${networks.length} nearby Wi-Fi network(s).`);
      } else {
        setActionError('No networks detected in scan. Ensure MikroTik radio is in range.');
      }
    } catch (err: any) {
      setActionError(err.detail || 'Failed to scan nearby Wi-Fi networks.');
    } finally {
      setScanning(false);
    }
  };

  const handleSelectScanned = (net: ScannedNetwork) => {
    setNewSsid(net.ssid);
    if (!newLabel || newLabel === newSsid) {
      setNewLabel(net.ssid);
    }
    setActionSuccess(`Selected "${net.ssid}". Enter password below and click Connect.`);
  };

  const handleRestoreHome = async () => {
    setRestoringHome(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await apiFetch<any>('/companies/uplink/restore-home/', {
        method: 'POST',
        body: JSON.stringify({
          company_id: selectedCompany?.id,
          router_id: routerId,
          router_ip: routerIp,
        })
      });
      setActionSuccess('Restored connection to Home Airtel (Avie_5G) successfully!');
      if (res?.status) {
        setStatus(res.status);
      }
      await fetchStatus();
    } catch (err: any) {
      setActionError(err.detail || 'Failed to restore Home Airtel.');
    } finally {
      setRestoringHome(false);
    }
  };

  const handleSwitch = async (profile: SavedProfile) => {
    setSwitchingId(profile.id);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await apiFetch<any>('/companies/uplink/connect/', {
        method: 'POST',
        body: JSON.stringify({
          company_id: selectedCompany?.id,
          profile_id: profile.id,
          router_id: routerId,
          router_ip: routerIp,
        })
      });
      setActionSuccess(`Switched to "${profile.name}" (${profile.ssid}) successfully!`);
      if (res?.status) {
        setStatus(res.status);
      }
      await fetchStatus();
      [2000, 4500, 7500, 11000].forEach(delay => setTimeout(() => fetchStatus(), delay));
    } catch (err: any) {
      setActionError(err.detail || 'Failed to switch network.');
    } finally {
      setSwitchingId(null);
    }
  };

  const handleConnectNew = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSsid.trim()) {
      setActionError('SSID is required.');
      return;
    }

    setConnectingNew(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const res = await apiFetch<any>('/companies/uplink/connect/', {
        method: 'POST',
        body: JSON.stringify({
          company_id: selectedCompany?.id,
          router_id: routerId,
          router_ip: routerIp,
          ssid: newSsid.trim(),
          password: newPassword,
          profile_name: newLabel.trim() || newSsid.trim()
        })
      });
      setActionSuccess(`Successfully connected and saved "${newSsid.trim()}"!`);
      setNewLabel('');
      setNewSsid('');
      setNewPassword('');
      if (res?.status) {
        setStatus(res.status);
      }
      await fetchStatus();
      [2000, 4500, 7500, 11000].forEach(delay => setTimeout(() => fetchStatus(), delay));
    } catch (err: any) {
      setActionError(err.detail || 'Failed to connect to new network.');
    } finally {
      setConnectingNew(false);
    }
  };

  const handleDeleteProfile = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to remove "${name}" from saved networks?`)) return;
    try {
      const params = new URLSearchParams();
      if (selectedCompany?.id) params.set('company_id', selectedCompany.id);
      if (routerId) params.set('router_id', routerId);
      if (routerIp) params.set('router_ip', routerIp);
      const query = params.toString() ? `?${params.toString()}` : '';
      await apiFetch(`/companies/uplink/profiles/${id}/${query}`, {
        method: 'DELETE'
      });
      setProfiles(prev => prev.filter(p => p.id !== id));
      setActionSuccess(`Profile "${name}" removed.`);
    } catch (err: any) {
      setActionError(err.detail || 'Failed to delete profile.');
    }
  };

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Notifications */}
      {actionSuccess && (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-xs text-muted-foreground hover:text-foreground">Dismiss</button>
        </div>
      )}

      {actionError && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <WifiOff className="h-5 w-5 flex-shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-xs text-muted-foreground hover:text-foreground">Dismiss</button>
        </div>
      )}

      {/* Live Uplink Status Card */}
      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Wifi className="h-5 w-5 text-primary" />
              Upstream Wi-Fi WAN (Station Client)
            </CardTitle>
            <CardDescription>
              MikroTik <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">wlan2</code> wireless uplink to your local Internet connection (Home Airtel or Office Vodacom).
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRestoreHome}
              disabled={restoringHome}
              className="flex items-center gap-1.5 text-xs"
              title="Instantly re-connect to Home Airtel 5G using saved hardware profile"
            >
              <Home className={`h-3.5 w-3.5 ${restoringHome ? 'animate-spin' : 'text-primary'}`} />
              Restore Airtel (Home)
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchStatus(true)}
              disabled={refreshing}
              className="flex items-center gap-1.5"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 text-center text-muted-foreground">Checking MikroTik uplink status...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Connected SSID */}
              <div className="p-4 rounded-lg bg-muted/40 border border-border">
                <div className="text-xs text-muted-foreground uppercase font-semibold">Active Wi-Fi</div>
                <div className="mt-1 flex items-center gap-2">
                  {status?.connected ? (
                    <Badge variant="success">
                      Connected
                    </Badge>
                  ) : status?.ssid ? (
                    <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/20 animate-pulse">
                      Connecting…
                    </Badge>
                  ) : (
                    <Badge variant="destructive">Disconnected</Badge>
                  )}
                  <span className="font-bold text-foreground truncate">{status?.ssid || 'None'}</span>
                </div>
              </div>

              {/* Signal Strength */}
              <div className="p-4 rounded-lg bg-muted/40 border border-border">
                <div className="text-xs text-muted-foreground uppercase font-semibold flex items-center gap-1">
                  <Signal className="h-3.5 w-3.5" /> Signal Strength
                </div>
                <div className="mt-1 font-semibold text-foreground">
                  {status?.signal_strength && status.signal_strength !== 'N/A'
                    ? status.signal_strength
                    : 'Searching…'}
                </div>
              </div>

              {/* WAN IP & Gateway */}
              <div className="p-4 rounded-lg bg-muted/40 border border-border">
                <div className="text-xs text-muted-foreground uppercase font-semibold flex items-center gap-1">
                  <Globe className="h-3.5 w-3.5" /> WAN IP / Gateway
                </div>
                <div className="mt-1 font-mono text-xs text-foreground truncate">
                  {status?.wan_ip || 'No Lease'}
                </div>
                <div className="text-[11px] text-muted-foreground font-mono truncate">
                  GW: {status?.gateway || 'None'}
                </div>
              </div>

              {/* Internet Status & Latency */}
              <div className="p-4 rounded-lg bg-muted/40 border border-border">
                <div className="text-xs text-muted-foreground uppercase font-semibold flex items-center gap-1">
                  <Activity className="h-3.5 w-3.5" /> Internet Health
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={`inline-block h-2.5 w-2.5 rounded-full ${
                      status?.internet_online ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-rose-500'
                    }`}
                  />
                  <span className="text-sm font-bold text-foreground">
                    {status?.internet_online ? 'ONLINE' : 'OFFLINE'}
                  </span>
                  {status?.latency_ms && (
                    <span className="text-xs text-muted-foreground font-mono">({status.latency_ms})</span>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available Networks Scanner */}
      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Radio className="h-5 w-5 text-primary" />
              Available Nearby Wi-Fi Networks (Air Scanner)
            </CardTitle>
            <CardDescription>
              Scan for nearby Wi-Fi networks within range of the MikroTik router. Click any detected network to auto-fill the connection form.
            </CardDescription>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={handleScan}
            disabled={scanning}
            className="flex items-center gap-2"
          >
            <Radio className={`h-4 w-4 ${scanning ? 'animate-pulse' : ''}`} />
            {scanning ? 'Scanning Airwaves (4s)...' : 'Scan Nearby Wi-Fi'}
          </Button>
        </CardHeader>
        <CardContent>
          {scanning ? (
            <div className="py-8 flex flex-col items-center justify-center text-center space-y-2">
              <RefreshCw className="h-8 w-8 text-primary animate-spin" />
              <div className="text-sm font-medium text-foreground">Scanning wireless spectrum on MikroTik...</div>
              <p className="text-xs text-muted-foreground">Listening for 5GHz and 2.4GHz broadcast beacons...</p>
            </div>
          ) : scannedNetworks.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {scannedNetworks.map(net => {
                const isSelected = newSsid === net.ssid;
                const isCurrent = status?.ssid === net.ssid;

                return (
                  <div
                    key={net.ssid}
                    onClick={() => handleSelectScanned(net)}
                    className={`p-3.5 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                      isSelected
                        ? 'border-primary bg-primary/10 shadow-sm shadow-primary/20'
                        : isCurrent
                        ? 'border-emerald-500/40 bg-emerald-500/5'
                        : 'border-border bg-muted/20 hover:border-muted-foreground/40 hover:bg-muted/40'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 overflow-hidden">
                      <Wifi className={`h-4 w-4 flex-shrink-0 ${isCurrent ? 'text-emerald-500' : isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                      <div className="truncate">
                        <div className="text-sm font-semibold text-foreground truncate">{net.ssid}</div>
                        <div className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-mono">
                          <span>{net.signal}</span>
                          <span>•</span>
                          <span>{net.band || '5GHz'}</span>
                        </div>
                      </div>
                    </div>
                    {isCurrent ? (
                      <Badge variant="success" className="text-[10px]">Connected</Badge>
                    ) : (
                      <Button size="sm" variant={isSelected ? 'primary' : 'outline'} className="h-7 text-xs px-2">
                        {isSelected ? 'Selected' : 'Select'}
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          ) : scanPerformed ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No networks found. Try scanning again or enter SSID manually below.
            </div>
          ) : (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Click <strong className="text-foreground">"Scan Nearby Wi-Fi"</strong> to detect office or home routers within range.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Saved Networks (1-Click Switch) */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-primary" />
            Saved Locations (1-Click Switch)
          </CardTitle>
          <CardDescription>
            Quickly switch the MikroTik uplink when moving between your Home and Office networks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profiles.map(profile => {
              const isActive = status?.ssid === profile.ssid;
              const isSwitching = switchingId === profile.id;

              return (
                <div
                  key={profile.id}
                  className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${
                    isActive
                      ? 'bg-primary/5 border-primary shadow-sm shadow-primary/10'
                      : 'bg-muted/20 border-border hover:border-muted-foreground/30'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground text-base">{profile.name}</span>
                        {isActive && (
                          <Badge variant="success">ACTIVE</Badge>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground font-mono mt-1">SSID: {profile.ssid}</div>
                    </div>
                    {!isActive && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteProfile(profile.id, profile.name)}
                        className="text-muted-foreground hover:text-destructive h-8 w-8 p-0"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      {isActive ? 'Currently Connected' : 'Saved for 1-Click switch'}
                    </span>
                    <Button
                      size="sm"
                      disabled={isActive || isSwitching}
                      onClick={() => handleSwitch(profile)}
                      variant={isActive ? 'outline' : 'primary'}
                      className="gap-1.5"
                    >
                      {isSwitching ? (
                        <>
                          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          Switching...
                        </>
                      ) : isActive ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                          In Use
                        </>
                      ) : (
                        <>
                          <ArrowRightLeft className="h-3.5 w-3.5" />
                          Connect
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Add / Connect New Network */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" />
            Connect to a Wi-Fi Network
          </CardTitle>
          <CardDescription>
            Select a scanned network above or enter the SSID and password for a new Wi-Fi network (e.g. Office Vodacom).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleConnectNew} className="space-y-4 max-w-xl">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-foreground mb-1">Location Label</label>
                <Input
                  placeholder="e.g. Office Vodacom Wi-Fi"
                  value={newLabel}
                  onChange={e => setNewLabel(e.target.value)}
                  className="bg-background"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-foreground mb-1">Wi-Fi Network Name (SSID) *</label>
                <Input
                  placeholder="e.g. Vodacom_Office_5G"
                  value={newSsid}
                  onChange={e => setNewSsid(e.target.value)}
                  required
                  className="bg-background"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Wi-Fi Password (WPA2-PSK)</label>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter Wi-Fi password (leave blank for open networks)"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  className="bg-background pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button type="submit" variant="primary" disabled={connectingNew || !newSsid.trim()} className="gap-2">
              {connectingNew ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Connecting to {newSsid}...
                </>
              ) : (
                <>
                  <Wifi className="h-4 w-4" />
                  Connect & Save Profile
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
