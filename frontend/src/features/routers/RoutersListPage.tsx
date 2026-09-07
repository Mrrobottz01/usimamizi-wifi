import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Router as RouterIcon,
  Search,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  MapPin,
  Radio,
  ChevronRight,
  Zap,
  BookOpen,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { routersApi, locationsApi } from '../../lib/infrastructure-api';
import {
  RouterSummary,
  RouterHealthStatus,
  LocationSummary,
} from '../../types';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '../../components/ui/dialog';

export function RouterHealthBadge({
  status,
  message,
}: {
  status: RouterHealthStatus;
  message?: string;
}) {
  switch (status) {
    case 'ONLINE':
      return (
        <Badge variant="success" className="flex items-center gap-1 font-medium text-xs">
          <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          <span>Online</span>
        </Badge>
      );
    case 'DEGRADED':
      return (
        <Badge variant="warning" className="flex items-center gap-1 font-medium text-xs" title={message}>
          <AlertTriangle className="h-3 w-3 text-amber-600 dark:text-amber-400" />
          <span>Degraded</span>
        </Badge>
      );
    case 'UNREACHABLE':
      return (
        <Badge variant="destructive" className="flex items-center gap-1 font-medium text-xs" title={message}>
          <XCircle className="h-3 w-3 text-rose-600 dark:text-rose-400" />
          <span>Unreachable</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="flex items-center gap-1 text-muted-foreground text-xs">
          <HelpCircle className="h-3 w-3" />
          <span>Unknown</span>
        </Badge>
      );
  }
}

export const RoutersListPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.id;
  const navigate = useNavigate();
  const { toast } = useToast();

  const [routers, setRouters] = useState<RouterSummary[]>([]);
  const [locations, setLocations] = useState<LocationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [locationFilter, setLocationFilter] = useState('ALL');
  const [healthFilter, setHealthFilter] = useState('ALL');

  // Register Modal State
  const [registerOpen, setRegisterOpen] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [testResult, setTestResult] = useState<{
    tested: boolean;
    loading: boolean;
    success?: boolean;
    latency_ms?: number | null;
    version?: string | null;
    error?: string | null;
  }>({ tested: false, loading: false });

  const [newRouterId, setNewRouterId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    location_id: '',
    management_ip: '10.5.50.1',
    api_port: 8728,
    use_tls: false,
    username: 'admin',
    password: '',
    uplink_interface: 'ether1',
    identity: '',
    model: '',
    serial_number: '',
  });

  const fetchData = useCallback(async () => {
    if (!companyId) return;
    try {
      setLoading(true);
      const [routersData, locationsData] = await Promise.all([
        routersApi.list({
          company_id: companyId,
          q: searchQuery.trim() || undefined,
          location_id: locationFilter !== 'ALL' ? locationFilter : undefined,
          health_status: healthFilter !== 'ALL' ? healthFilter : undefined,
        }),
        locationsApi.list({ company_id: companyId }),
      ]);
      setRouters(routersData);
      setLocations(locationsData);
    } catch (err: any) {
      toast({ title: 'Failed to load routers', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [companyId, searchQuery, locationFilter, healthFilter, toast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    const totalRouters = routers.length;
    const online = routers.filter((r) => r.health_status === 'ONLINE').length;
    const degraded = routers.filter((r) => r.health_status === 'DEGRADED').length;
    const unreachable = routers.filter((r) => r.health_status === 'UNREACHABLE').length;
    return { totalRouters, online, degraded, unreachable };
  }, [routers]);

  const handleOpenRegister = () => {
    setNewRouterId(null);
    setTestResult({ tested: false, loading: false });
    setFormData({
      name: '',
      location_id: locations.length > 0 ? locations[0].id : '',
      management_ip: '10.5.50.1',
      api_port: 8728,
      use_tls: false,
      username: 'admin',
      password: '',
      uplink_interface: 'ether1',
      identity: '',
      model: '',
      serial_number: '',
    });
    setRegisterOpen(true);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyId || !formData.name.trim() || !formData.management_ip.trim()) return;

    try {
      setRegistering(true);
      const res = await routersApi.create({
        company_id: companyId,
        name: formData.name.trim(),
        location_id: formData.location_id || null,
        management_ip: formData.management_ip.trim(),
        api_port: Number(formData.api_port),
        use_tls: formData.use_tls,
        username: formData.username.trim(),
        password: formData.password,
        uplink_interface: formData.uplink_interface.trim() || 'ether1',
        identity: formData.identity.trim(),
        model: formData.model.trim(),
        serial_number: formData.serial_number.trim(),
      });
      toast({ title: `Router '${res.name}' registered successfully`, type: 'success' });
      setNewRouterId(res.id);
      fetchData();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to register router', type: 'error' });
    } finally {
      setRegistering(false);
    }
  };

  const handleTestNewRouter = async () => {
    if (!newRouterId || !companyId) return;
    try {
      setTestResult({ tested: true, loading: true });
      const res = await routersApi.testConnection(newRouterId, companyId);
      setTestResult({
        tested: true,
        loading: false,
        success: res.success,
        latency_ms: res.latency_ms,
        version: res.version,
        error: res.error,
      });
      if (res.success) {
        toast({ title: 'Router connection verified!', type: 'success' });
      } else {
        toast({ title: res.error || 'Connection failed', type: 'error' });
      }
    } catch (err: any) {
      setTestResult({
        tested: true,
        loading: false,
        success: false,
        error: 'Connection timeout or socket error',
      });
    }
  };

  const handleQuickRefreshHealth = async (routerId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      toast({ title: 'Refreshing router health...', type: 'info' });
      const res = await routersApi.refreshHealth(routerId, companyId);
      toast({
        title: `Health status: ${res.health_status}`,
        type: res.health_status === 'ONLINE' ? 'success' : 'error',
      });
      fetchData();
    } catch (err: any) {
      toast({ title: 'Health refresh failed', type: 'error' });
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <RouterIcon className="h-6 w-6 text-primary" />
            Routers
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Monitor and manage MikroTik hardware gateways across your physical locations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link to="/settings?tab=router-guide">
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs text-indigo-600 dark:text-indigo-400 border-indigo-200 dark:border-indigo-800/80 hover:bg-indigo-50 dark:hover:bg-indigo-950/50"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Router Setup & ISP Guide</span>
            </Button>
          </Link>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
          <Button onClick={handleOpenRegister} size="sm" className="gap-1.5 text-xs">
            <Plus className="h-4 w-4" />
            <span>Register Router</span>
          </Button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Routers</p>
              <p className="text-2xl font-bold text-foreground mt-1">{metrics.totalRouters}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <RouterIcon className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Online</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{metrics.online}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Degraded</p>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{metrics.degraded}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Unreachable</p>
              <p className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">{metrics.unreachable}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-600 dark:text-rose-400">
              <XCircle className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 bg-card p-3 rounded-xl border border-border">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search name, identity, management IP, serial..."
            className="pl-9 h-9 text-sm"
          />
        </div>

        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
          <select
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
            className="h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="ALL">All Locations</option>
            {locations.map((loc) => (
              <option key={loc.id} value={loc.id}>{loc.name}</option>
            ))}
          </select>

          <select
            value={healthFilter}
            onChange={(e) => setHealthFilter(e.target.value)}
            className="h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="ALL">All Health States</option>
            <option value="ONLINE">Online</option>
            <option value="DEGRADED">Degraded</option>
            <option value="UNREACHABLE">Unreachable</option>
            <option value="UNKNOWN">Unknown</option>
          </select>
        </div>
      </div>

      {/* Router Desktop Table / Mobile Cards */}
      {loading ? (
        <div className="py-20 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-2">
          <RefreshCw className="h-6 w-6 animate-spin text-primary" />
          <p>Loading gateway fleet...</p>
        </div>
      ) : routers.length === 0 ? (
        <div className="py-16 text-center rounded-2xl border border-dashed border-border bg-card/50 p-8">
          <RouterIcon className="h-10 w-10 text-muted-foreground mx-auto mb-3 opacity-40" />
          <h3 className="text-base font-semibold text-foreground">No routers registered</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1 mb-4">
            {searchQuery || locationFilter !== 'ALL' || healthFilter !== 'ALL'
              ? 'No routers match your active filter criteria.'
              : 'Register your first MikroTik hardware gateway to begin centralized policy enforcement.'}
          </p>
          <Button onClick={handleOpenRegister} size="sm" className="gap-1.5 text-xs">
            <Plus className="h-4 w-4" />
            <span>Register Router</span>
          </Button>
        </div>
      ) : (
        <>
          {/* Desktop Table */}
          <div className="hidden md:block border border-border rounded-xl overflow-hidden bg-card shadow-sm">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
                <tr>
                  <th className="p-3.5">Router Gateway</th>
                  <th className="p-3.5">Deployment Site</th>
                  <th className="p-3.5">Management IP</th>
                  <th className="p-3.5">Health</th>
                  <th className="p-3.5">Hotspots</th>
                  <th className="p-3.5">Last Seen</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {routers.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => navigate(`/routers/${r.id}`)}
                    className="hover:bg-muted/30 cursor-pointer transition-colors"
                  >
                    <td className="p-3.5 font-semibold text-foreground">
                      <div className="font-bold hover:text-primary transition-colors">{r.name}</div>
                      <div className="text-[11px] font-normal text-muted-foreground flex items-center gap-1.5 mt-0.5">
                        <span>{r.identity || 'MikroTik'}</span>
                        {r.model && <span>• {r.model}</span>}
                      </div>
                    </td>

                    <td className="p-3.5 text-muted-foreground">
                      {r.location ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/locations/${r.location?.id}`);
                          }}
                          className="hover:text-primary transition-colors flex items-center gap-1 font-medium text-foreground text-left"
                        >
                          <MapPin className="h-3 w-3 text-muted-foreground shrink-0" />
                          <span>{r.location.name}</span>
                        </button>
                      ) : (
                        <span className="text-muted-foreground italic">Unassigned</span>
                      )}
                    </td>

                    <td className="p-3.5 font-mono">
                      <div className="flex items-center gap-1.5">
                        <span>{r.management_ip}:{r.api_port}</span>
                        {r.use_tls ? (
                          <Badge variant="outline" className="text-[10px] py-0 px-1 font-mono">SSL</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-[10px] py-0 px-1 font-mono">API</Badge>
                        )}
                      </div>
                      <div className="text-[10px] font-sans text-muted-foreground mt-0.5">
                        {r.has_credentials ? 'Credentials set' : 'No credentials'}
                      </div>
                    </td>

                    <td className="p-3.5">
                      <RouterHealthBadge status={r.health_status} message={r.health_message} />
                    </td>

                    <td className="p-3.5 font-bold text-foreground">
                      <div className="flex items-center gap-1">
                        <Radio className="h-3.5 w-3.5 text-primary" />
                        <span>{r.hotspots_count}</span>
                      </div>
                    </td>

                    <td className="p-3.5 text-muted-foreground text-[11px]">
                      {r.last_seen_at ? new Date(r.last_seen_at).toLocaleTimeString() : 'Never'}
                    </td>

                    <td className="p-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => handleQuickRefreshHealth(r.id, e)}
                          title="Refresh cached health"
                          className="h-7 px-2 text-xs"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/routers/${r.id}`)}
                          className="h-7 px-2.5 text-xs font-semibold"
                        >
                          Manage
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards */}
          <div className="md:hidden space-y-3">
            {routers.map((r) => (
              <div
                key={r.id}
                onClick={() => navigate(`/routers/${r.id}`)}
                className="p-4 rounded-xl border border-border bg-card space-y-3 cursor-pointer hover:border-primary/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-foreground text-sm">{r.name}</h3>
                    <p className="text-xs text-muted-foreground">{r.identity || 'MikroTik'} {r.model && `• ${r.model}`}</p>
                  </div>
                  <RouterHealthBadge status={r.health_status} message={r.health_message} />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border/60">
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Location</span>
                    <span className="font-medium text-foreground line-clamp-1">{r.location?.name || 'Unassigned'}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Management IP</span>
                    <span className="font-mono text-foreground">{r.management_ip}:{r.api_port}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-border/60 text-xs">
                  <span className="text-muted-foreground text-[11px]">
                    Hotspots: <strong className="text-foreground">{r.hotspots_count}</strong>
                  </span>
                  <span className="text-primary font-semibold flex items-center gap-1">
                    <span>Manage</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Register Router Modal */}
      <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RouterIcon className="h-5 w-5 text-primary" />
              <span>Register MikroTik Gateway</span>
            </DialogTitle>
          </DialogHeader>

          {newRouterId ? (
            <div className="space-y-4 py-3">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-center space-y-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-600 dark:text-emerald-400 mx-auto" />
                <h3 className="text-sm font-bold text-foreground">Router Registered Successfully</h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Router credentials have been securely encrypted. Would you like to test API connectivity right now?
                </p>
              </div>

              {testResult.tested && (
                <div
                  className={`p-3 rounded-lg border text-xs ${
                    testResult.success
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-300'
                      : 'bg-rose-500/10 border-rose-500/30 text-rose-800 dark:text-rose-300'
                  }`}
                >
                  <p className="font-bold flex items-center gap-1.5 mb-1">
                    {testResult.success ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                    <span>{testResult.success ? 'Connection Healthy' : 'Connection Failed'}</span>
                  </p>
                  {testResult.success ? (
                    <div className="space-y-0.5 pl-5">
                      <p>Latency: {testResult.latency_ms} ms</p>
                      {testResult.version && <p>Firmware: {testResult.version}</p>}
                    </div>
                  ) : (
                    <p className="pl-5">{testResult.error || 'Connection timed out or unreachable.'}</p>
                  )}
                </div>
              )}

              <DialogFooter className="gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={handleTestNewRouter}
                  disabled={testResult.loading}
                  className="text-xs h-9 gap-1.5"
                >
                  <Zap className={`h-3.5 w-3.5 ${testResult.loading ? 'animate-spin' : ''}`} />
                  <span>{testResult.loading ? 'Testing...' : 'Test Connection'}</span>
                </Button>
                <Button
                  onClick={() => {
                    setRegisterOpen(false);
                    navigate(`/routers/${newRouterId}`);
                  }}
                  className="text-xs h-9"
                >
                  Open Router Dashboard
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <form onSubmit={handleRegister} className="space-y-4 pt-2" autoComplete="off">
              {/* Decoy fields to capture browser password manager autofill */}
              <div style={{ display: 'none', opacity: 0, position: 'absolute', left: '-9999px' }} aria-hidden="true">
                <input type="text" name="decoy_router_reg_username" tabIndex={-1} autoComplete="off" />
                <input type="password" name="decoy_router_reg_password" tabIndex={-1} autoComplete="new-password" />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Router Name *</label>
                  <Input
                    name="router_name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. MikroTik Main Gateway"
                    required
                    autoComplete="off"
                    data-lpignore="true"
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Physical Location *</label>
                  <select
                    value={formData.location_id}
                    onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
                    className="w-full h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="">Unassigned Location</option>
                    {locations.map((loc) => (
                      <option key={loc.id} value={loc.id}>{loc.name} ({loc.code})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Management IP *</label>
                  <Input
                    value={formData.management_ip}
                    onChange={(e) => setFormData({ ...formData, management_ip: e.target.value })}
                    placeholder="10.5.50.1"
                    required
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">RouterOS API Port *</label>
                  <Input
                    type="number"
                    value={formData.api_port}
                    onChange={(e) => setFormData({ ...formData, api_port: Number(e.target.value) })}
                    placeholder="8728"
                    required
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">API Username *</label>
                  <Input
                    name="routeros_api_username"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    placeholder="admin"
                    required
                    autoComplete="off"
                    data-lpignore="true"
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">API Password *</label>
                  <Input
                    name="routeros_api_password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="••••••••"
                    required
                    autoComplete="new-password"
                    data-lpignore="true"
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Uplink WAN Interface</label>
                  <Input
                    value={formData.uplink_interface}
                    onChange={(e) => setFormData({ ...formData, uplink_interface: e.target.value })}
                    placeholder="ether1 or wlan1"
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div className="flex items-center space-x-2 pt-6">
                  <input
                    type="checkbox"
                    id="use_tls_checkbox"
                    checked={formData.use_tls}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        use_tls: e.target.checked,
                        api_port: e.target.checked && formData.api_port === 8728 ? 8729 : formData.api_port,
                      })
                    }
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <label htmlFor="use_tls_checkbox" className="text-xs font-medium text-foreground cursor-pointer">
                    Use TLS (Port 8729 API-SSL)
                  </label>
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Router Identity (Optional)</label>
                  <Input
                    value={formData.identity}
                    onChange={(e) => setFormData({ ...formData, identity: e.target.value })}
                    placeholder="e.g. MikroTik-Lab"
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Model (Optional)</label>
                  <Input
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    placeholder="e.g. hAP ac3, RB4011"
                    className="text-xs h-9"
                  />
                </div>
              </div>

              <DialogFooter className="gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setRegisterOpen(false)}
                  disabled={registering}
                  className="text-xs h-9"
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={registering} className="text-xs h-9">
                  {registering ? <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                  <span>Register Router</span>
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};