import { useCallback, useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Select } from '../../components/ui/select';
import { Checkbox } from '../../components/ui/checkbox';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { MessageSquare, Mail, Send, CheckCircle2, XCircle, RefreshCw, Radio } from 'lucide-react';
import { Alert } from '../../components/ui/alert';
import { apiClient } from '../../lib/api-client';
import { useAuth } from '../../hooks/useAuth';
import { ApiError, NotificationProviderConfig } from '../../types';

export function NotificationsSettings() {
  const { selectedCompany } = useAuth();
  const [providers, setProviders] = useState<NotificationProviderConfig[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  const [selectedProviderCode, setSelectedProviderCode] = useState<string>('');
  const [selectedSenderId, setSelectedSenderId] = useState<string>('');
  const [testPhone, setTestPhone] = useState('');
  const [testSending, setTestSending] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; details?: string } | null>(null);

  const fetchProviders = useCallback(async () => {
    if (!selectedCompany) return;
    setLoadingProviders(true);
    try {
      const res = await apiClient.get<NotificationProviderConfig[]>(
        `/api/v1/settings/notifications/?company_id=${selectedCompany.id}`
      );
      setProviders(res.data);
    } catch {
      // Fallback silently if company not selected yet
    } finally {
      setLoadingProviders(false);
    }
  }, [selectedCompany]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleToggleActive = async (provider: NotificationProviderConfig) => {
    if (!selectedCompany) return;
    setUpdatingId(provider.id);
    try {
      await apiClient.patch('/api/v1/settings/notifications/', {
        company_id: selectedCompany.id,
        id: provider.id,
        is_active: !provider.is_active,
      });
      await fetchProviders();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      alert(apiErr?.detail || 'Failed to update provider status.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleSetPrimary = async (provider: NotificationProviderConfig) => {
    if (!selectedCompany) return;
    setUpdatingId(provider.id);
    try {
      await apiClient.patch('/api/v1/settings/notifications/', {
        company_id: selectedCompany.id,
        id: provider.id,
        priority: 1,
        is_active: true,
      });
      // Adjust other providers priority upwards
      for (const p of providers) {
        if (p.id !== provider.id && p.priority <= 1) {
          await apiClient.patch('/api/v1/settings/notifications/', {
            company_id: selectedCompany.id,
            id: p.id,
            priority: 2,
          });
        }
      }
      await fetchProviders();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      alert(apiErr?.detail || 'Failed to set primary provider.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleSyncSenderIds = async (provider: NotificationProviderConfig) => {
    if (!selectedCompany) return;
    setSyncingId(provider.id);
    try {
      const res = await apiClient.post<{ message: string; sender_ids: unknown[]; default_sender_id: string }>(
        `/api/v1/settings/notifications/sms/providers/${provider.id}/sync-sender-ids/`,
        { company_id: selectedCompany.id }
      );
      alert(res.data.message);
      await fetchProviders();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      alert(apiErr?.detail || 'Failed to sync sender IDs.');
    } finally {
      setSyncingId(null);
    }
  };

  const handleSetDefaultSender = async (provider: NotificationProviderConfig, senderId: string) => {
    if (!selectedCompany) return;
    setUpdatingId(provider.id);
    try {
      await apiClient.patch(`/api/v1/settings/notifications/sms/providers/${provider.id}/default-sender/`, {
        company_id: selectedCompany.id,
        sender_id: senderId,
      });
      await fetchProviders();
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      alert(apiErr?.detail || 'Failed to set default sender ID.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleSendTestSMS = async () => {
    if (!selectedCompany || !testPhone) return;

    setTestSending(true);
    setTestResult(null);

    try {
      const res = await apiClient.post<{
        status: string;
        recipient: string;
        attempts?: { provider_code: string; sender_id?: string; status: string; provider_status?: string; failure_reason?: string; failure_category?: string }[];
      }>(
        '/api/v1/settings/notifications/test-sms/',
        {
          company_id: selectedCompany.id,
          recipient_phone: testPhone,
          provider_code: selectedProviderCode || undefined,
          sender_id: selectedSenderId || undefined,
          message_text: 'Usimamizi Wi-Fi: Test SMS delivery verified successfully!',
        }
      );

      const attempts = res.data.attempts || [];
      const lastAttempt = attempts[attempts.length - 1];

      if (res.data.status === 'SENT' || res.data.status === 'DELIVERED') {
        setTestResult({
          success: true,
          message: `Test SMS sent successfully to ${res.data.recipient}!`,
          details: lastAttempt ? `Delivered via ${lastAttempt.provider_code} (Sender: ${lastAttempt.sender_id || 'DEFAULT'}, Status: ${lastAttempt.provider_status || 'QUEUED'})` : undefined,
        });
      } else {
        setTestResult({
          success: false,
          message: `Test SMS delivery failed. Status: ${res.data.status}`,
          details: lastAttempt ? `Provider: ${lastAttempt.provider_code}, Sender: ${lastAttempt.sender_id || 'N/A'}, Reason: ${lastAttempt.failure_reason || lastAttempt.failure_category}` : undefined,
        });
      }
    } catch (err: unknown) {
      const apiErr = err as ApiError;
      setTestResult({ success: false, message: apiErr?.detail || 'Failed to trigger test SMS.' });
    } finally {
      setTestSending(false);
    }
  };

  // Find active available senders for currently selected provider in Test SMS
  const activeTargetProvider = providers.find((p) => p.code === selectedProviderCode);
  const targetSenderList = activeTargetProvider?.available_sender_ids?.filter((s) => s.is_available) || [];

  return (
    <div className="space-y-6">
      <Alert variant="info" title="Multi-Provider SMS Engine & Sender ID Architecture">
        Dynamic Sender ID discovery is supported for <strong>RafikiSMS</strong>. Click <strong>Sync Sender IDs</strong> to retrieve approved brand sender names from your provider account.
      </Alert>

      {/* 1. Multi-Provider Gateway Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <MessageSquare className="h-5 w-5" />
              </div>
              <div>
                <CardTitle>Active SMS Providers & Sender IDs</CardTitle>
                <CardDescription>Configure routing priority, toggle gateway status, and sync approved sender IDs.</CardDescription>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={fetchProviders} disabled={loadingProviders}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loadingProviders ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            {providers.map((p) => {
              const isPrimary = p.priority === 1 && p.is_active;
              const availableSenders = p.available_sender_ids?.filter((s) => s.is_available) || [];

              return (
                <div
                  key={p.id}
                  className={`rounded-lg border p-4 transition ${
                    p.is_active
                      ? 'border-emerald-200 bg-emerald-50/20 dark:border-emerald-900/40 dark:bg-emerald-950/10'
                      : 'border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/30 opacity-75'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-foreground">{p.name}</span>
                        {isPrimary ? (
                          <Badge variant="success">Priority {p.priority} (Primary)</Badge>
                        ) : p.is_active ? (
                          <Badge variant="outline">Priority {p.priority} (Failover)</Badge>
                        ) : (
                          <Badge variant="secondary">Disabled</Badge>
                        )}
                        {p.default_sender_id && (
                          <Badge variant="secondary">Default Sender: {p.default_sender_id}</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Endpoint: <code className="font-mono text-[11px]">{p.base_url || 'https://api.rafikisms.com'}</code>
                        {p.last_sender_sync_at && (
                          <span className="ml-2">| Last Sender Sync: {new Date(p.last_sender_sync_at).toLocaleTimeString()}</span>
                        )}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSyncSenderIds(p)}
                        disabled={syncingId === p.id}
                        title="Query provider for available sender IDs"
                      >
                        <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${syncingId === p.id ? 'animate-spin' : ''}`} />
                        {syncingId === p.id ? 'Syncing...' : 'Sync Senders'}
                      </Button>

                      {!isPrimary && p.is_active && (
                        <button
                          onClick={() => handleSetPrimary(p)}
                          disabled={updatingId === p.id}
                          className="text-xs font-semibold text-primary hover:underline px-2"
                        >
                          Set Primary
                        </button>
                      )}

                      <button
                        onClick={() => handleToggleActive(p)}
                        disabled={updatingId === p.id}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                          p.is_active
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800 hover:bg-emerald-200'
                            : 'bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 hover:bg-slate-200'
                        }`}
                      >
                        {p.is_active ? (
                          <>
                            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" /> Active
                          </>
                        ) : (
                          <>
                            <XCircle className="h-3.5 w-3.5 text-slate-500" /> Inactive
                          </>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Sender ID Selector Dropdown */}
                  {availableSenders.length > 0 && (
                    <div className="pt-2 border-t border-border/60 flex items-center gap-3">
                      <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                        <Radio className="h-3.5 w-3.5" /> Select Default Sender:
                      </span>
                      <select
                        value={p.default_sender_id || p.sender_id || ''}
                        onChange={(e) => handleSetDefaultSender(p, e.target.value)}
                        disabled={updatingId === p.id}
                        className="rounded-md border border-border bg-background px-2.5 py-1 text-xs font-semibold text-foreground max-w-xs"
                      >
                        {availableSenders.map((s) => (
                          <option key={s.id} value={s.sender_id}>
                            {s.sender_id} ({s.status}) {s.is_default ? '★ Default' : ''}
                          </option>
                        ))}
                      </select>
                      <span className="text-[11px] text-muted-foreground">({availableSenders.length} approved senders discovered)</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Test SMS Component */}
          <div className="pt-4 border-t border-border space-y-3">
            <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider">Test SMS Provider Integration</h4>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Target Provider</label>
                <select
                  value={selectedProviderCode}
                  onChange={(e) => {
                    setSelectedProviderCode(e.target.value);
                    setSelectedSenderId('');
                  }}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  <option value="">Auto (Active Priority)</option>
                  {providers.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.name} {p.is_active ? '(Active)' : '(Inactive)'}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Sender ID</label>
                <select
                  value={selectedSenderId}
                  onChange={(e) => setSelectedSenderId(e.target.value)}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
                >
                  <option value="">Auto (Provider Default)</option>
                  {targetSenderList.map((s) => (
                    <option key={s.id} value={s.sender_id}>
                      {s.sender_id}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Recipient Phone</label>
                <Input
                  placeholder="+255712345678"
                  value={testPhone}
                  onChange={(e) => setTestPhone(e.target.value)}
                />
              </div>

              <div className="flex items-end">
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={handleSendTestSMS}
                  disabled={testSending || !testPhone}
                >
                  <Send className="mr-2 h-4 w-4" />
                  {testSending ? 'Sending SMS...' : 'Send Test SMS'}
                </Button>
              </div>
            </div>

            {testResult && (
              <div
                className={`p-3 rounded-lg text-xs font-medium space-y-1 ${
                  testResult.success
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-400'
                    : 'bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-400'
                }`}
              >
                <div>{testResult.message}</div>
                {testResult.details && <div className="text-[11px] opacity-85 font-mono">{testResult.details}</div>}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 2. Preferences & Templates */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <MessageSquare className="h-5 w-5" />
              </div>
              <div>
                <CardTitle>SMS Preferences & Sender Identification</CardTitle>
                <CardDescription>Configure Wi-Fi voucher SMS delivery options.</CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3 border-b border-border pb-4">
            <Checkbox label="Enable SMS Notifications" defaultChecked />
            <Checkbox label="Send Wi-Fi Vouchers via SMS automatically" defaultChecked />
            <Checkbox label="Send Access Expiry Reminder SMS" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input label="Sender ID / Sender Name" placeholder="USIMAMIZI" defaultValue="USIMAMIZI" />
            <Select label="Default Notification Language" defaultValue="en">
              <option value="en">English</option>
              <option value="sw">Swahili (Kiswahili)</option>
            </Select>
          </div>
        </CardContent>
        <CardFooter className="justify-end border-t border-border pt-4">
          <Button variant="primary">Save Preferences</Button>
        </CardFooter>
      </Card>

      {/* 3. Email Notifications Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Mail className="h-5 w-5" />
              </div>
              <div>
                <CardTitle>Email Notification Settings</CardTitle>
                <CardDescription>Configure receipt emails, reports, and administrative alerts.</CardDescription>
              </div>
            </div>
            <Badge variant="outline">Configurable</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <Checkbox label="Send payment receipts via email" defaultChecked />
            <Checkbox label="Send router status alert emails" defaultChecked />
          </div>
          <Input label="Notification Email Address" placeholder="alerts@company.com" />
        </CardContent>
        <CardFooter className="justify-end border-t border-border pt-4">
          <Button variant="primary">Save Email Settings</Button>
        </CardFooter>
      </Card>
    </div>
  );
}
