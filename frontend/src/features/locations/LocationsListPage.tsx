import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapPin,
  Search,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Router as RouterIcon,
  Users,
  Edit2,
  PowerOff,
  ChevronRight,
  Clock,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { locationsApi } from '../../lib/infrastructure-api';
import {
  LocationSummary,
  SiteType,
  LocationStatus,
  LocationNetworkHealth,
} from '../../types';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogHeader, DialogTitle, DialogContent, DialogFooter } from '../../components/ui/dialog';

export const SITE_TYPES: { value: SiteType; label: string }[] = [
  { value: 'BRANCH', label: 'Branch Office' },
  { value: 'HOTEL', label: 'Hotel & Hospitality' },
  { value: 'RESTAURANT', label: 'Restaurant' },
  { value: 'CAFE', label: 'Café & Lounge' },
  { value: 'BUS_TERMINAL', label: 'Bus / Transit Terminal' },
  { value: 'MALL', label: 'Shopping Mall' },
  { value: 'OFFICE', label: 'Commercial Office' },
  { value: 'PUBLIC_SITE', label: 'Public Site / Park' },
  { value: 'OTHER', label: 'Other Venue' },
];

export function HealthBadge({ health }: { health: LocationNetworkHealth }) {
  switch (health) {
    case 'HEALTHY':
      return (
        <Badge variant="success" className="flex items-center gap-1 font-medium">
          <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
          <span>Healthy</span>
        </Badge>
      );
    case 'DEGRADED':
      return (
        <Badge variant="warning" className="flex items-center gap-1 font-medium">
          <AlertTriangle className="h-3 w-3 text-amber-600 dark:text-amber-400" />
          <span>Degraded</span>
        </Badge>
      );
    case 'OFFLINE':
      return (
        <Badge variant="destructive" className="flex items-center gap-1 font-medium">
          <XCircle className="h-3 w-3 text-rose-600 dark:text-rose-400" />
          <span>Offline</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="flex items-center gap-1 text-muted-foreground">
          <HelpCircle className="h-3 w-3" />
          <span>Unknown</span>
        </Badge>
      );
  }
}

export function StatusBadge({ status }: { status: LocationStatus }) {
  switch (status) {
    case 'ACTIVE':
      return <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">Active</Badge>;
    case 'INACTIVE':
      return <Badge variant="outline" className="text-muted-foreground">Inactive</Badge>;
    case 'MAINTENANCE':
      return <Badge variant="warning">Maintenance</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export const LocationsListPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.id;
  const navigate = useNavigate();
  const { toast } = useToast();

  const [locations, setLocations] = useState<LocationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [siteTypeFilter, setSiteTypeFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [healthFilter, setHealthFilter] = useState<string>('ALL');

  // Modal State for Add / Edit
  const [modalOpen, setModalOpen] = useState(false);
  const [editingLocation, setEditingLocation] = useState<LocationSummary | null>(null);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<{
    name: string;
    code: string;
    site_type: SiteType;
    status: LocationStatus;
    region: string;
    district: string;
    address: string;
    timezone: string;
    operating_hours: string;
    installation_date: string;
    external_reference: string;
    contact_person: string;
    contact_phone: string;
    latitude: string;
    longitude: string;
    notes: string;
  }>({
    name: '',
    code: '',
    site_type: 'BRANCH',
    status: 'ACTIVE',
    region: '',
    district: '',
    address: '',
    timezone: 'Africa/Dar_es_Salaam',
    operating_hours: '',
    installation_date: '',
    external_reference: '',
    contact_person: '',
    contact_phone: '',
    latitude: '',
    longitude: '',
    notes: '',
  });

  const fetchLocations = useCallback(async () => {
    if (!companyId) return;
    try {
      setLoading(true);
      const data = await locationsApi.list({
        company_id: companyId,
        q: searchQuery.trim() || undefined,
        site_type: siteTypeFilter !== 'ALL' ? siteTypeFilter : undefined,
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
      });
      setLocations(data);
    } catch (err: any) {
      console.error(err);
      toast({ title: 'Failed to load locations', type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [companyId, searchQuery, siteTypeFilter, statusFilter, toast]);

  useEffect(() => {
    fetchLocations();
  }, [fetchLocations]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    const totalLocations = locations.length;
    const activeSites = locations.filter((l) => l.is_active && l.status === 'ACTIVE').length;
    const onlineRouters = locations.reduce((acc, l) => acc + (l.online_router_count || 0), 0);
    const activeUsers = locations.reduce((acc, l) => acc + (l.active_session_count || 0), 0);
    return { totalLocations, activeSites, onlineRouters, activeUsers };
  }, [locations]);

  // Filtered Locations
  const filteredLocations = useMemo(() => {
    return locations.filter((loc) => {
      if (healthFilter !== 'ALL' && loc.network_health !== healthFilter) {
        return false;
      }
      return true;
    });
  }, [locations, healthFilter]);

  const handleOpenAdd = () => {
    setEditingLocation(null);
    setFormData({
      name: '',
      code: '',
      site_type: 'BRANCH',
      status: 'ACTIVE',
      region: '',
      district: '',
      address: '',
      timezone: 'Africa/Dar_es_Salaam',
      operating_hours: '',
      installation_date: '',
      external_reference: '',
      contact_person: '',
      contact_phone: '',
      latitude: '',
      longitude: '',
      notes: '',
    });
    setModalOpen(true);
  };

  const handleOpenEdit = (loc: LocationSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingLocation(loc);
    setFormData({
      name: loc.name,
      code: loc.code,
      site_type: loc.site_type,
      status: loc.status,
      region: loc.region || '',
      district: loc.district || '',
      address: loc.address || '',
      timezone: loc.timezone || 'Africa/Dar_es_Salaam',
      operating_hours: loc.operating_hours || '',
      installation_date: loc.installation_date || '',
      external_reference: loc.external_reference || '',
      contact_person: loc.contact_person || '',
      contact_phone: loc.contact_phone || '',
      latitude: loc.latitude ? String(loc.latitude) : '',
      longitude: loc.longitude ? String(loc.longitude) : '',
      notes: loc.notes || '',
    });
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyId || !formData.name.trim()) return;

    try {
      setSaving(true);
      const payload: any = {
        name: formData.name.trim(),
        site_type: formData.site_type,
        status: formData.status,
        region: formData.region.trim(),
        district: formData.district.trim(),
        address: formData.address.trim(),
        timezone: formData.timezone.trim(),
        operating_hours: formData.operating_hours.trim(),
        installation_date: formData.installation_date || null,
        external_reference: formData.external_reference.trim(),
        contact_person: formData.contact_person.trim(),
        contact_phone: formData.contact_phone.trim(),
        latitude: formData.latitude.trim() || null,
        longitude: formData.longitude.trim() || null,
        notes: formData.notes.trim(),
        company_id: companyId,
      };
      if (formData.code.trim()) {
        payload.code = formData.code.trim().toUpperCase();
      }

      if (editingLocation) {
        await locationsApi.update(editingLocation.id, payload);
        toast({ title: 'Location updated successfully', type: 'success' });
      } else {
        await locationsApi.create(payload);
        toast({ title: 'Location created successfully', type: 'success' });
      }
      setModalOpen(false);
      fetchLocations();
    } catch (err: any) {
      toast({
        title: err.response?.data?.detail || err.message || 'Failed to save location',
        type: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (loc: LocationSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      if (loc.is_active && loc.status === 'ACTIVE') {
        const res = await locationsApi.delete(loc.id, companyId);
        toast({
          title: res.detail || 'Location deactivated',
          type: res.action === 'deleted' ? 'success' : 'info',
        });
      } else {
        const res = await locationsApi.reactivate(loc.id, companyId);
        toast({ title: res.detail || 'Location reactivated', type: 'success' });
      }
      fetchLocations();
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Action failed', type: 'error' });
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <MapPin className="h-6 w-6 text-primary" />
            Locations
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage Wi-Fi deployment sites, branches, and physical network venues.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchLocations}
            disabled={loading}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
          <Button onClick={handleOpenAdd} size="sm" className="gap-1.5 text-xs">
            <Plus className="h-4 w-4" />
            <span>Add Location</span>
          </Button>
        </div>
      </div>

      {/* Top Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Locations</p>
              <p className="text-2xl font-bold text-foreground mt-1">{metrics.totalLocations}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <MapPin className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Active Sites</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{metrics.activeSites}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Online Routers</p>
              <p className="text-2xl font-bold text-foreground mt-1">{metrics.onlineRouters}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-600 dark:text-blue-400">
              <RouterIcon className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Active Users</p>
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">{metrics.activeUsers}</p>
            </div>
            <div className="h-10 w-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-600 dark:text-purple-400">
              <Users className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 bg-card p-3 rounded-xl border border-border">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search name, code, region or address..."
            className="pl-9 h-9 text-sm"
          />
        </div>

        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
          <select
            value={siteTypeFilter}
            onChange={(e) => setSiteTypeFilter(e.target.value)}
            className="h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="ALL">All Site Types</option>
            {SITE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="ALL">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
            <option value="MAINTENANCE">Maintenance</option>
          </select>

          <select
            value={healthFilter}
            onChange={(e) => setHealthFilter(e.target.value)}
            className="h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="ALL">All Health</option>
            <option value="HEALTHY">Healthy</option>
            <option value="DEGRADED">Degraded</option>
            <option value="OFFLINE">Offline</option>
            <option value="UNKNOWN">Unknown</option>
          </select>
        </div>
      </div>

      {/* Locations Presentation (Cards / Grid) */}
      {loading ? (
        <div className="py-20 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-2">
          <RefreshCw className="h-6 w-6 animate-spin text-primary" />
          <p>Loading deployment sites...</p>
        </div>
      ) : filteredLocations.length === 0 ? (
        <div className="py-16 text-center rounded-2xl border border-dashed border-border bg-card/50 p-8">
          <MapPin className="h-10 w-10 text-muted-foreground mx-auto mb-3 opacity-40" />
          <h3 className="text-base font-semibold text-foreground">No locations found</h3>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1 mb-4">
            {searchQuery || siteTypeFilter !== 'ALL' || statusFilter !== 'ALL' || healthFilter !== 'ALL'
              ? 'No sites match your active search or filter criteria.'
              : 'Add your first deployment site to organize routers and hotspots.'}
          </p>
          <Button onClick={handleOpenAdd} size="sm" className="gap-1.5 text-xs">
            <Plus className="h-4 w-4" />
            <span>Add Location</span>
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredLocations.map((loc) => (
            <div
              key={loc.id}
              onClick={() => navigate(`/locations/${loc.id}`)}
              className="group cursor-pointer rounded-xl border border-border bg-card p-5 hover:border-primary/50 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div>
                {/* Header row */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors flex items-center gap-1.5">
                      <span>{loc.name}</span>
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-muted text-muted-foreground">
                        {loc.code}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {SITE_TYPES.find((t) => t.value === loc.site_type)?.label || loc.site_type}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1.5">
                    <HealthBadge health={loc.network_health} />
                    <StatusBadge status={loc.status} />
                  </div>
                </div>

                {/* Region / Address */}
                <div className="mt-3.5 text-xs text-muted-foreground space-y-1">
                  {(loc.region || loc.district) && (
                    <p className="font-medium text-foreground flex items-center gap-1.5">
                      <MapPin className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <span>{[loc.region, loc.district].filter(Boolean).join(' · ')}</span>
                    </p>
                  )}
                  {loc.address && (
                    <p className="line-clamp-1 pl-5 text-[11px]">{loc.address}</p>
                  )}
                  {loc.operating_hours && (
                    <p className="flex items-center gap-1.5 pl-0.5 text-[11px]">
                      <Clock className="h-3 w-3 text-muted-foreground shrink-0" />
                      <span>{loc.operating_hours}</span>
                    </p>
                  )}
                </div>

                {/* Sub-resource counts */}
                <div className="mt-4 pt-3.5 border-t border-border/60 grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="bg-muted/40 rounded-lg p-2">
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground block">Routers</span>
                    <span className="text-sm font-bold text-foreground">
                      {loc.online_router_count}/{loc.router_count}
                    </span>
                  </div>
                  <div className="bg-muted/40 rounded-lg p-2">
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground block">Hotspots</span>
                    <span className="text-sm font-bold text-foreground">{loc.hotspot_count}</span>
                  </div>
                  <div className="bg-muted/40 rounded-lg p-2">
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground block">Users</span>
                    <span className="text-sm font-bold text-primary">{loc.active_session_count}</span>
                  </div>
                </div>
              </div>

              {/* Card Footer Actions */}
              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs">
                <span className="text-[11px] text-muted-foreground group-hover:text-primary transition-colors flex items-center gap-1">
                  <span>View Details</span>
                  <ChevronRight className="h-3 w-3" />
                </span>

                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleOpenEdit(loc, e)}
                    className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
                  >
                    <Edit2 className="h-3.5 w-3.5 mr-1" />
                    <span>Edit</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleToggleActive(loc, e)}
                    className={`h-7 px-2 text-xs ${
                      loc.is_active && loc.status === 'ACTIVE'
                        ? 'text-amber-600 hover:text-amber-700 dark:text-amber-400'
                        : 'text-emerald-600 hover:text-emerald-700 dark:text-emerald-400'
                    }`}
                  >
                    <PowerOff className="h-3.5 w-3.5 mr-1" />
                    <span>{loc.is_active && loc.status === 'ACTIVE' ? 'Deactivate' : 'Reactivate'}</span>
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Location Modal */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-primary" />
              <span>{editingLocation ? 'Edit Location' : 'Register New Location'}</span>
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSave} className="space-y-5 pt-2">
            {/* Section 1: General Identity */}
            <div className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
                1. Venue & Operational Identity
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">
                    Location Name *
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Kariakoo Branch, Mbezi Resort"
                    required
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">
                    Location Code (Optional)
                  </label>
                  <Input
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    placeholder="Auto-generated (e.g. LOC-KAR-001)"
                    className="text-xs h-9 font-mono uppercase"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">
                    Site Categorization *
                  </label>
                  <select
                    value={formData.site_type}
                    onChange={(e) => setFormData({ ...formData, site_type: e.target.value as SiteType })}
                    className="w-full h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {SITE_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">
                    Status *
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as LocationStatus })}
                    className="w-full h-9 text-xs px-3 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="ACTIVE">Active (Operational)</option>
                    <option value="MAINTENANCE">Maintenance</option>
                    <option value="INACTIVE">Inactive (Suspended)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Section 2: Physical & Spatial */}
            <div className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
                2. Geographic & Physical Address
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Region</label>
                  <Input
                    value={formData.region}
                    onChange={(e) => setFormData({ ...formData, region: e.target.value })}
                    placeholder="e.g. Dar es Salaam, Arusha, Mwanza"
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">District</label>
                  <Input
                    value={formData.district}
                    onChange={(e) => setFormData({ ...formData, district: e.target.value })}
                    placeholder="e.g. Ilala, Kinondoni, Nyamagana"
                    className="text-xs h-9"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="text-xs font-semibold text-foreground block mb-1">Physical Address / Landmark</label>
                  <Input
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    placeholder="e.g. Lumumba Street, Plot 42, Opposite Clocktower"
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Latitude</label>
                  <Input
                    value={formData.latitude}
                    onChange={(e) => setFormData({ ...formData, latitude: e.target.value })}
                    placeholder="e.g. -6.816667"
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Longitude</label>
                  <Input
                    value={formData.longitude}
                    onChange={(e) => setFormData({ ...formData, longitude: e.target.value })}
                    placeholder="e.g. 39.283333"
                    className="text-xs h-9 font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Section 3: Operations & Contact */}
            <div className="space-y-3">
              <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground border-b border-border pb-1">
                3. Operations & Administrative Contacts
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Operating Hours</label>
                  <Input
                    value={formData.operating_hours}
                    onChange={(e) => setFormData({ ...formData, operating_hours: e.target.value })}
                    placeholder="e.g. 08:00 - 22:00 or 24/7"
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Installation Date</label>
                  <Input
                    type="date"
                    value={formData.installation_date}
                    onChange={(e) => setFormData({ ...formData, installation_date: e.target.value })}
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Contact Person</label>
                  <Input
                    value={formData.contact_person}
                    onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                    placeholder="e.g. Site Manager, Juma Ally"
                    className="text-xs h-9"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Contact Phone</label>
                  <Input
                    value={formData.contact_phone}
                    onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                    placeholder="e.g. +255712345678"
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">External ERP/Billing Ref</label>
                  <Input
                    value={formData.external_reference}
                    onChange={(e) => setFormData({ ...formData, external_reference: e.target.value })}
                    placeholder="e.g. CUST-SITE-9801"
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Timezone</label>
                  <Input
                    value={formData.timezone}
                    onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                    placeholder="Africa/Dar_es_Salaam"
                    className="text-xs h-9 font-mono"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="text-xs font-semibold text-foreground block mb-1">Internal Notes</label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Deployment notes, key access instructions, power backup details..."
                    rows={2}
                    className="w-full text-xs p-2.5 rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>
            </div>

            <DialogFooter className="gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setModalOpen(false)}
                disabled={saving}
                className="text-xs h-9"
              >
                Cancel
              </Button>
              <Button type="submit" disabled={saving} className="text-xs h-9">
                {saving ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1" />
                ) : null}
                <span>{editingLocation ? 'Save Changes' : 'Create Location'}</span>
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};