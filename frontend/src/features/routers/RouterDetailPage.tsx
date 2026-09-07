import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Server,
  ArrowLeft,
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Cpu,
  HardDrive,
  Radio,
  Wifi,
  Shield,
  Key,
  RefreshCw,
  ExternalLink,
  MapPin,
  Lock,
  Globe,
  Settings,
  AlertCircle,
  HelpCircle,
  Zap,
  Copy,
  Check,
  Download,
  FileCode2,
  Sliders,
  Sparkles
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { routersApi } from '../../lib/infrastructure-api';
import { RouterDetail, RouterTestConnectionResult, RouterProvisionResult, RouterBootstrapScript } from '../../types';
import { UplinkNetworkSettings } from '../settings/UplinkNetworkSettings';

export const RouterDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [router, setRouter] = useState<RouterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'interfaces' | 'hotspots' | 'radius' | 'security' | 'provisioning'>('overview');

  // Provisioning state
  const [provisioning, setProvisioning] = useState(false);
  const [provisionResult, setProvisionResult] = useState<RouterProvisionResult | null>(null);
  const [provisionError, setProvisionError] = useState<string | null>(null);
  const [bootstrapScript, setBootstrapScript] = useState<RouterBootstrapScript | null>(null);
  const [loadingScript, setLoadingScript] = useState(false);
  const [copiedCommand, setCopiedCommand] = useState(false);
  const [copiedScript, setCopiedScript] = useState(false);
  const [showScriptDetails, setShowScriptDetails] = useState(false);

  // Module options
  const [provRadius, setProvRadius] = useState(true);
  const [provHotspot, setProvHotspot] = useState(true);
  const [provWalledGarden, setProvWalledGarden] = useState(true);
  const [provAntiTethering, setProvAntiTethering] = useState(true);

  const fetchBootstrapScript = useCallback(async () => {
    if (!id) return;
    try {
      setLoadingScript(true);
      const res = await routersApi.getBootstrapScript(id, {
        anti_tethering: provAntiTethering,
        radius: provRadius,
        hotspot: provHotspot,
        walled_garden: provWalledGarden,
      });
      setBootstrapScript(res);
    } catch (err: any) {
      console.error('Failed fetching bootstrap script:', err);
    } finally {
      setLoadingScript(false);
    }
  }, [id, provAntiTethering, provRadius, provHotspot, provWalledGarden]);

  useEffect(() => {
    if (activeTab === 'provisioning') {
      fetchBootstrapScript();
    }
  }, [activeTab, fetchBootstrapScript]);

  const handleRunProvisioning = async () => {
    if (!router) return;
    try {
      setProvisioning(true);
      setProvisionError(null);
      setProvisionResult(null);
      const res = await routersApi.provision(router.id, {
        enable_anti_tethering: provAntiTethering,
        enable_radius: provRadius,
        enable_hotspot: provHotspot,
        enable_walled_garden: provWalledGarden,
      });
      setProvisionResult(res.result);
      if (res.result.success) {
        fetchRouter();
      }
    } catch (err: any) {
      setProvisionError(err.message || 'Provisioning execution failed.');
    } finally {
      setProvisioning(false);
    }
  };

  const handleCopyText = (textToCopy: string, isCommand: boolean) => {
    navigator.clipboard.writeText(textToCopy);
    if (isCommand) {
      setCopiedCommand(true);
      setTimeout(() => setCopiedCommand(false), 2000);
    } else {
      setCopiedScript(true);
      setTimeout(() => setCopiedScript(false), 2000);
    }
  };

  // Actions state
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<RouterTestConnectionResult | null>(null);
  const [refreshingHealth, setRefreshingHealth] = useState(false);

  // Credentials modal
  const [showCredModal, setShowCredModal] = useState(false);
  const [credUsername, setCredUsername] = useState('');
  const [credPassword, setCredPassword] = useState('');
  const [credPort, setCredPort] = useState(8728);
  const [credUseTls, setCredUseTls] = useState(false);
  const [credSaving, setCredSaving] = useState(false);
  const [credError, setCredError] = useState<string | null>(null);

  const fetchRouter = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await routersApi.get(id);
      setRouter(data);
      setCredUsername(data.api_username || '');
      setCredPort(data.api_port || 8728);
      setCredUseTls(Boolean(data.use_tls));
    } catch (err: any) {
      setError(err.message || 'Failed to load router details.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRouter();
  }, [fetchRouter]);

  const handleTestConnection = async () => {
    if (!router) return;
    try {
      setTestingConnection(true);
      setTestResult(null);
      const res = await routersApi.testConnection(router.id);
      setTestResult(res);
      if (res.success) {
        fetchRouter();
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        detail: err.message || 'Connection test failed',
        authenticated: false,
        latency_ms: null,
        identity: null,
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleRefreshHealth = async () => {
    if (!router) return;
    try {
      setRefreshingHealth(true);
      await routersApi.refreshHealth(router.id);
      await fetchRouter();
    } catch (err: any) {
      console.error('Failed to refresh health', err);
    } finally {
      setRefreshingHealth(false);
    }
  };

  const handleSaveCredentials = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!router) return;
    try {
      setCredSaving(true);
      setCredError(null);
      await routersApi.updateCredentials(router.id, {
        api_username: credUsername,
        api_password: credPassword || undefined,
        api_port: credPort,
        use_tls: credUseTls,
      });
      setShowCredModal(false);
      setCredPassword('');
      await fetchRouter();
    } catch (err: any) {
      setCredError(err.message || 'Failed to update credentials');
    } finally {
      setCredSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-gray-500">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Loading router details...</p>
      </div>
    );
  }

  if (error || !router) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 rounded-xl p-6 text-center">
          <AlertCircle className="w-10 h-10 text-red-600 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Router Not Found</h2>
          <p className="text-sm text-red-700 dark:text-red-400 mb-4">{error || 'The requested router could not be found or has been removed.'}</p>
          <Button onClick={() => navigate('/routers')} variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Routers Fleet
          </Button>
        </div>
      </div>
    );
  }

  const renderHealthBadge = (health: string) => {
    switch (health?.toUpperCase()) {
      case 'ONLINE':
      case 'HEALTHY':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 dark:bg-green-950/60 dark:text-green-300 border border-green-200 dark:border-green-800/50">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-600 dark:text-green-400" /> Online
          </span>
        );
      case 'DEGRADED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border border-amber-200 dark:border-amber-800/50">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" /> Degraded
          </span>
        );
      case 'UNREACHABLE':
      case 'OFFLINE':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border border-red-200 dark:border-red-800/50">
            <XCircle className="w-3.5 h-3.5 text-red-600 dark:text-red-400" /> Unreachable
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
            <HelpCircle className="w-3.5 h-3.5 text-gray-500" /> Unknown
          </span>
        );
    }
  };

  const sys = (router.system_resources as Record<string, any>) || (router.cached_system_info as Record<string, any>) || {};
  const cpuLoad = sys.cpu_load !== undefined && sys.cpu_load !== null ? Number(sys.cpu_load) : null;
  const freeMem = sys.free_memory_bytes !== undefined ? Number(sys.free_memory_bytes) : (sys.free_memory !== undefined ? Number(sys.free_memory) : null);
  const totalMem = sys.total_memory_bytes !== undefined ? Number(sys.total_memory_bytes) : (sys.total_memory !== undefined ? Number(sys.total_memory) : null);
  const memUsagePercent = freeMem && totalMem ? Math.round(((totalMem - freeMem) / totalMem) * 100) : null;
  const uptimeStr = (sys.uptime as string) || (sys.details?.uptime as string) || null;
  const archStr = router.architecture || (sys.architecture as string) || (sys.details?.['architecture-name'] as string) || router.model || 'MikroTik RouterBOARD';

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/routers')}
            className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <div className="h-4 w-px bg-gray-300 dark:bg-gray-700" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                {router.name}
              </h1>
              {renderHealthBadge(router.health_status)}
              {router.use_tls && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300">
                  <Lock className="w-3 h-3" /> API-SSL
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-blue-500" />
                Location:
                {router.location ? (
                  <Link
                    to={`/locations/${router.location.id}`}
                    className="font-medium text-blue-600 dark:text-blue-400 hover:underline ml-1"
                  >
                    {router.location.name}
                  </Link>
                ) : (
                  <span className="text-gray-400 ml-1">Unassigned</span>
                )}
              </span>
              <span>•</span>
              <span className="font-mono font-medium text-gray-700 dark:text-gray-300">
                {router.management_ip}:{router.api_port}
              </span>
              {router.routeros_version && (
                <>
                  <span>•</span>
                  <span>RouterOS v{router.routeros_version}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleTestConnection}
            disabled={testingConnection}
            className="h-9"
          >
            <Activity className={`w-4 h-4 mr-1.5 ${testingConnection ? 'animate-spin text-blue-600' : 'text-blue-500'}`} />
            {testingConnection ? 'Testing...' : 'Test Connection'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefreshHealth}
            disabled={refreshingHealth}
            className="h-9"
          >
            <RefreshCw className={`w-4 h-4 mr-1.5 ${refreshingHealth ? 'animate-spin text-gray-600' : 'text-gray-500'}`} />
            {refreshingHealth ? 'Refreshing...' : 'Refresh Health'}
          </Button>
          <Button
            size="sm"
            onClick={() => setActiveTab('provisioning')}
            className={`h-9 font-medium shadow-sm transition-all ${
              activeTab === 'provisioning'
                ? 'bg-indigo-700 text-white'
                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white'
            }`}
          >
            <Zap className="w-4 h-4 mr-1.5 text-amber-300" />
            Provision & Scripts
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowCredModal(true)}
            className="h-9"
          >
            <Key className="w-4 h-4 mr-1.5 text-amber-500" />
            Update Credentials
          </Button>
        </div>
      </div>

      {/* Test Connection Banner */}
      {testResult && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
            testResult.success
              ? 'bg-green-50 dark:bg-green-950/40 border-green-200 dark:border-green-800/60 text-green-900 dark:text-green-200'
              : 'bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800/60 text-red-900 dark:text-red-200'
          }`}
        >
          {testResult.success ? (
            <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
          )}
          <div className="flex-1 text-sm">
            <div className="font-bold flex items-center gap-2">
              <span>{testResult.success ? 'Connectivity Verified Successfully' : 'Connection Failed'}</span>
              {testResult.latency_ms && (
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-white/60 dark:bg-black/40 border border-green-300 dark:border-green-800">
                  {testResult.latency_ms} ms
                </span>
              )}
            </div>
            <p className="text-xs mt-1 text-gray-700 dark:text-gray-300">
              {testResult.detail || (testResult.success ? 'Router responded to API probe with valid credentials.' : 'Unable to reach or authenticate with RouterOS API.')}
            </p>
            {testResult.identity && (
              <div className="mt-2 text-xs flex gap-4 font-mono">
                <span>Identity: <strong>{testResult.identity}</strong></span>
                {testResult.version && <span>Version: <strong>{testResult.version}</strong></span>}
                {testResult.board_name && <span>Model: <strong>{testResult.board_name}</strong></span>}
              </div>
            )}
          </div>
          <button
            onClick={() => setTestResult(null)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-sm p-1"
          >
            ×
          </button>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="border-b border-gray-200 dark:border-gray-800">
        <nav className="flex space-x-6 overflow-x-auto" aria-label="Tabs">
          {[
            { id: 'overview', label: 'Overview & Telemetry', icon: Server },
            { id: 'interfaces', label: 'Interfaces & WAN', icon: Globe },
            { id: 'hotspots', label: `Hosted Hotspots (${router.hotspots?.length || 0})`, icon: Wifi },
            { id: 'radius', label: 'RADIUS AAA Client', icon: Shield },
            { id: 'security', label: 'Security & Access', icon: Lock },
            { id: 'provisioning', label: 'Provisioning & Bootstrap', icon: Zap },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 px-1 border-b-2 font-medium text-sm inline-flex items-center gap-2 whitespace-nowrap transition-colors ${
                  active
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'}`} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* TAB CONTENTS */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Telemetry Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* CPU Load */}
            <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span className="font-medium">CPU LOAD</span>
                <Cpu className="w-4 h-4 text-blue-500" />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {cpuLoad !== null ? `${cpuLoad}%` : 'N/A'}
              </div>
              {cpuLoad !== null && (
                <div className="w-full bg-gray-100 dark:bg-gray-800 h-2 rounded-full overflow-hidden mt-3">
                  <div
                    className={`h-full transition-all ${
                      cpuLoad > 85 ? 'bg-red-500' : cpuLoad > 60 ? 'bg-amber-500' : 'bg-blue-600'
                    }`}
                    style={{ width: `${Math.min(cpuLoad, 100)}%` }}
                  />
                </div>
              )}
            </div>

            {/* RAM Usage */}
            <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span className="font-medium">MEMORY USAGE</span>
                <HardDrive className="w-4 h-4 text-purple-500" />
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {memUsagePercent !== null ? `${memUsagePercent}%` : 'N/A'}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {freeMem && totalMem
                  ? `${Math.round(freeMem / 1024 / 1024)} MB free of ${Math.round(totalMem / 1024 / 1024)} MB`
                  : 'Telemetry not yet captured'}
              </p>
            </div>

            {/* Uptime */}
            <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span className="font-medium">UPTIME</span>
                <Clock className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="text-xl font-bold text-gray-900 dark:text-white truncate">
                {uptimeStr || 'N/A'}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Last seen: {router.last_seen_at ? new Date(router.last_seen_at).toLocaleTimeString() : 'Never'}
              </p>
            </div>

            {/* RouterOS Version */}
            <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                <span className="font-medium">ROUTEROS FIRMWARE</span>
                <Server className="w-4 h-4 text-orange-500" />
              </div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                {router.routeros_version ? `v${router.routeros_version}` : 'Unknown'}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Arch: {archStr}
              </p>
            </div>
          </div>

          {/* Details 2-Column Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Identity & Hardware Card */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
                <Server className="w-4 h-4 text-blue-600" /> Hardware & System Identity
              </h3>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-y-3 gap-x-4 text-sm">
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Device Name</dt>
                  <dd className="font-medium text-gray-900 dark:text-white mt-0.5">{router.name}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">RouterOS Identity</dt>
                  <dd className="font-mono font-medium text-gray-900 dark:text-white mt-0.5">{router.identity || 'MikroTik'}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Model / Board</dt>
                  <dd className="text-gray-900 dark:text-white mt-0.5">{router.model || (sys.board_name as string) || 'Standard Gateway'}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Serial Number</dt>
                  <dd className="font-mono text-gray-900 dark:text-white mt-0.5">{router.serial_number || 'N/A'}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Operating Site</dt>
                  <dd className="mt-0.5">
                    {router.location ? (
                      <Link
                        to={`/locations/${router.location.id}`}
                        className="text-blue-600 dark:text-blue-400 font-medium hover:underline inline-flex items-center gap-1"
                      >
                        {router.location.name} <ExternalLink className="w-3 h-3" />
                      </Link>
                    ) : (
                      <span className="text-gray-400">Unassigned</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Site Code</dt>
                  <dd className="font-mono text-gray-700 dark:text-gray-300 mt-0.5">{router.location?.code || 'N/A'}</dd>
                </div>
              </dl>
            </div>

            {/* Management & API Card */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
                <Settings className="w-4 h-4 text-purple-600" /> Management & API Configuration
              </h3>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-y-3 gap-x-4 text-sm">
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Management IP</dt>
                  <dd className="font-mono font-medium text-gray-900 dark:text-white mt-0.5">{router.management_ip}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">API Port</dt>
                  <dd className="font-mono text-gray-900 dark:text-white mt-0.5">
                    {router.api_port} ({router.use_tls ? 'TLS Enabled' : 'Plaintext API'})
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">API Username</dt>
                  <dd className="font-mono text-gray-900 dark:text-white mt-0.5">{router.api_username}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">API Password</dt>
                  <dd className="font-mono text-gray-400 mt-0.5">•••••••••••• (Encrypted)</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Uplink Interface</dt>
                  <dd className="font-mono text-gray-900 dark:text-white mt-0.5">{router.uplink_interface}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Fallback Management IP</dt>
                  <dd className="font-mono text-gray-700 dark:text-gray-300 mt-0.5">{router.fallback_management_ip || 'None configured'}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}

      {/* TAB: INTERFACES & WAN */}
      {activeTab === 'interfaces' && (
        <div className="space-y-6">
          <div className="bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/40 rounded-xl p-4 text-xs text-blue-800 dark:text-blue-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-blue-600 shrink-0" />
              <span>
                Managing WAN interfaces and failover uplink network profiles for router <strong>{router.name}</strong> ({router.management_ip}).
              </span>
            </div>
          </div>
          <UplinkNetworkSettings routerId={router.id} routerIp={router.management_ip} />
        </div>
      )}

      {/* TAB: HOSTED HOTSPOTS */}
      {activeTab === 'hotspots' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-gray-900 dark:text-white">
              Captive HotSpots Hosted on this Gateway
            </h3>
            <Button
              size="sm"
              onClick={() => navigate('/hotspots')}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Wifi className="w-4 h-4 mr-1.5" /> Open Hotspots Directory
            </Button>
          </div>

          {(!router.hotspots || router.hotspots.length === 0) ? (
            <div className="text-center py-12 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl">
              <Wifi className="w-12 h-12 text-gray-400 mx-auto mb-3 opacity-50" />
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">No HotSpots Hosted Yet</p>
              <p className="text-xs text-gray-500 mt-1">Create a captive hotspot server and attach it to this gateway.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {router.hotspots.map((h) => (
                <div
                  key={h.id}
                  className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 shadow-sm hover:border-blue-300 dark:hover:border-blue-700 transition-all"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <h4 className="font-bold text-gray-900 dark:text-white text-base">{h.name}</h4>
                      <p className="text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-0.5">
                        <Radio className="w-3.5 h-3.5 text-blue-500" /> SSID: <strong>{h.ssid}</strong>
                      </p>
                    </div>
                    {h.is_default && (
                      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-[10px]">
                        DEFAULT
                      </Badge>
                    )}
                  </div>

                  <div className="text-xs space-y-1 py-3 border-y border-gray-100 dark:border-gray-800 font-mono text-gray-600 dark:text-gray-300">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Interface:</span>
                      <span>{h.interface || h.interface_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Gateway IP:</span>
                      <span>{h.gateway_ip}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Subnet:</span>
                      <span>{h.subnet_mask}</span>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Status: <strong className={h.is_active || h.status === 'ACTIVE' ? 'text-green-600' : 'text-gray-400'}>
                        {h.is_active || h.status === 'ACTIVE' ? 'Active' : 'Disabled'}
                      </strong>
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`/hotspots/${h.id}`)}
                      className="h-8 text-xs"
                    >
                      Manage HotSpot <ExternalLink className="w-3 h-3 ml-1" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB: RADIUS AAA */}
      {activeTab === 'radius' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-indigo-600" /> FreeRADIUS AAA Client Integration
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  Centralized AAA authentication, accounting, and Change of Authorization (CoA) for this router.
                </p>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 dark:bg-green-950/60 dark:text-green-300 border border-green-200 dark:border-green-800/50">
                Configured
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200/70 dark:border-gray-700/60 space-y-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">NAS IP / Identifier</span>
                <p className="font-mono font-semibold text-gray-900 dark:text-white">
                  {router.management_ip}
                </p>
                <p className="text-xs text-gray-500">
                  Traffic originating from this IP is matched against FreeRADIUS <code className="font-mono">nas</code> records.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200/70 dark:border-gray-700/60 space-y-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Shared RADIUS Secret</span>
                <p className="font-mono font-semibold text-gray-700 dark:text-gray-300">
                  ••••••••••••••••
                </p>
                <p className="text-xs text-gray-500">
                  Encrypted at rest using AES-256-GCM. Never disclosed over client API.
                </p>
              </div>

              <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200/70 dark:border-gray-700/60 space-y-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Ports & Protocols</span>
                <div className="space-y-1 text-xs font-mono text-gray-700 dark:text-gray-300">
                  <div>Auth Port: <strong>1812 UDP</strong></div>
                  <div>Acct Port: <strong>1813 UDP</strong></div>
                  <div>CoA / Disconnect: <strong>3799 UDP</strong></div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200/70 dark:border-gray-700/60 space-y-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Location Association</span>
                <p className="font-medium text-gray-900 dark:text-white">
                  {router.location ? router.location.name : 'Unassigned'}
                </p>
                <p className="text-xs text-gray-500">
                  Sessions on this router inherit location attribution for billing and analytics.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB: SECURITY & ACCESS */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
              <Lock className="w-5 h-5 text-purple-600" /> Gateway Security & Access Policy
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200/70 dark:border-gray-700/60">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">API Transport Encryption</span>
                <p className="font-semibold text-gray-900 dark:text-white mt-1">
                  {router.use_tls ? 'TLS Encrypted (API-SSL)' : 'Plaintext API (Port 8728)'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {router.use_tls
                    ? 'MikroTik API communications use TLS certificate encryption.'
                    : 'Unencrypted communication over internal management VLAN/tunnel.'}
                </p>
              </div>

              <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/60 border border-gray-200/70 dark:border-gray-700/60">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Credential Isolation</span>
                <p className="font-semibold text-green-700 dark:text-green-400 mt-1">
                  Hardware Specific Credentials
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Each router maintains isolated encrypted credentials, avoiding shared master passwords.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PROVISIONING & BOOTSTRAP TAB */}
      {activeTab === 'provisioning' && (
        <div className="space-y-6">
          {/* Section 1: 1-Click Live API Provisioning */}
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-gray-100 dark:border-gray-800">
              <div>
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-xl bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-gray-900 dark:text-white">
                      1-Click Live Router Provisioning
                    </h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      Pushes production configuration directly to RouterOS via API ({router.management_ip}:{router.api_port || 8728}).
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Button
                  onClick={handleRunProvisioning}
                  disabled={provisioning}
                  className="bg-blue-600 hover:bg-blue-700 text-white shadow-sm font-medium h-10 px-5"
                >
                  <Zap className={`w-4 h-4 mr-2 text-amber-300 ${provisioning ? 'animate-spin' : ''}`} />
                  {provisioning ? 'Provisioning Router...' : 'Run Provisioning Now'}
                </Button>
              </div>
            </div>

            {/* Feature Modules Toggles */}
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-800/40 cursor-pointer hover:bg-gray-100/60 transition-colors">
                <input
                  type="checkbox"
                  checked={provRadius}
                  onChange={(e) => setProvRadius(e.target.checked)}
                  className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-xs font-bold text-gray-900 dark:text-white block">
                    FreeRADIUS AAA & CoA
                  </span>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400 leading-tight block mt-0.5">
                    Auth (1812), Acct (1813), and RFC 3576 CoA Disconnect port 3799.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-800/40 cursor-pointer hover:bg-gray-100/60 transition-colors">
                <input
                  type="checkbox"
                  checked={provHotspot}
                  onChange={(e) => setProvHotspot(e.target.checked)}
                  className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-xs font-bold text-gray-900 dark:text-white block">
                    HotSpot Profile
                  </span>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400 leading-tight block mt-0.5">
                    RADIUS authentication, accounting, and 60s interim session updates.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-800/40 cursor-pointer hover:bg-gray-100/60 transition-colors">
                <input
                  type="checkbox"
                  checked={provWalledGarden}
                  onChange={(e) => setProvWalledGarden(e.target.checked)}
                  className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-xs font-bold text-gray-900 dark:text-white block">
                    Payment Walled Garden
                  </span>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400 leading-tight block mt-0.5">
                    Whitelists Snippe, USSD payment endpoints, and captive detection.
                  </span>
                </div>
              </label>

              <label className="flex items-start gap-3 p-3.5 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-800/40 cursor-pointer hover:bg-gray-100/60 transition-colors">
                <input
                  type="checkbox"
                  checked={provAntiTethering}
                  onChange={(e) => setProvAntiTethering(e.target.checked)}
                  className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div>
                  <span className="text-xs font-bold text-gray-900 dark:text-white block">
                    Anti-Tethering Lock
                  </span>
                  <span className="text-[11px] text-gray-500 dark:text-gray-400 leading-tight block mt-0.5">
                    Applies Mangle TTL-1 lock and drops forwarded secondary packets.
                  </span>
                </div>
              </label>
            </div>

            {/* Error Banner */}
            {provisionError && (
              <div className="mt-4 p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-300 text-xs flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
                <div>
                  <span className="font-bold">Provisioning Error: </span>
                  {provisionError}
                </div>
              </div>
            )}

            {/* Execution Result Stepper */}
            {provisionResult && (
              <div className="mt-5 p-5 rounded-2xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2">
                    {provisionResult.success ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-green-100 text-green-800 dark:bg-green-950/60 dark:text-green-300 border border-green-200 dark:border-green-800">
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> Provisioning Complete
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 border border-red-200 dark:border-red-800">
                        <XCircle className="w-3.5 h-3.5 text-red-600" /> Provisioning Incomplete
                      </span>
                    )}
                    <span className="text-xs text-gray-500 font-mono">({provisionResult.elapsed_ms} ms)</span>
                  </div>
                  <span className="text-xs font-mono text-gray-500">
                    Status: <strong className="text-gray-900 dark:text-white">{provisionResult.health_status}</strong>
                  </span>
                </div>

                <div className="mt-4 space-y-2.5">
                  {provisionResult.steps.map((s, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 rounded-xl bg-white dark:bg-gray-900 border border-gray-150 dark:border-gray-800 shadow-xs text-xs"
                    >
                      <div className="flex items-center gap-3">
                        {s.success ? (
                          <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-600 shrink-0" />
                        )}
                        <span className="font-semibold text-gray-900 dark:text-white capitalize">
                          {s.name.replace(/_/g, ' ')}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400">
                          {s.message}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-gray-400 shrink-0">
                        {s.timestamp.split('T')[1]?.split('.')[0] || ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Section 2: 1-Line Remote Terminal Bootstrap Script */}
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm">
            <div className="flex items-center justify-between pb-4 border-b border-gray-100 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400">
                  <FileCode2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-gray-900 dark:text-white">
                    Remote Router Bootstrap Command (.rsc)
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    For new routers or remote deployments without direct API reachability.
                  </p>
                </div>
              </div>

              {bootstrapScript?.download_url && (
                <a
                  href={bootstrapScript.download_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> Download .rsc
                </a>
              )}
            </div>

            <div className="mt-4">
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                Paste this 1-line command into <strong>Winbox ➔ New Terminal</strong> or <strong>SSH</strong>:
              </p>

              <div className="relative group">
                <pre className="p-4 rounded-xl bg-gray-950 text-green-400 font-mono text-xs overflow-x-auto border border-gray-800 select-all">
                  {loadingScript
                    ? 'Generating bootstrap command...'
                    : bootstrapScript?.command || 'Loading command...'}
                </pre>
                {bootstrapScript?.command && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopyText(bootstrapScript.command, true)}
                    className="absolute top-2.5 right-2.5 h-8 text-xs bg-gray-900/90 hover:bg-gray-800 text-white border-gray-700"
                  >
                    {copiedCommand ? (
                      <>
                        <Check className="w-3.5 h-3.5 mr-1 text-green-400" /> Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 mr-1" /> Copy Command
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>

            {/* Collapsible Full Script Viewer */}
            {bootstrapScript?.script && (
              <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                <button
                  onClick={() => setShowScriptDetails(!showScriptDetails)}
                  className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
                >
                  <Sliders className="w-3.5 h-3.5" />
                  {showScriptDetails ? 'Hide full .rsc configuration template' : 'Inspect full .rsc configuration template'}
                </button>

                {showScriptDetails && (
                  <div className="mt-3 relative">
                    <pre className="p-4 rounded-xl bg-gray-900 text-gray-200 font-mono text-[11px] max-h-80 overflow-y-auto border border-gray-800 leading-relaxed select-all">
                      {bootstrapScript.script}
                    </pre>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopyText(bootstrapScript.script, false)}
                      className="absolute top-2.5 right-2.5 h-7 text-xs bg-gray-800 text-white border-gray-700"
                    >
                      {copiedScript ? (
                        <>
                          <Check className="w-3 h-3 mr-1 text-green-400" /> Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3 mr-1" /> Copy Script
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* UPDATE CREDENTIALS MODAL */}
      {showCredModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-800">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
              Update Router Credentials
            </h3>
            <p className="text-xs text-gray-500 mb-4">
              Change management credentials for {router.name}. The API password is encrypted at rest.
            </p>

            {credError && (
              <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-800 border border-red-200 text-xs font-medium">
                {credError}
              </div>
            )}

            <form onSubmit={handleSaveCredentials} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  API Username *
                </label>
                <input
                  type="text"
                  value={credUsername}
                  onChange={(e) => setCredUsername(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  New API Password
                </label>
                <input
                  type="password"
                  value={credPassword}
                  onChange={(e) => setCredPassword(e.target.value)}
                  placeholder="Leave blank to keep existing password"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
                <p className="text-[11px] text-gray-400 mt-1">Never displayed or transmitted in plaintext responses.</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    API Port *
                  </label>
                  <input
                    type="number"
                    value={credPort}
                    onChange={(e) => setCredPort(parseInt(e.target.value) || 8728)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>

                <div className="flex flex-col justify-end">
                  <label className="flex items-center gap-2 cursor-pointer pb-2">
                    <input
                      type="checkbox"
                      checked={credUseTls}
                      onChange={(e) => {
                        const checked = e.target.checked;
                        setCredUseTls(checked);
                        if (checked && credPort === 8728) setCredPort(8729);
                        if (!checked && credPort === 8729) setCredPort(8728);
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                      Use TLS (API-SSL)
                    </span>
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCredModal(false)}
                  disabled={credSaving}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                  disabled={credSaving}
                >
                  {credSaving ? 'Saving...' : 'Save Credentials'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
