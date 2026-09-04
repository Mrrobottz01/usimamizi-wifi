import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch } from '../../lib/api-client';
import { PaymentSettings } from '../../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Select } from '../../components/ui/select';
import { AlertCircle, CheckCircle2, CreditCard, Key, Shield, RefreshCw } from 'lucide-react';

export function PaymentProviderSettings() {
  const { selectedCompany } = useAuth();
  const [config, setConfig] = useState<PaymentSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form input states
  const [isEnabled, setIsEnabled] = useState(true);
  const [environment, setEnvironment] = useState<'sandbox' | 'live'>('sandbox');
  const [apiBaseUrl, setApiBaseUrl] = useState('https://api.snippe.sh');
  const [apiKey, setApiKey] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');

  useEffect(() => {
    async function fetchConfig() {
      if (!selectedCompany) return;
      try {
        setLoading(true);
        setError(null);
        const data = await apiFetch<PaymentSettings>(`/payments/settings/?company_id=${selectedCompany.id}`);
        setConfig(data);
        setIsEnabled(data.is_enabled);
        setEnvironment(data.environment);
        setApiBaseUrl(data.api_base_url || 'https://api.snippe.sh');
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    fetchConfig();
  }, [selectedCompany]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompany) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      const payload: Record<string, unknown> = {
        company_id: selectedCompany.id,
        is_enabled: isEnabled,
        environment,
        api_base_url: apiBaseUrl,
      };
      if (apiKey.trim()) payload.api_key = apiKey.trim();
      if (webhookSecret.trim()) payload.webhook_secret = webhookSecret.trim();

      const updated = await apiFetch<PaymentSettings>(`/payments/settings/?company_id=${selectedCompany.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });

      setConfig(updated);
      setApiKey('');
      setWebhookSecret('');
      setSuccess(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-muted-foreground">
        <RefreshCw className="h-6 w-6 animate-spin mr-2" />
        <span>Loading Snippe payment settings…</span>
      </div>
    );
  }

  return (
    <Card className="border-border shadow-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500 border border-blue-500/20">
              <CreditCard className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Snippe Mobile Money Gateway</CardTitle>
              <CardDescription>
                Configure credentials for customer self-service internet purchases via M-Pesa, Airtel, Yas, and HaloPesa.
              </CardDescription>
            </div>
          </div>
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${
              environment === 'live' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
            }`}
          >
            {environment}
          </span>
        </div>
      </CardHeader>

      <form onSubmit={handleSave}>
        <CardContent className="space-y-6">
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg flex items-center gap-2 text-sm text-emerald-600">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>Snippe payment configuration saved successfully!</span>
            </div>
          )}

          <div className="flex items-center justify-between p-4 border rounded-xl bg-card">
            <div className="space-y-0.5">
              <label className="font-semibold text-sm text-foreground block">Enable Mobile Money Payments</label>
              <p className="text-xs text-muted-foreground">
                When enabled, captive portal visitors can purchase Wi-Fi packages directly with mobile money.
              </p>
            </div>
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={(e) => setIsEnabled(e.target.checked)}
              className="h-5 w-5 rounded border-input text-primary focus:ring-primary"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Environment Mode</label>
              <Select
                value={environment}
                onChange={(e) => setEnvironment(e.target.value as 'sandbox' | 'live')}
                className="h-10 text-sm"
              >
                <option value="sandbox">Sandbox (Testing)</option>
                <option value="live">Live (Production)</option>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">API Base URL</label>
              <Input
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
                placeholder="https://api.snippe.sh"
                className="h-10"
              />
            </div>
          </div>

          <div className="space-y-4 pt-2 border-t">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
                  <Key className="h-4 w-4 text-muted-foreground" />
                  <span>Snippe API Key</span>
                </label>
                <span className="text-xs font-mono text-muted-foreground">
                  Current: {config?.api_key_masked || 'None'}
                </span>
              </div>
              <Input
                type="password"
                placeholder="Enter new API key to update (leave blank to keep existing)"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <span>Webhook Signing Secret</span>
                </label>
                <span className="text-xs font-mono text-muted-foreground">
                  Current: {config?.webhook_secret_masked || 'None'}
                </span>
              </div>
              <Input
                type="password"
                placeholder="Enter new Webhook secret to update (leave blank to keep existing)"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
              />
              <p className="text-[11px] text-muted-foreground">
                In your Snippe Dashboard, set the Webhook URL to: <code className="bg-muted px-1 py-0.5 rounded font-mono text-foreground">https://your-domain/api/v1/payments/snippe/webhook/</code>
              </p>
            </div>
          </div>
        </CardContent>

        <CardFooter className="flex justify-end border-t pt-4">
          <Button type="submit" disabled={saving}>
            {saving ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                <span>Saving…</span>
              </>
            ) : (
              'Save Payment Settings'
            )}
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
}
