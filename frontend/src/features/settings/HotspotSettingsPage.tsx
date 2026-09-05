import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { apiClient } from '../../lib/api-client';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import {
  Wifi,
  Save,
  RefreshCw,
  Smartphone,
  ExternalLink,
  Check,
  AlertCircle,
  Lock,
  ShieldCheck,
} from 'lucide-react';
import { AntiTetheringSettings } from './AntiTetheringSettings';

interface HotspotSettingsData {
  id?: string;
  name: string;
  slug: string;
  ssid: string;
  brand_name: string;
  headline: string;
  welcome_text: string;
  primary_color: string;
  logo_url: string;
  support_phone: string;
  terms_url: string;
  privacy_url: string;
  default_language: 'EN' | 'SW';
  router_login_url: string;
  is_active: boolean;
}

export const HotspotSettingsPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.id;
  const [searchParams, setSearchParams] = useSearchParams();

  const tabParam = searchParams.get('tab');
  const [activeTab, setActiveTab] = useState<'branding' | 'anti-tethering'>(
    tabParam === 'anti-tethering' ? 'anti-tethering' : 'branding'
  );

  const handleTabChange = (tab: 'branding' | 'anti-tethering') => {
    setActiveTab(tab);
    setSearchParams(tab === 'branding' ? {} : { tab });
  };

  const [settings, setSettings] = useState<HotspotSettingsData>({
    name: 'Main Wi-Fi HotSpot',
    slug: 'main-hotspot',
    ssid: 'Company-WiFi',
    brand_name: '',
    headline: 'Welcome to High-Speed Wi-Fi',
    welcome_text: 'Enter your access voucher code below to start browsing.',
    primary_color: '#2563eb',
    logo_url: '',
    support_phone: '',
    terms_url: '',
    privacy_url: '',
    default_language: 'EN',
    router_login_url: 'http://10.5.50.1/login',
    is_active: true,
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchSettings = useCallback(async () => {
    if (!companyId) return;
    try {
      setLoading(true);
      setErrorMsg('');
      const res = await apiClient.get<HotspotSettingsData>(`/api/v1/settings/hotspot/?company_id=${companyId}`);
      if (res.data) {
        setSettings({
          name: res.data.name || '',
          slug: res.data.slug || '',
          ssid: res.data.ssid || '',
          brand_name: res.data.brand_name || '',
          headline: res.data.headline || '',
          welcome_text: res.data.welcome_text || '',
          primary_color: res.data.primary_color || '#2563eb',
          logo_url: res.data.logo_url || '',
          support_phone: res.data.support_phone || '',
          terms_url: res.data.terms_url || '',
          privacy_url: res.data.privacy_url || '',
          default_language: res.data.default_language || 'EN',
          router_login_url: res.data.router_login_url || 'http://10.5.50.1/login',
          is_active: res.data.is_active ?? true,
        });
      }
    } catch (err) {
      console.error('Failed to fetch hotspot settings', err);
      setErrorMsg('Failed to load hotspot settings.');
    } finally {
      setLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyId || saving) return;

    try {
      setSaving(true);
      setErrorMsg('');
      setSavedSuccess(false);

      await apiClient.put(`/api/v1/settings/hotspot/?company_id=${companyId}`, {
        company_id: companyId,
        ...settings,
      });

      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: unknown) {
      let msg = 'Failed to save hotspot settings.';
      if (err && typeof err === 'object' && 'response' in err) {
        const res = (err as { response?: { data?: { detail?: string } } }).response;
        msg = res?.data?.detail || msg;
      }
      setErrorMsg(msg);
    } finally {
      setSaving(false);
    }
  };

  const portalUrl = `${window.location.origin}/p/${settings.slug}`;

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Wifi className="h-6 w-6 text-primary" />
            Captive Portal & HotSpot Branding
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Customize the customer-facing Wi-Fi access experience, branding tokens, and languages.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={portalUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-border bg-card text-foreground hover:bg-muted transition-colors"
          >
            <span>Live Portal Preview</span>
            <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
          </a>
        </div>
      </div>

      {/* Subtabs: Portal Branding vs Anti-Tethering */}
      <div className="flex items-center gap-2 border-b border-border">
        <button
          type="button"
          onClick={() => handleTabChange('branding')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'branding'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Wifi className="h-4 w-4" />
          <span>Portal Branding & Appearance</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabChange('anti-tethering')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
            activeTab === 'anti-tethering'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          <span>Anti-Tethering & Router Policy</span>
        </button>
      </div>

      {activeTab === 'anti-tethering' ? (
        <AntiTetheringSettings />
      ) : loading ? (
        <div className="py-20 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-2">
          <RefreshCw className="h-6 w-6 animate-spin text-primary" />
          Loading hotspot branding configurations…
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Settings Form (7 cols) */}
          <form onSubmit={handleSave} className="lg:col-span-7 space-y-6">
            <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-5">
              <h2 className="text-sm font-bold uppercase tracking-wider text-foreground border-b border-border pb-2">
                Network & Routing Identity
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">HotSpot Name</label>
                  <Input
                    value={settings.name}
                    onChange={(e) => setSettings({ ...settings, name: e.target.value })}
                    placeholder="e.g. Kariakoo Branch HotSpot"
                    className="text-xs"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Portal URL Slug</label>
                  <Input
                    value={settings.slug}
                    onChange={(e) => setSettings({ ...settings, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                    placeholder="e.g. hotel-kariakoo"
                    className="text-xs font-mono"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Broadcast Wi-Fi SSID</label>
                  <Input
                    value={settings.ssid}
                    onChange={(e) => setSettings({ ...settings, ssid: e.target.value })}
                    placeholder="e.g. Usimamizi-WiFi-Lab"
                    className="text-xs"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Router Login Handoff URL</label>
                  <Input
                    value={settings.router_login_url}
                    onChange={(e) => setSettings({ ...settings, router_login_url: e.target.value })}
                    placeholder="http://10.5.50.1/login"
                    className="text-xs font-mono"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-5">
              <h2 className="text-sm font-bold uppercase tracking-wider text-foreground border-b border-border pb-2">
                Brand Appearance & Copy
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Brand / Business Display Name</label>
                  <Input
                    value={settings.brand_name}
                    onChange={(e) => setSettings({ ...settings, brand_name: e.target.value })}
                    placeholder="e.g. Hotel Kariakoo Guest Wi-Fi"
                    className="text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Primary Accent Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={settings.primary_color}
                      onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
                      className="w-9 h-9 p-0.5 rounded border border-border cursor-pointer bg-card"
                    />
                    <Input
                      value={settings.primary_color}
                      onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
                      className="text-xs font-mono"
                    />
                  </div>
                </div>

                <div className="sm:col-span-2 space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Portal Logo URL</label>
                  <Input
                    value={settings.logo_url}
                    onChange={(e) => setSettings({ ...settings, logo_url: e.target.value })}
                    placeholder="https://example.com/logo.png"
                    className="text-xs font-mono"
                  />
                </div>

                <div className="sm:col-span-2 space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Headline</label>
                  <Input
                    value={settings.headline}
                    onChange={(e) => setSettings({ ...settings, headline: e.target.value })}
                    placeholder="e.g. Karibu Usimamizi Wi-Fi"
                    className="text-xs"
                  />
                </div>

                <div className="sm:col-span-2 space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Welcome / Instruction Text</label>
                  <textarea
                    rows={2}
                    value={settings.welcome_text}
                    onChange={(e) => setSettings({ ...settings, welcome_text: e.target.value })}
                    placeholder="Enter your voucher code below to start browsing."
                    className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Support Phone Number</label>
                  <Input
                    value={settings.support_phone}
                    onChange={(e) => setSettings({ ...settings, support_phone: e.target.value })}
                    placeholder="+255 712 345 678"
                    className="text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Default Language</label>
                  <select
                    value={settings.default_language}
                    onChange={(e) => setSettings({ ...settings, default_language: e.target.value as 'EN' | 'SW' })}
                    className="w-full h-9 rounded-md border border-input bg-card px-3 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="EN">English (EN)</option>
                    <option value="SW">Kiswahili (SW)</option>
                  </select>
                </div>
              </div>
            </div>

            {errorMsg && (
              <div className="p-3 bg-rose-500/15 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {savedSuccess && (
              <div className="p-3 bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 rounded-lg text-xs flex items-center gap-2">
                <Check className="h-4 w-4 shrink-0" />
                <span>HotSpot branding tokens updated successfully!</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                type="submit"
                disabled={saving}
                className="flex items-center gap-1.5"
              >
                {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Save Portal Settings
              </Button>
            </div>
          </form>

          {/* Live Mobile Simulator (5 cols) */}
          <div className="lg:col-span-5 space-y-3 sticky top-6">
            <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
              <span className="font-semibold flex items-center gap-1.5">
                <Smartphone className="h-4 w-4 text-primary" />
                Live Smartphone Preview
              </span>
              <span className="font-mono text-[11px]">390px Viewport</span>
            </div>

            {/* Mock Phone Frame */}
            <div className="mx-auto w-full max-w-[340px] bg-slate-950 border-4 border-slate-800 rounded-[36px] shadow-2xl p-4 overflow-hidden text-slate-100 flex flex-col justify-between min-h-[540px]">
              {/* Phone Status Bar */}
              <div className="flex items-center justify-between text-[10px] text-slate-400 pb-3 border-b border-slate-900">
                <div className="flex items-center gap-1">
                  <Wifi className="h-3 w-3 text-emerald-400" />
                  <span className="font-medium truncate max-w-[120px]">{settings.ssid || 'Wi-Fi'}</span>
                </div>
                <div className="font-bold text-[10px] bg-slate-900 px-1.5 py-0.5 rounded text-slate-300">
                  {settings.default_language}
                </div>
              </div>

              {/* Portal Card inside Simulator */}
              <div className="my-auto bg-slate-900 border border-slate-800/80 rounded-2xl p-5 space-y-4 shadow-xl">
                <div className="text-center space-y-1.5">
                  {settings.logo_url ? (
                    <img src={settings.logo_url} alt="Logo" className="h-10 mx-auto object-contain mb-1" />
                  ) : (
                    <div
                      style={{ backgroundColor: `${settings.primary_color}20`, color: settings.primary_color }}
                      className="w-10 h-10 rounded-xl mx-auto flex items-center justify-center mb-2"
                    >
                      <Wifi className="h-5 w-5" />
                    </div>
                  )}
                  <h3 className="text-xs font-bold text-slate-100 truncate">
                    {settings.brand_name || selectedCompany?.name || 'Your Brand'}
                  </h3>
                  <p className="text-[10px] text-slate-400 leading-tight">
                    {settings.welcome_text || 'Enter voucher code to connect.'}
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="relative">
                    <Lock className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-500" />
                    <input
                      disabled
                      placeholder="XXXX-XXXX"
                      className="w-full pl-7 pr-2 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-center font-mono font-bold text-xs tracking-widest"
                    />
                  </div>

                  <button
                    type="button"
                    disabled
                    style={{ backgroundColor: settings.primary_color }}
                    className="w-full py-2 rounded-lg text-white font-bold text-xs shadow"
                  >
                    Connect Wi-Fi
                  </button>
                </div>

                {settings.support_phone && (
                  <div className="text-center text-[10px] text-slate-400 pt-1 border-t border-slate-800/60">
                    Support: <span className="text-slate-200 font-semibold">{settings.support_phone}</span>
                  </div>
                )}
              </div>

              {/* Phone Home Bar */}
              <div className="pt-2 text-center text-[9px] text-slate-600">
                Powered by Usimamizi Wi-Fi
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
