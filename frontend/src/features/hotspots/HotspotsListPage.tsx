import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  Wifi,
  Plus,
  Search,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  Radio,
  Server,
  MapPin,
  ExternalLink,
  Users,
  Star,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { hotspotsApi, locationsApi, routersApi } from '../../lib/infrastructure-api';
import { HotspotSummary, LocationSummary, RouterSummary } from '../../types';

export const HotspotsListPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [hotspots, setHotspots] = useState<HotspotSummary[]>([]);
  const [locations, setLocations] = useState<LocationSummary[]>([]);
  const [routers, setRouters] = useState<RouterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLocation, setSelectedLocation] = useState(searchParams.get('location') || 'ALL');
  const [selectedRouter, setSelectedRouter] = useState(searchParams.get('router') || 'ALL');
  const [selectedStatus, setSelectedStatus] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');

  // Create Modal
  const [showCreateModal, setShowCreateModal] = useState(searchParams.get('new') === 'true');
  const [createLocId, setCreateLocId] = useState(searchParams.get('location_id') || '');
  const [createRouterId, setCreateRouterId] = useState(searchParams.get('router_id') || '');
  const [createName, setCreateName] = useState('');
  const [createSsid, setCreateSsid] = useState('');
  const [createSlug, setCreateSlug] = useState('');
  const [createInterface, setCreateInterface] = useState('wlan1');
  const [createGatewayIp, setCreateGatewayIp] = useState('10.5.50.1');
  const [createSubnet, setCreateSubnet] = useState('255.255.255.0');
  const [createLoginUrl, setCreateLoginUrl] = useState('http://10.5.50.1/login');
  const [createIsDefault, setCreateIsDefault] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Action states
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [hList, lList, rList] = await Promise.all([
        hotspotsApi.list(),
        locationsApi.list(),
        routersApi.list(),
      ]);
      setHotspots(hList);
      setLocations(lList);
      setRouters(rList);
    } catch (err: any) {
      setError(err.message || 'Failed to load hotspots fleet data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // If a router was pre-selected, auto-set location
  useEffect(() => {
    if (createRouterId && routers.length > 0) {
      const foundRouter = routers.find((r) => r.id === createRouterId);
      if (foundRouter && foundRouter.location_id) {
        setCreateLocId(foundRouter.location_id);
      }
    }
  }, [createRouterId, routers]);

  // Auto-slug generator from name
  const handleNameChange = (val: string) => {
    setCreateName(val);
    if (!createSlug || createSlug === createName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')) {
      setCreateSlug(val.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''));
    }
  };

  // Routers filtered by selected createLocId
  const availableRoutersForCreate = useMemo(() => {
    if (!createLocId) return routers;
    return routers.filter((r) => r.location_id === createLocId);
  }, [routers, createLocId]);

  // Filtered hotspots list
  const filteredHotspots = useMemo(() => {
    return hotspots.filter((h) => {
      if (selectedLocation !== 'ALL' && h.location?.id !== selectedLocation) {
        return false;
      }
      if (selectedRouter !== 'ALL' && h.router?.id !== selectedRouter) {
        return false;
      }
      if (selectedStatus === 'ACTIVE' && !h.is_active) {
        return false;
      }
      if (selectedStatus === 'INACTIVE' && h.is_active) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = h.name.toLowerCase().includes(q);
        const matchSsid = h.ssid.toLowerCase().includes(q);
        const matchSlug = h.slug.toLowerCase().includes(q);
        const matchInterface = (h.interface || h.interface_name || '').toLowerCase().includes(q);
        const matchRouter = (h.router?.name || '').toLowerCase().includes(q);
        const matchLoc = (h.location?.name || '').toLowerCase().includes(q);
        if (!matchName && !matchSsid && !matchSlug && !matchInterface && !matchRouter && !matchLoc) {
          return false;
        }
      }
      return true;
    });
  }, [hotspots, selectedLocation, selectedRouter, selectedStatus, searchQuery]);

  // Metrics
  const metrics = useMemo(() => {
    const total = hotspots.length;
    const active = hotspots.filter((h) => h.is_active).length;
    const connectedUsers = hotspots.reduce((sum, h) => sum + (h.active_sessions_count || h.active_users_count || 0), 0);
    const protectedCount = hotspots.filter((h) => h.anti_tethering_enabled || h.is_anti_tethering_enabled).length;
    return { total, active, connectedUsers, protectedCount };
  }, [hotspots]);

  const handleSetDefault = async (hotspot: HotspotSummary) => {
    try {
      setActionLoadingId(hotspot.id);
      await hotspotsApi.setDefault(hotspot.id);
      await fetchData();
    } catch (err: any) {
      alert(err.message || 'Failed to set default hotspot.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createRouterId) {
      setCreateError('Please select a router to host this hotspot.');
      return;
    }
    try {
      setCreating(true);
      setCreateError(null);
      const newH = await hotspotsApi.create({
        router_id: createRouterId,
        name: createName,
        ssid: createSsid,
        slug: createSlug,
        interface: createInterface,
        gateway_ip: createGatewayIp,
        subnet_mask: createSubnet,
        router_login_url: createLoginUrl,
        is_default: createIsDefault,
      });
      setShowCreateModal(false);
      // Reset form
      setCreateName('');
      setCreateSsid('');
      setCreateSlug('');
      setCreateIsDefault(false);
      navigate(`/hotspots/${newH.id}`);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create hotspot server.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Wifi className="w-7 h-7 text-blue-600 dark:text-blue-400" />
            Hotspots
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage captive portal access profiles, SSIDs, and client policies across your network.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium"
          >
            <Plus className="w-4 h-4 mr-1.5" /> Create Hotspot
          </Button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span className="font-semibold uppercase tracking-wider">Total Hotspots</span>
            <Wifi className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.total}</div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span className="font-semibold uppercase tracking-wider">Active Services</span>
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">{metrics.active}</div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span className="font-semibold uppercase tracking-wider">Connected Users</span>
            <Users className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{metrics.connectedUsers}</div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
            <span className="font-semibold uppercase tracking-wider">Anti-Tethering Protected</span>
            <ShieldCheck className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{metrics.protectedCount}</div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white dark:bg-gray-900 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search hotspot, SSID, slug, or interface..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Location Filter */}
          <select
            value={selectedLocation}
            onChange={(e) => setSelectedLocation(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
          >
            <option value="ALL">All Locations</option>
            {locations.map((loc) => (
              <option key={loc.id} value={loc.id}>{loc.name}</option>
            ))}
          </select>

          {/* Router Filter */}
          <select
            value={selectedRouter}
            onChange={(e) => setSelectedRouter(e.target.value)}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
          >
            <option value="ALL">All Routers</option>
            {routers.map((r) => (
              <option key={r.id} value={r.id}>{r.name} ({r.management_ip})</option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value as any)}
            className="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300"
          >
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active Only</option>
            <option value="INACTIVE">Disabled Only</option>
          </select>
        </div>
      </div>

      {/* Hotspots Fleet Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] text-gray-500">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
          <p className="text-sm font-medium">Loading hotspots fleet...</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-center">
          <AlertCircle className="w-8 h-8 text-red-600 mx-auto mb-2" />
          <p className="text-sm text-red-700 dark:text-red-400 font-medium">{error}</p>
          <Button onClick={fetchData} variant="outline" size="sm" className="mt-4">
            Retry
          </Button>
        </div>
      ) : filteredHotspots.length === 0 ? (
        <div className="p-12 text-center bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
          <Wifi className="w-12 h-12 text-gray-400 mx-auto mb-3 opacity-60" />
          <h3 className="text-base font-bold text-gray-900 dark:text-white">No Hotspots Found</h3>
          <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
            {searchQuery || selectedLocation !== 'ALL' || selectedRouter !== 'ALL'
              ? 'No hotspot profiles match the specified filters.'
              : 'You have not registered any captive hotspot servers yet.'}
          </p>
          <Button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 bg-blue-600 hover:bg-blue-700 text-white text-xs"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> Create First Hotspot
          </Button>
        </div>
      ) : (
        /* Hotspots Table */
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="bg-gray-50 dark:bg-gray-800/60 text-xs uppercase font-semibold text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                <tr>
                  <th className="px-5 py-3.5">Hotspot & SSID</th>
                  <th className="px-5 py-3.5">Site & Router</th>
                  <th className="px-5 py-3.5">Network Config</th>
                  <th className="px-5 py-3.5">Assigned Plans</th>
                  <th className="px-5 py-3.5">Active Users</th>
                  <th className="px-5 py-3.5">Anti-Tethering</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {filteredHotspots.map((h) => (
                  <tr key={h.id} className="hover:bg-gray-50/70 dark:hover:bg-gray-800/40 transition-colors">
                    {/* Hotspot & SSID */}
                    <td className="px-5 py-4">
                      <div className="flex items-start gap-2">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <Link
                              to={`/hotspots/${h.id}`}
                              className="font-bold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                            >
                              {h.name}
                            </Link>
                            {h.is_default && (
                              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 text-[10px] font-bold px-1.5 py-0">
                                DEFAULT
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-0.5 font-medium">
                            <Radio className="w-3 h-3 text-blue-500" />
                            <span>SSID: <strong>{h.ssid}</strong></span>
                            <span className="text-gray-300">•</span>
                            <code className="text-[11px] font-mono text-gray-400">{h.slug}</code>
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Site & Router */}
                    <td className="px-5 py-4 text-xs">
                      <div className="space-y-0.5">
                        {h.location ? (
                          <Link
                            to={`/locations/${h.location.id}`}
                            className="font-medium text-gray-900 dark:text-white hover:text-blue-600 flex items-center gap-1"
                          >
                            <MapPin className="w-3 h-3 text-gray-400" /> {h.location.name}
                          </Link>
                        ) : (
                          <span className="text-gray-400">Unassigned</span>
                        )}
                        {h.router ? (
                          <Link
                            to={`/routers/${h.router.id}`}
                            className="text-gray-500 dark:text-gray-400 hover:text-blue-600 flex items-center gap-1 font-mono"
                          >
                            <Server className="w-3 h-3 text-gray-400" /> {h.router.name}
                          </Link>
                        ) : (
                          <span className="text-gray-400">No gateway</span>
                        )}
                      </div>
                    </td>

                    {/* Network Config */}
                    <td className="px-5 py-4 text-xs font-mono">
                      <div className="space-y-0.5">
                        <div>Int: <span className="font-semibold text-gray-800 dark:text-gray-200">{h.interface || h.interface_name}</span></div>
                        <div className="text-gray-500">GW: {h.gateway_ip}</div>
                      </div>
                    </td>

                    {/* Assigned Plans */}
                    <td className="px-5 py-4 text-xs">
                      <span className="px-2 py-0.5 rounded-full font-medium bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                        {h.plans_count && h.plans_count > 0 ? `${h.plans_count} plans` : 'All Active Plans'}
                      </span>
                    </td>

                    {/* Active Users */}
                    <td className="px-5 py-4">
                      <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-900 dark:text-white">
                        <Users className="w-3.5 h-3.5 text-blue-500" />
                        {h.active_sessions_count || h.active_users_count || 0}
                      </span>
                    </td>

                    {/* Anti-Tethering */}
                    <td className="px-5 py-4">
                      {h.anti_tethering_enabled || h.is_anti_tethering_enabled ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-950/60 px-2 py-0.5 rounded-full border border-purple-200 dark:border-purple-800/60">
                          <ShieldCheck className="w-3 h-3 text-purple-600" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-gray-500 bg-gray-50 dark:bg-gray-800/60 px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700">
                          <ShieldAlert className="w-3 h-3 text-gray-400" /> Disabled
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold ${
                        h.is_active ? 'text-green-600 dark:text-green-400' : 'text-gray-400'
                      }`}>
                        {h.is_active ? (
                          <><CheckCircle2 className="w-3.5 h-3.5" /> Active</>
                        ) : (
                          <><XCircle className="w-3.5 h-3.5" /> Disabled</>
                        )}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {!h.is_default && (
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={actionLoadingId === h.id}
                            onClick={() => handleSetDefault(h)}
                            title="Set as Default Hotspot"
                            className="h-8 text-xs text-gray-600 hover:text-blue-600"
                          >
                            <Star className="w-3.5 h-3.5" />
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigate(`/hotspots/${h.id}`)}
                          className="h-8 text-xs font-medium"
                        >
                          Manage <ExternalLink className="w-3 h-3 ml-1" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* CREATE HOTSPOT MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm overflow-y-auto">
          <div className="bg-white dark:bg-gray-900 rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-gray-200 dark:border-gray-800 my-8">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-1">
              Create New Hotspot Server
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
              Configure a new captive portal service attached to a MikroTik gateway.
            </p>

            {createError && (
              <div className="mb-4 p-3 rounded-lg bg-red-50 text-red-800 border border-red-200 text-xs font-medium">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              {/* Location & Router Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Operating Location *
                  </label>
                  <select
                    value={createLocId}
                    onChange={(e) => {
                      setCreateLocId(e.target.value);
                      setCreateRouterId('');
                    }}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="">Select Location</option>
                    {locations.map((loc) => (
                      <option key={loc.id} value={loc.id}>{loc.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Gateway Router *
                  </label>
                  <select
                    value={createRouterId}
                    onChange={(e) => setCreateRouterId(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  >
                    <option value="">Select Router</option>
                    {availableRoutersForCreate.map((r) => (
                      <option key={r.id} value={r.id}>{r.name} ({r.management_ip})</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Name & SSID */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Hotspot Profile Name *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Mbezi Resort Guest WiFi"
                    value={createName}
                    onChange={(e) => handleNameChange(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Broadcast SSID *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Mbezi-Guest-WiFi"
                    value={createSsid}
                    onChange={(e) => setCreateSsid(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              {/* Slug & Interface */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    URL Portal Slug *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. mbezi-guest"
                    value={createSlug}
                    onChange={(e) => setCreateSlug(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                  />
                  <p className="text-[11px] text-gray-400 mt-1">Portal URL: /portal/{createSlug || ':slug'}</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Router Interface *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. wlan1 or bridge-hotspot"
                    value={createInterface}
                    onChange={(e) => setCreateInterface(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                  />
                </div>
              </div>

              {/* Gateway IP & Subnet */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Gateway IP *
                  </label>
                  <input
                    type="text"
                    placeholder="10.5.50.1"
                    value={createGatewayIp}
                    onChange={(e) => setCreateGatewayIp(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Subnet Mask *
                  </label>
                  <input
                    type="text"
                    placeholder="255.255.255.0"
                    value={createSubnet}
                    onChange={(e) => setCreateSubnet(e.target.value)}
                    required
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                  />
                </div>
              </div>

              {/* Router Login URL */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  RouterOS HotSpot Login URL *
                </label>
                <input
                  type="text"
                  placeholder="http://10.5.50.1/login"
                  value={createLoginUrl}
                  onChange={(e) => setCreateLoginUrl(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                />
              </div>

              {/* Default Checkbox */}
              <div>
                <label className="flex items-center gap-2 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={createIsDefault}
                    onChange={(e) => setCreateIsDefault(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                    Set as company default hotspot profile
                  </span>
                </label>
              </div>

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100 dark:border-gray-800">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateModal(false)}
                  disabled={creating}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                  disabled={creating}
                >
                  {creating ? 'Creating...' : 'Create Hotspot'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
