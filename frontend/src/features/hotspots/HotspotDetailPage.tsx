import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Wifi,
  ArrowLeft,
  Settings,
  Shield,
  Palette,
  Layers,
  Radio,
  ExternalLink,
  Users,
  CheckCircle2,
  XCircle,
  Star,
  RefreshCw,
  MapPin,
  Server,
  Globe,
  Smartphone,
  Save,
  Info,
  Check,
  AlertCircle
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { hotspotsApi, locationsApi } from '../../lib/infrastructure-api';
import { HotspotDetail, LocationSessionSummary } from '../../types';
import { AntiTetheringSettings } from '../settings/AntiTetheringSettings';

export const HotspotDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [hotspot, setHotspot] = useState<HotspotDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'branding' | 'plans' | 'anti-tethering' | 'sessions'>('overview');

  // Action status
  const [settingDefault, setSettingDefault] = useState(false);
  const [togglingActive, setTogglingActive] = useState(false);

  // Branding Form State
  const [brandName, setBrandName] = useState('');
  const [portalTitle, setPortalTitle] = useState('');
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const [primaryColor, setPrimaryColor] = useState('#2563EB');
  const [logoUrl, setLogoUrl] = useState('');
  const [supportPhone, setSupportPhone] = useState('');
  const [routerLoginUrl, setRouterLoginUrl] = useState('');
  const [savingBranding, setSavingBranding] = useState(false);
  const [brandingSuccess, setBrandingSuccess] = useState(false);

  // Plans Tab State
  const [allPlans, setAllPlans] = useState<any[]>([]);
  const [assignedPlanIds, setAssignedPlanIds] = useState<string[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(false);
  const [savingPlans, setSavingPlans] = useState(false);
  const [plansSuccess, setPlansSuccess] = useState(false);

  // Sessions Tab State
  const [sessions, setSessions] = useState<LocationSessionSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  const fetchHotspot = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await hotspotsApi.get(id);
      setHotspot(data);

      // Initialize branding form
      setBrandName(data.brand_name || '');
      setPortalTitle(data.portal_title || data.headline || '');
      setWelcomeMessage(data.welcome_message || data.welcome_text || '');
      setPrimaryColor(data.primary_color || '#2563EB');
      setLogoUrl(data.logo_url || '');
      setSupportPhone(data.support_phone || '');
      setRouterLoginUrl(data.router_login_url || '');
    } catch (err: any) {
      setError(err.message || 'Failed to load hotspot details.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchHotspot();
  }, [fetchHotspot]);

  // Load plans when Plans tab opened
  const loadPlans = useCallback(async () => {
    if (!id) return;
    try {
      setLoadingPlans(true);
      const data = await hotspotsApi.getPlans(id);
      setAllPlans(data.plans || []);
      setAssignedPlanIds(data.assigned_plan_ids || []);
    } catch (err) {
      console.error('Failed to load hotspot plans', err);
    } finally {
      setLoadingPlans(false);
    }
  }, [id]);

  // Load sessions when Sessions tab opened
  const loadSessions = useCallback(async () => {
    if (!hotspot?.location?.id) return;
    try {
      setLoadingSessions(true);
      const allSessions = await locationsApi.getSessions(hotspot.location.id);
      // Filter sessions for this hotspot
      const filtered = allSessions.filter((s) => s.hotspot_id === hotspot.id);
      setSessions(filtered.length > 0 ? filtered : allSessions);
    } catch (err) {
      console.error('Failed to load hotspot sessions', err);
    } finally {
      setLoadingSessions(false);
    }
  }, [hotspot?.location?.id, hotspot?.id]);

  useEffect(() => {
    if (activeTab === 'plans') {
      loadPlans();
    } else if (activeTab === 'sessions') {
      loadSessions();
    }
  }, [activeTab, loadPlans, loadSessions]);

  const handleSetDefault = async () => {
    if (!hotspot) return;
    try {
      setSettingDefault(true);
      await hotspotsApi.setDefault(hotspot.id);
      await fetchHotspot();
    } catch (err: any) {
      alert(err.message || 'Failed to set as default');
    } finally {
      setSettingDefault(false);
    }
  };

  const handleToggleActive = async () => {
    if (!hotspot) return;
    try {
      setTogglingActive(true);
      await hotspotsApi.update(hotspot.id, { is_active: !hotspot.is_active });
      await fetchHotspot();
    } catch (err: any) {
      alert(err.message || 'Failed to update status');
    } finally {
      setTogglingActive(false);
    }
  };

  const handleSaveBranding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hotspot) return;
    try {
      setSavingBranding(true);
      setBrandingSuccess(false);
      await hotspotsApi.update(hotspot.id, {
        brand_name: brandName,
        portal_title: portalTitle,
        welcome_message: welcomeMessage,
        primary_color: primaryColor,
        logo_url: logoUrl,
        support_phone: supportPhone,
        router_login_url: routerLoginUrl,
      });
      setBrandingSuccess(true);
      setTimeout(() => setBrandingSuccess(false), 3000);
      await fetchHotspot();
    } catch (err: any) {
      alert(err.message || 'Failed to update branding');
    } finally {
      setSavingBranding(false);
    }
  };

  const handleTogglePlan = (planId: string) => {
    setAssignedPlanIds((prev) =>
      prev.includes(planId) ? prev.filter((pid) => pid !== planId) : [...prev, planId]
    );
  };

  const handleSavePlans = async () => {
    if (!hotspot) return;
    try {
      setSavingPlans(true);
      setPlansSuccess(false);
      await hotspotsApi.updatePlans(hotspot.id, assignedPlanIds);
      setPlansSuccess(true);
      setTimeout(() => setPlansSuccess(false), 3000);
    } catch (err: any) {
      alert(err.message || 'Failed to save assigned plans');
    } finally {
      setSavingPlans(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-gray-500">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mb-3" />
        <p className="text-sm font-medium">Loading hotspot details...</p>
      </div>
    );
  }

  if (error || !hotspot) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 rounded-xl p-6 text-center">
          <AlertCircle className="w-10 h-10 text-red-600 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-1">Hotspot Not Found</h2>
          <p className="text-sm text-red-700 dark:text-red-400 mb-4">{error || 'The requested hotspot could not be found.'}</p>
          <Button onClick={() => navigate('/hotspots')} variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Hotspots
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/hotspots')}
            className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <div className="h-4 w-px bg-gray-300 dark:bg-gray-700" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
                {hotspot.name}
              </h1>
              {hotspot.is_default && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800 dark:bg-blue-950/70 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                  <Star className="w-3 h-3 fill-blue-600 text-blue-600" /> DEFAULT PROFILE
                </span>
              )}
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                hotspot.is_active ? 'bg-green-100 text-green-800 dark:bg-green-950/60 dark:text-green-300' : 'bg-gray-100 text-gray-700'
              }`}>
                {hotspot.is_active ? <><CheckCircle2 className="w-3 h-3" /> Active</> : <><XCircle className="w-3 h-3" /> Disabled</>}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span className="flex items-center gap-1">
                <Radio className="w-3.5 h-3.5 text-blue-500" />
                SSID: <strong className="text-gray-800 dark:text-gray-200">{hotspot.ssid}</strong>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-blue-500" />
                Location:
                {hotspot.location ? (
                  <Link to={`/locations/${hotspot.location.id}`} className="font-medium text-blue-600 dark:text-blue-400 hover:underline ml-1">
                    {hotspot.location.name}
                  </Link>
                ) : (
                  <span className="text-gray-400 ml-1">Unassigned</span>
                )}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Server className="w-3.5 h-3.5 text-gray-500" />
                Router:
                {hotspot.router ? (
                  <Link to={`/routers/${hotspot.router.id}`} className="font-mono text-gray-700 dark:text-gray-300 hover:underline ml-1">
                    {hotspot.router.name}
                  </Link>
                ) : (
                  <span className="text-gray-400 ml-1">No gateway</span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {!hotspot.is_default && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSetDefault}
              disabled={settingDefault}
              className="h-9"
            >
              <Star className="w-4 h-4 mr-1.5 text-amber-500" />
              {settingDefault ? 'Setting...' : 'Set as Default'}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleToggleActive}
            disabled={togglingActive}
            className="h-9"
          >
            {hotspot.is_active ? 'Deactivate Hotspot' : 'Activate Hotspot'}
          </Button>
          <a
            href={`/portal/${hotspot.slug}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center h-9 px-3 text-xs font-semibold rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5 mr-1" /> Open Live Portal
          </a>
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="border-b border-gray-200 dark:border-gray-800">
        <nav className="flex space-x-6 overflow-x-auto" aria-label="Tabs">
          {[
            { id: 'overview', label: 'Overview & Network', icon: Settings },
            { id: 'branding', label: 'Portal & Branding', icon: Palette },
            { id: 'plans', label: 'Plan Assignments', icon: Layers },
            { id: 'anti-tethering', label: 'Anti-Tethering Policy', icon: Shield },
            { id: 'sessions', label: `Active Sessions (${hotspot.active_sessions_count || hotspot.active_users_count || 0})`, icon: Users },
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

      {/* TAB: OVERVIEW & NETWORK */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Network Parameters */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
                <Globe className="w-4 h-4 text-blue-600" /> HotSpot Network Profile
              </h3>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-y-3 gap-x-4 text-sm font-mono">
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 font-sans uppercase">Broadcast SSID</dt>
                  <dd className="font-bold text-gray-900 dark:text-white mt-0.5">{hotspot.ssid}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 font-sans uppercase">Portal Slug</dt>
                  <dd className="text-blue-600 dark:text-blue-400 mt-0.5">/portal/{hotspot.slug}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 font-sans uppercase">Router Interface</dt>
                  <dd className="text-gray-900 dark:text-white mt-0.5">{hotspot.interface || hotspot.interface_name}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 font-sans uppercase">Gateway IP</dt>
                  <dd className="text-gray-900 dark:text-white mt-0.5">{hotspot.gateway_ip}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 font-sans uppercase">Subnet Mask</dt>
                  <dd className="text-gray-900 dark:text-white mt-0.5">{hotspot.subnet_mask}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 font-sans uppercase">Router Login URL</dt>
                  <dd className="text-gray-700 dark:text-gray-300 mt-0.5 truncate">{hotspot.router_login_url || 'Not set'}</dd>
                </div>
              </dl>
            </div>

            {/* Infrastructure Hierarchy Card */}
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2 border-b border-gray-100 dark:border-gray-800 pb-3">
                <MapPin className="w-4 h-4 text-indigo-600" /> Infrastructure Attachment
              </h3>
              <dl className="grid grid-cols-1 gap-y-3 text-sm">
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Operating Location</dt>
                  <dd className="mt-0.5">
                    {hotspot.location ? (
                      <Link
                        to={`/locations/${hotspot.location.id}`}
                        className="text-blue-600 dark:text-blue-400 font-medium hover:underline inline-flex items-center gap-1"
                      >
                        {hotspot.location.name} <ExternalLink className="w-3 h-3" />
                      </Link>
                    ) : (
                      <span className="text-gray-400">Unassigned</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Gateway Router</dt>
                  <dd className="mt-0.5">
                    {hotspot.router ? (
                      <Link
                        to={`/routers/${hotspot.router.id}`}
                        className="text-blue-600 dark:text-blue-400 font-mono font-medium hover:underline inline-flex items-center gap-1"
                      >
                        {hotspot.router.name} ({hotspot.router.management_ip}) <ExternalLink className="w-3 h-3" />
                      </Link>
                    ) : (
                      <span className="text-gray-400">No gateway router</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Scope & Fallback</dt>
                  <dd className="text-gray-700 dark:text-gray-300 mt-0.5">
                    {hotspot.is_default
                      ? 'Designated as primary fallback hotspot for captive portal clients on this company.'
                      : 'Dedicated hotspot profile attached to this router interface.'}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}

      {/* TAB: PORTAL & BRANDING */}
      {activeTab === 'branding' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Branding Form */}
          <div className="lg:col-span-7 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm space-y-4">
            <div className="border-b border-gray-100 dark:border-gray-800 pb-3 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-white">
                  Captive Portal Customization
                </h3>
                <p className="text-xs text-gray-500">
                  Configure brand identity, colors, and welcome messaging presented to guests connecting to this hotspot.
                </p>
              </div>
              {brandingSuccess && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 bg-green-50 px-2.5 py-1 rounded-full border border-green-200">
                  <Check className="w-3 h-3" /> Saved
                </span>
              )}
            </div>

            <form onSubmit={handleSaveBranding} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Brand Name *
                  </label>
                  <input
                    type="text"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    required
                    placeholder="e.g. Kariakoo HighSpeed Wi-Fi"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Portal Headline / Title
                  </label>
                  <input
                    type="text"
                    value={portalTitle}
                    onChange={(e) => setPortalTitle(e.target.value)}
                    placeholder="e.g. Welcome to High-Speed Internet"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Welcome Message
                </label>
                <textarea
                  rows={2}
                  value={welcomeMessage}
                  onChange={(e) => setWelcomeMessage(e.target.value)}
                  placeholder="Select an internet pass or enter your voucher to get connected immediately."
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Primary Accent Color
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="color"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-10 h-10 rounded border border-gray-300 p-0.5 cursor-pointer"
                    />
                    <input
                      type="text"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-28 px-3 py-2 text-sm font-mono rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                    Support Phone Number
                  </label>
                  <input
                    type="text"
                    value={supportPhone}
                    onChange={(e) => setSupportPhone(e.target.value)}
                    placeholder="+255 7XX XXX XXX"
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  Logo URL (Optional)
                </label>
                <input
                  type="url"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://yourdomain.com/logo.png"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  RouterOS Login URL
                </label>
                <input
                  type="text"
                  value={routerLoginUrl}
                  onChange={(e) => setRouterLoginUrl(e.target.value)}
                  placeholder="http://10.5.50.1/login"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono"
                />
                <p className="text-[11px] text-gray-400 mt-1">Form action where captive portal credentials are submitted on login.</p>
              </div>

              <div className="pt-3 border-t border-gray-100 dark:border-gray-800 flex justify-end">
                <Button
                  type="submit"
                  disabled={savingBranding}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Save className="w-4 h-4 mr-1.5" />
                  {savingBranding ? 'Saving...' : 'Save Portal Branding'}
                </Button>
              </div>
            </form>
          </div>

          {/* Right: Live Mobile Preview */}
          <div className="lg:col-span-5 flex flex-col items-center">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Smartphone className="w-4 h-4" /> Guest Mobile Portal Preview
            </div>
            {/* Mobile Device Mockup */}
            <div className="w-[320px] rounded-[36px] border-4 border-gray-800 dark:border-gray-700 bg-white dark:bg-gray-950 p-4 shadow-2xl overflow-hidden relative min-h-[520px] flex flex-col justify-between">
              {/* Device Notch */}
              <div className="w-24 h-4 bg-gray-800 dark:bg-gray-700 rounded-full mx-auto mb-4" />

              {/* Portal Content Mockup */}
              <div className="space-y-4 text-center">
                {logoUrl ? (
                  <img src={logoUrl} alt="Logo" className="h-10 mx-auto object-contain" />
                ) : (
                  <div
                    className="w-12 h-12 rounded-2xl mx-auto flex items-center justify-center text-white shadow-md"
                    style={{ backgroundColor: primaryColor }}
                  >
                    <Wifi className="w-6 h-6" />
                  </div>
                )}

                <div>
                  <h4 className="font-bold text-gray-900 dark:text-white text-base">
                    {brandName || 'Hotspot Portal'}
                  </h4>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {portalTitle || 'Connect to Internet'}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-gray-50 dark:bg-gray-900 border border-gray-100 dark:border-gray-800 text-[11px] text-gray-600 dark:text-gray-300">
                  {welcomeMessage || 'Select your plan below or enter a voucher.'}
                </div>

                <div className="space-y-2">
                  <div
                    className="w-full py-2.5 rounded-xl text-white text-xs font-bold shadow-sm"
                    style={{ backgroundColor: primaryColor }}
                  >
                    Buy Internet Pass
                  </div>
                  <div className="w-full py-2 rounded-xl text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-800 text-xs font-semibold bg-white dark:bg-gray-900">
                    Use Voucher Code
                  </div>
                </div>

                <div className="text-[10px] text-gray-400 font-mono">
                  SSID: {hotspot.ssid}
                </div>
              </div>

              {/* Mobile Footer */}
              <div className="text-[10px] text-gray-400 text-center pt-4 border-t border-gray-100 dark:border-gray-900">
                {supportPhone ? `Support: ${supportPhone}` : 'Powered by Usimamizi Wi-Fi'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB: PLAN ASSIGNMENTS */}
      {activeTab === 'plans' && (
        <div className="space-y-6">
          <div className="bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/40 rounded-xl p-4 flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
            <div className="text-xs text-blue-800 dark:text-blue-300">
              <p className="font-bold text-sm mb-0.5">Hotspot Plan Inheritance Rule</p>
              <p>
                When <strong>no specific plans</strong> are selected, all active billing plans created under your company are automatically available to customers at this hotspot. If you check specific plans, only those assigned plans will be offered on the captive portal.
              </p>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 dark:border-gray-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-white">
                  Assigned Plans ({assignedPlanIds.length} of {allPlans.length} selected)
                </h3>
                <p className="text-xs text-gray-500">
                  {assignedPlanIds.length === 0
                    ? 'Currently inheriting ALL active company plans.'
                    : `Restricted to ${assignedPlanIds.length} designated plans.`}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setAssignedPlanIds([])}
                  className="text-xs h-8"
                >
                  Clear Selection (Inherit All)
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setAssignedPlanIds(allPlans.map((p) => p.id))}
                  className="text-xs h-8"
                >
                  Select All
                </Button>
                <Button
                  size="sm"
                  onClick={handleSavePlans}
                  disabled={savingPlans}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs h-8"
                >
                  {savingPlans ? 'Saving...' : 'Save Plan Assignments'}
                </Button>
              </div>
            </div>

            {plansSuccess && (
              <div className="p-3 rounded-lg bg-green-50 text-green-800 border border-green-200 text-xs font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" /> Plan assignments saved successfully.
              </div>
            )}

            {loadingPlans ? (
              <div className="py-8 text-center text-gray-500">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
                <p className="text-xs">Loading available plans...</p>
              </div>
            ) : allPlans.length === 0 ? (
              <div className="py-8 text-center text-gray-500">
                <p className="text-sm font-semibold">No Commercial Plans Available</p>
                <p className="text-xs mt-1">Create internet plans under Billing & Access &gt; Plans first.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
                {allPlans.map((plan) => {
                  const isChecked = assignedPlanIds.includes(plan.id);
                  return (
                    <div
                      key={plan.id}
                      onClick={() => handleTogglePlan(plan.id)}
                      className={`p-4 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                        isChecked
                          ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-950/30'
                          : 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-gray-900 dark:text-white text-sm">{plan.name}</h4>
                          <span className="font-bold text-blue-600 dark:text-blue-400 text-xs">
                            {plan.price} {plan.currency || 'TZS'}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Duration: {plan.duration_minutes ? `${plan.duration_minutes} mins` : 'Unlimited'}
                          {plan.data_limit_mb ? ` • ${plan.data_limit_mb} MB` : ''}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB: ANTI-TETHERING POLICY */}
      {activeTab === 'anti-tethering' && (
        <div className="space-y-4">
          <div className="bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-900/40 rounded-xl p-4 text-xs text-purple-800 dark:text-purple-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-600 shrink-0" />
              <span>
                Managing anti-tethering rules, TTL enforcement, and client sharing detection specifically for hotspot <strong>{hotspot.name}</strong>.
              </span>
            </div>
          </div>
          <AntiTetheringSettings hotspotId={hotspot.id} />
        </div>
      )}

      {/* TAB: ACTIVE SESSIONS */}
      {activeTab === 'sessions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-gray-900 dark:text-white">
              Active Sessions on this Hotspot
            </h3>
            <Button size="sm" variant="outline" onClick={loadSessions} className="text-xs">
              <RefreshCw className="w-3.5 h-3.5 mr-1" /> Refresh Sessions
            </Button>
          </div>

          {loadingSessions ? (
            <div className="py-12 text-center text-gray-500">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
              <p className="text-xs">Loading sessions...</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-8 text-center bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
              <Users className="w-10 h-10 text-gray-400 mx-auto mb-2 opacity-50" />
              <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">No Active Sessions</p>
              <p className="text-xs text-gray-500 mt-1">There are currently no authenticated subscribers browsing on this hotspot.</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden shadow-sm">
              <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                <thead className="bg-gray-50 dark:bg-gray-800/60 text-xs uppercase font-semibold text-gray-500 border-b border-gray-200 dark:border-gray-800">
                  <tr>
                    <th className="px-4 py-3">User / Phone</th>
                    <th className="px-4 py-3">Device & IP</th>
                    <th className="px-4 py-3">Plan</th>
                    <th className="px-4 py-3">Data Used</th>
                    <th className="px-4 py-3">Started</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {sessions.map((s) => (
                    <tr key={s.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                      <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                        {s.username}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5 font-medium text-gray-900 dark:text-white">
                          <Smartphone className="h-3.5 w-3.5 text-primary shrink-0" />
                          <span className="font-semibold text-xs">{s.device_name || 'Generic Device'}</span>
                        </div>
                        <div className="font-mono text-[11px] text-gray-500 mt-0.5">
                          {s.ip_address || s.client_ip} • {s.mac_address || s.client_mac}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs">{s.plan_name || 'Standard'}</td>
                      <td className="px-4 py-3 text-xs font-mono">
                        {Math.round(((s.bytes_in || 0) + (s.bytes_out || 0)) / 1024 / 1024)} MB
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {s.start_time ? new Date(s.start_time).toLocaleTimeString() : 'Active'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
