import React, { useEffect, useState } from 'react';
import { CustomerSubscriptionSettings as SettingsType } from '../../types';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';
import { useToast } from '../../hooks/useToast';
import { Clock, Bell, RefreshCw, Save } from 'lucide-react';

export const CustomerSubscriptionSettings: React.FC = () => {
  const { selectedCompany } = useAuth();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState<SettingsType>({
    grace_period_minutes: 30,
    otp_expiry_minutes: 5,
    otp_resend_cooldown_seconds: 60,
    remind_1day_before: true,
    remind_1hour_before: true,
    remind_at_expiry: true,
    allow_self_service: true,
  });

  useEffect(() => {
    const fetchSettings = async () => {
      if (!selectedCompany) return;
      setLoading(true);
      try {
        const res = await apiClient.get<SettingsType>(
          `/api/v1/settings/subscriptions/?company_id=${selectedCompany.id}`
        );
        setSettings(res.data);
      } catch (err: any) {
        toast({ title: 'Failed to load subscription settings', type: 'error' });
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, [selectedCompany, toast]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompany) return;

    setSaving(true);
    try {
      await apiClient.put(
        `/api/v1/settings/subscriptions/?company_id=${selectedCompany.id}`,
        settings
      );
      toast({ title: 'Subscription settings saved successfully', type: 'success' });
    } catch (err: any) {
      toast({ title: err.response?.data?.detail || 'Failed to save settings', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <RefreshCw className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-6 max-w-3xl">
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex items-center gap-3 border-b border-border pb-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground">
              Grace Period & Expiration Policy
            </h2>
            <p className="text-xs text-muted-foreground">
              Configure grace periods before active physical sessions are disconnected via RFC 3576 POD.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-foreground mb-1">
              Grace Period (Minutes)
            </label>
            <input
              type="number"
              min={0}
              max={1440}
              value={settings.grace_period_minutes}
              onChange={(e) =>
                setSettings({ ...settings, grace_period_minutes: parseInt(e.target.value) || 0 })
              }
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <p className="text-[11px] text-muted-foreground mt-1">
              Extra courtesy time before live physical sessions are disconnected.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-foreground mb-1">
              OTP Resend Cooldown (Seconds)
            </label>
            <input
              type="number"
              min={10}
              max={300}
              value={settings.otp_resend_cooldown_seconds}
              onChange={(e) =>
                setSettings({ ...settings, otp_resend_cooldown_seconds: parseInt(e.target.value) || 60 })
              }
              className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <p className="text-[11px] text-muted-foreground mt-1">
              Minimum seconds a customer must wait before requesting a new SMS OTP.
            </p>
          </div>
        </div>
      </div>

      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex items-center gap-3 border-b border-border pb-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
            <Bell className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground">
              Proactive SMS Renewal Reminders
            </h2>
            <p className="text-xs text-muted-foreground">
              Notify subscribers via RafikiSMS before plan expiration to prevent unexpected dropouts.
            </p>
          </div>
        </div>

        <div className="space-y-3 pt-2">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.remind_1day_before}
              onChange={(e) => setSettings({ ...settings, remind_1day_before: e.target.checked })}
              className="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary/20"
            />
            <div>
              <span className="text-sm font-semibold text-foreground">24-Hour Expiry Reminder</span>
              <p className="text-xs text-muted-foreground">
                Sends an SMS alert 1 day before plan expiration with a quick renewal link.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.remind_1hour_before}
              onChange={(e) => setSettings({ ...settings, remind_1hour_before: e.target.checked })}
              className="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary/20"
            />
            <div>
              <span className="text-sm font-semibold text-foreground">1-Hour Expiry Reminder</span>
              <p className="text-xs text-muted-foreground">
                Sends an urgent SMS alert 60 minutes before expiration.
              </p>
            </div>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.allow_self_service}
              onChange={(e) => setSettings({ ...settings, allow_self_service: e.target.checked })}
              className="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary/20"
            />
            <div>
              <span className="text-sm font-semibold text-foreground">Enable Customer Self-Service Portal</span>
              <p className="text-xs text-muted-foreground">
                Allows customers to log into <span className="font-mono">/p/:slug/account</span> via SMS OTP.
              </p>
            </div>
          </label>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={saving}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-all shadow-sm disabled:opacity-50"
        >
          {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save Settings
        </button>
      </div>
    </form>
  );
};
