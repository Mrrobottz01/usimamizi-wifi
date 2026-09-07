import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  MapPin,
  ArrowLeft,
  RefreshCw,
  Edit2,
  PowerOff,
  Share2,
  Router as RouterIcon,
  Radio,
  Activity,
  AlertTriangle,
  User,
  ExternalLink,
  Building,
  Smartphone,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { locationsApi, routersApi } from '../../lib/infrastructure-api';
import {
  LocationDetail,
  LocationRouterSummary,
  LocationHotspotSummary,
  LocationSessionSummary,
  RouterSummary,
  SiteType,
  LocationStatus,
} from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { HealthBadge, StatusBadge, SITE_TYPES } from './LocationsListPage';

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0s';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hrs > 0) return `${hrs}h ${mins}m`;
  if (mins > 0) return `${mins}m ${secs}s`;
  return `${secs}s`;
}

export const LocationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.id;
  const navigate = useNavigate();
  const { toast } = useToast();

  const [location, setLocation] = useState<LocationDetail | null>(null);
  const [routers, setRouters] = useState<LocationRouterSummary[]>([]);
  const [hotspots, setHotspots] = useState<LocationHotspotSummary[]>([]);
  const [sessions, setSessions] = useState<LocationSessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  // Edit Modal State
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [editFormData, setEditFormData] = useState<any>({});

  // Move Router Modal State
  const [moveModalOpen, setMoveModalOpen] = useState(false);
  const [movingRouter, setMovingRouter] = useState(false);
  const [candidateRouters, setCandidateRouters] = useState<RouterSummary[]>([]);
  const [selectedRouterId, setSelectedRouterId] = useState('');

  const fetchLocationData = useCallback(async () => {
    if (!id || !companyId) return;
    try {
      setLoading(true);
      const locData = await locationsApi.get(id, companyId);
      setLocation(locData);

      const [routersData, hotspotsData, sessionsData] = await Promise.all([
        locationsApi.getRouters(id, companyId).catch(() => []),
        locationsApi.getHotspots(id, companyId).catch(() => []),
        locationsApi.getSessions(id, companyId).catch(() => []),
      ]);

      setRouters(routersData);
      setHotspots(hotspotsData);
      setSessions(sessionsData);
    } catch (err: any) {
      toast({ title: 'Failed to load location details', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [id, companyId, toast]);

  useEffect(() => {
    fetchLocationData();
  }, [fetchLocationData]);

  const handleOpenEdit = () => {
    if (!location) return;
    setEditFormData({
      name: location.name,
      code: location.code,
      site_type: location.site_type,
      status: location.status,
      region: location.region || '',
      district: location.district || '',
      address: location.address || '',
      timezone: location.timezone || 'Africa/Dar_es_Salaam',
      operating_hours: location.operating_hours || '',
      installation_date: location.installation_date || '',
      external_reference: location.external_reference || '',
      contact_person: location.contact_person || '',
      contact_phone: location.contact_phone || '',
      latitude: location.latitude ? String(location.latitude) : '',
      longitude: location.longitude ? String(location.longitude) : '',
      notes: location.notes || '',
    });
    setEditModalOpen(true);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !companyId) return;

    try {
      setSavingEdit(true);
      await locationsApi.update(id, {
        ...editFormData,
        company_id: companyId,
      });
      toast({ title: 'Location updated successfully', type: 'success' });
      setEditModalOpen(false);
      fetchLocationData();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to update location', type: 'error' });
    } finally {
      setSavingEdit(false);
    }
  };

  const handleToggleActive = async () => {
    if (!location || !companyId) return;
    try {
      if (location.is_active && location.status === 'ACTIVE') {
        const res = await locationsApi.delete(location.id, companyId);
        toast({
          title: res.detail || 'Location deactivated',
          type: res.action === 'deleted' ? 'success' : 'info',
        });
      } else {
        const res = await locationsApi.reactivate(location.id, companyId);
        toast({ title: res.name ? `Location ${res.name} reactivated` : 'Location reactivated', type: 'success' });
      }
      fetchLocationData();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Action failed', type: 'error' });
    }
  };

  const handleOpenMoveRouter = async () => {
    if (!companyId) return;
    try {
      const allRouters = await routersApi.list({ company_id: companyId });
      // Filter out routers that already reside at this location
      const candidates = allRouters.filter((r) => r.location?.id !== id);
      setCandidateRouters(candidates);
      setSelectedRouterId(candidates.length > 0 ? candidates[0].id : '');
      setMoveModalOpen(true);
    } catch (err) {
      toast({ title: 'Failed to load company routers', type: 'error' });
    }
  };

  const handleExecuteMove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !selectedRouterId || !companyId) return;

    try {
      setMovingRouter(true);
      const res = await locationsApi.moveRouter(id, selectedRouterId, companyId);
      toast({
        title: res.success ? 'Router moved successfully' : 'Move completed',
        type: 'success',
      });
      setMoveModalOpen(false);
      fetchLocationData();
    } catch (err: any) {
      toast({
        title: err.response?.data?.detail || 'Failed to move router',
        type: 'error',
      });
    } finally {
      setMovingRouter(false);
    }
  };

  if (loading && !location) {
    return (
      <div className="py-24 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-2">
        <RefreshCw className="h-6 w-6 animate-spin text-primary" />
        <p>Loading location details...</p>
      </div>
    );
  }

  if (!location) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <h2 className="text-xl font-bold text-foreground">Location Not Found</h2>
        <p className="text-sm text-muted-foreground mt-1 mb-4">
          The requested deployment site does not exist or belongs to another company.
        </p>
        <Button onClick={() => navigate('/locations')} size="sm">
          Return to Locations
        </Button>
      </div>
    );
  }

  const siteTypeLabel = SITE_TYPES.find((t) => t.value === location.site_type)?.label || location.site_type;

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Back Navigation & Breadcrumb */}
      <div>
        <button
          onClick={() => navigate('/locations')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors mb-3"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Locations</span>
        </button>

        {/* Header Title & Actions */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight text-foreground">{location.name}</h1>
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground">
                {location.code}
              </span>
              <HealthBadge health={location.network_health} />
              <StatusBadge status={location.status} />
            </div>
            <p className="text-sm text-muted-foreground mt-1 flex items-center gap-1.5">
              <Building className="h-3.5 w-3.5 text-muted-foreground" />
              <span>{siteTypeLabel}</span>
              {(location.region || location.district) && (
                <>
                  <span>•</span>
                  <span>{[location.region, location.district].filter(Boolean).join(', ')}</span>
                </>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchLocationData}
              disabled={loading}
              className="gap-1.5 text-xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenMoveRouter}
              className="gap-1.5 text-xs"
            >
              <Share2 className="h-3.5 w-3.5" />
              <span>Move Router</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleOpenEdit}
              className="gap-1.5 text-xs"
            >
              <Edit2 className="h-3.5 w-3.5" />
              <span>Edit Site</span>
            </Button>
            <Button
              variant={location.is_active && location.status === 'ACTIVE' ? 'destructive' : 'primary'}
              size="sm"
              onClick={handleToggleActive}
              className="gap-1.5 text-xs"
            >
              <PowerOff className="h-3.5 w-3.5" />
              <span>{location.is_active && location.status === 'ACTIVE' ? 'Deactivate' : 'Reactivate'}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Detail Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full justify-start border-b border-border bg-transparent p-0 h-auto rounded-none gap-6">
          <TabsTrigger
            value="overview"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium text-xs"
          >
            <MapPin className="h-4 w-4" />
            <span>Overview</span>
          </TabsTrigger>
          <TabsTrigger
            value="routers"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium text-xs"
          >
            <RouterIcon className="h-4 w-4" />
            <span>Routers ({routers.length})</span>
          </TabsTrigger>
          <TabsTrigger
            value="hotspots"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium text-xs"
          >
            <Radio className="h-4 w-4" />
            <span>Hotspots ({hotspots.length})</span>
          </TabsTrigger>
          <TabsTrigger
            value="sessions"
            className="flex items-center gap-2 border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent rounded-none px-1 pb-3 pt-2 text-muted-foreground data-[state=active]:text-foreground font-medium text-xs"
          >
            <Activity className="h-4 w-4" />
            <span>Active Sessions ({sessions.length})</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Overview */}
        <TabsContent value="overview" className="pt-6 space-y-6">
          {/* Network Health Summary Box */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Network Health
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">Derived Status</span>
                  <HealthBadge health={location.network_health} />
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Online Gateways</span>
                  <span className="font-bold text-foreground">
                    {location.online_router_count} / {location.router_count}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Degraded / Offline</span>
                  <span className="font-bold text-amber-600 dark:text-amber-400">
                    {location.degraded_router_count + location.unreachable_router_count}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Service Capacity
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Total Hotspots</span>
                  <span className="font-bold text-foreground">{location.hotspot_count}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Active Hotspots</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">{location.active_hotspot_count}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Active Users</span>
                  <span className="font-bold text-primary">{location.active_session_count}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Administrative Reference
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>External Ref</span>
                  <span className="font-mono text-xs text-foreground">{location.external_reference || '—'}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Timezone</span>
                  <span className="font-mono text-xs text-foreground">{location.timezone}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Commissioned</span>
                  <span className="text-xs text-foreground">{location.installation_date || '—'}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Operational Details Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Physical & Spatial Card */}
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-primary" />
                  <span>Physical Venue Information</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Full Address</span>
                  <span className="col-span-2 font-medium text-foreground">{location.address || '—'}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Region / District</span>
                  <span className="col-span-2 font-medium text-foreground">
                    {[location.region, location.district].filter(Boolean).join(' · ') || '—'}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Operating Schedule</span>
                  <span className="col-span-2 font-medium text-foreground">{location.operating_hours || '24/7'}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-1.5">
                  <span className="text-muted-foreground">GPS Coordinates</span>
                  <span className="col-span-2 font-mono text-foreground">
                    {location.latitude && location.longitude ? `${location.latitude}, ${location.longitude}` : 'Not mapped'}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Operational Contact Card */}
            <Card className="border-border">
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <User className="h-4 w-4 text-primary" />
                  <span>Site Management & Notes</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Contact Person</span>
                  <span className="col-span-2 font-medium text-foreground">{location.contact_person || '—'}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-border/50">
                  <span className="text-muted-foreground">Contact Phone</span>
                  <span className="col-span-2 font-mono text-foreground">{location.contact_phone || '—'}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-1.5">
                  <span className="text-muted-foreground">Internal Notes</span>
                  <span className="col-span-2 text-muted-foreground whitespace-pre-wrap">{location.notes || 'None recorded'}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Tab 2: Routers */}
        <TabsContent value="routers" className="pt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Deployed Gateways</h3>
              <p className="text-xs text-muted-foreground">MikroTik routers stationed at this physical facility.</p>
            </div>
            <Button size="sm" onClick={() => navigate('/routers')} variant="outline" className="text-xs gap-1.5">
              <span>Fleet View</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
          </div>

          {routers.length === 0 ? (
            <div className="py-12 text-center border border-dashed border-border rounded-xl p-6 bg-card/40">
              <RouterIcon className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium text-foreground">No routers assigned to this site</p>
              <p className="text-xs text-muted-foreground mt-1 mb-3">
                Register a new router or relocate an existing router here.
              </p>
              <Button size="sm" onClick={handleOpenMoveRouter} className="text-xs">
                Move Router Here
              </Button>
            </div>
          ) : (
            <div className="border border-border rounded-xl overflow-hidden bg-card">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="p-3">Router Name</th>
                    <th className="p-3">Model / Identity</th>
                    <th className="p-3">Management IP</th>
                    <th className="p-3">Health</th>
                    <th className="p-3">Hotspots</th>
                    <th className="p-3">Last Seen</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {routers.map((r) => (
                    <tr key={r.id} className="hover:bg-muted/30 transition-colors">
                      <td className="p-3 font-semibold text-foreground">
                        <button
                          onClick={() => navigate(`/routers/${r.id}`)}
                          className="hover:text-primary transition-colors text-left"
                        >
                          {r.name}
                        </button>
                      </td>
                      <td className="p-3 text-muted-foreground">
                        <span>{r.identity || 'MikroTik'}</span>
                        {r.model && <span className="block text-[11px] opacity-80">{r.model}</span>}
                      </td>
                      <td className="p-3 font-mono">
                        <span>{r.management_ip}:{r.api_port}</span>
                        {r.use_tls && (
                          <Badge variant="outline" className="ml-1.5 text-[10px] py-0 px-1">SSL</Badge>
                        )}
                      </td>
                      <td className="p-3">
                        <HealthBadge health={r.health_status as any} />
                      </td>
                      <td className="p-3 font-semibold text-foreground">{r.hotspots_count}</td>
                      <td className="p-3 text-muted-foreground">
                        {r.last_seen_at ? new Date(r.last_seen_at).toLocaleTimeString() : 'Never'}
                      </td>
                      <td className="p-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/routers/${r.id}`)}
                          className="h-7 px-2 text-xs"
                        >
                          Manage
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        {/* Tab 3: Hotspots */}
        <TabsContent value="hotspots" className="pt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Hosted HotSpot Services</h3>
              <p className="text-xs text-muted-foreground">Captive portal SSIDs and subscriber access zones on site.</p>
            </div>
            <Button size="sm" onClick={() => navigate('/hotspots')} variant="outline" className="text-xs gap-1.5">
              <span>Hotspots View</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
          </div>

          {hotspots.length === 0 ? (
            <div className="py-12 text-center border border-dashed border-border rounded-xl p-6 bg-card/40">
              <Radio className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium text-foreground">No hotspots hosted at this location</p>
              <p className="text-xs text-muted-foreground mt-1 mb-3">
                Create a hotspot captive access service attached to this venue.
              </p>
              <Button size="sm" onClick={() => navigate('/hotspots')} className="text-xs">
                Create Hotspot
              </Button>
            </div>
          ) : (
            <div className="border border-border rounded-xl overflow-hidden bg-card">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="p-3">Hotspot</th>
                    <th className="p-3">SSID</th>
                    <th className="p-3">Router Gateway</th>
                    <th className="p-3">Network Interface</th>
                    <th className="p-3">Users</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {hotspots.map((h) => (
                    <tr key={h.id} className="hover:bg-muted/30 transition-colors">
                      <td className="p-3 font-semibold text-foreground">
                        <button
                          onClick={() => navigate(`/hotspots/${h.id}`)}
                          className="hover:text-primary transition-colors text-left flex items-center gap-1.5"
                        >
                          <span>{h.name}</span>
                          {h.is_default && (
                            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">DEFAULT</Badge>
                          )}
                        </button>
                      </td>
                      <td className="p-3 font-mono text-muted-foreground">{h.ssid}</td>
                      <td className="p-3 text-muted-foreground">
                        {h.router_name ? (
                          <button
                            onClick={() => h.router_id && navigate(`/routers/${h.router_id}`)}
                            className="hover:underline text-primary"
                          >
                            {h.router_name}
                          </button>
                        ) : '—'}
                      </td>
                      <td className="p-3 font-mono text-muted-foreground">
                        {h.interface_name} ({h.gateway_ip})
                      </td>
                      <td className="p-3 font-bold text-primary">{h.active_sessions_count}</td>
                      <td className="p-3">
                        <Badge variant={h.status === 'ACTIVE' ? 'success' : 'outline'} className="text-[11px]">
                          {h.status}
                        </Badge>
                      </td>
                      <td className="p-3 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/hotspots/${h.id}`)}
                          className="h-7 px-2 text-xs"
                        >
                          Configure
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        {/* Tab 4: Sessions */}
        <TabsContent value="sessions" className="pt-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Active Site Sessions</h3>
              <p className="text-xs text-muted-foreground">Currently connected client devices across this location's hotspots.</p>
            </div>
            <Button size="sm" onClick={() => navigate('/sessions')} variant="outline" className="text-xs gap-1.5">
              <span>All Active Sessions</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
          </div>

          {sessions.length === 0 ? (
            <div className="py-12 text-center border border-dashed border-border rounded-xl p-6 bg-card/40">
              <Activity className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium text-foreground">No active client sessions</p>
              <p className="text-xs text-muted-foreground mt-1">
                Connected subscribers at this location will appear here in real-time.
              </p>
            </div>
          ) : (
            <div className="border border-border rounded-xl overflow-hidden bg-card">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="p-3">Subscriber / Code</th>
                    <th className="p-3">Device & IP</th>
                    <th className="p-3">Hotspot</th>
                    <th className="p-3">Duration</th>
                    <th className="p-3">Traffic (Total)</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {sessions.map((s) => (
                    <tr key={s.id} className="hover:bg-muted/30 transition-colors">
                      <td className="p-3 font-semibold text-foreground">{s.username}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-1.5 font-medium text-foreground">
                          <Smartphone className="h-3.5 w-3.5 text-primary shrink-0" />
                          <span className="font-semibold">{s.device_name || 'Generic Device'}</span>
                        </div>
                        <div className="font-mono text-[11px] text-muted-foreground">{s.client_mac}</div>
                        {s.client_ip && <div className="text-[10px] font-mono opacity-70">{s.client_ip}</div>}
                      </td>
                      <td className="p-3 text-muted-foreground">{s.hotspot_name || '—'}</td>
                      <td className="p-3 text-muted-foreground">{formatDuration(s.duration_seconds)}</td>
                      <td className="p-3 font-mono text-foreground">{formatBytes(s.total_bytes)}</td>
                      <td className="p-3">
                        <Badge variant="success" className="text-[10px] px-1.5 py-0">
                          {s.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Edit Location Modal */}
      <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-primary" />
              <span>Edit Location</span>
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSaveEdit} className="space-y-4 pt-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Location Name *</label>
                <Input
                  value={editFormData.name || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                  required
                  className="text-xs h-9"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Location Code *</label>
                <Input
                  value={editFormData.code || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, code: e.target.value })}
                  required
                  className="text-xs h-9 font-mono uppercase"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Site Categorization *</label>
                <select
                  value={editFormData.site_type || 'BRANCH'}
                  onChange={(e) => setEditFormData({ ...editFormData, site_type: e.target.value as SiteType })}
                  className="w-full h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {SITE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Status *</label>
                <select
                  value={editFormData.status || 'ACTIVE'}
                  onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value as LocationStatus })}
                  className="w-full h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="ACTIVE">Active (Operational)</option>
                  <option value="MAINTENANCE">Maintenance</option>
                  <option value="INACTIVE">Inactive (Suspended)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Region</label>
                <Input
                  value={editFormData.region || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, region: e.target.value })}
                  className="text-xs h-9"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">District</label>
                <Input
                  value={editFormData.district || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, district: e.target.value })}
                  className="text-xs h-9"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="text-xs font-semibold text-foreground block mb-1">Address</label>
                <Input
                  value={editFormData.address || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, address: e.target.value })}
                  className="text-xs h-9"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Operating Hours</label>
                <Input
                  value={editFormData.operating_hours || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, operating_hours: e.target.value })}
                  className="text-xs h-9"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Contact Phone</label>
                <Input
                  value={editFormData.contact_phone || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, contact_phone: e.target.value })}
                  className="text-xs h-9 font-mono"
                />
              </div>
            </div>

            <DialogFooter className="gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditModalOpen(false)}
                disabled={savingEdit}
                className="text-xs h-9"
              >
                Cancel
              </Button>
              <Button type="submit" disabled={savingEdit} className="text-xs h-9">
                {savingEdit ? <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                <span>Save Changes</span>
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Move Router Modal */}
      <Dialog open={moveModalOpen} onOpenChange={setMoveModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Share2 className="h-5 w-5 text-primary" />
              <span>Relocate Router into {location.name}</span>
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleExecuteMove} className="space-y-4 pt-2">
            <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-800 dark:text-amber-300">
              <p className="font-semibold flex items-center gap-1 mb-1">
                <AlertTriangle className="h-3.5 w-3.5" />
                <span>Router Relocation Cascade</span>
              </p>
              <p>
                Moving a router automatically moves all of its hosted HotSpots to this location as well.
                Historical client sessions and payments are preserved intact.
              </p>
            </div>

            <div>
              <label className="text-xs font-semibold text-foreground block mb-1">
                Select Router to Move *
              </label>
              {candidateRouters.length === 0 ? (
                <p className="text-xs text-muted-foreground p-3 border border-border rounded-lg">
                  No candidate routers available in other locations.
                </p>
              ) : (
                <select
                  value={selectedRouterId}
                  onChange={(e) => setSelectedRouterId(e.target.value)}
                  className="w-full h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {candidateRouters.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.management_ip}) — currently at: {r.location?.name || 'Unassigned'}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <DialogFooter className="gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setMoveModalOpen(false)}
                disabled={movingRouter}
                className="text-xs h-9"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={movingRouter || candidateRouters.length === 0}
                className="text-xs h-9"
              >
                {movingRouter ? <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1" /> : null}
                <span>Confirm Relocation</span>
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};
