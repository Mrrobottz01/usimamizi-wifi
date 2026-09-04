import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch } from '../../lib/api-client';
import { HotspotWalledGardenEntry } from '../../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select } from '../../components/ui/select';
import {
  ShieldCheck,
  Download,
  Copy,
  Plus,
  Trash2,
  RefreshCw,
  Globe,
  Sparkles,
  Check,
} from 'lucide-react';

export function WalledGardenPage() {
  const { selectedCompany } = useAuth();

  const [entries, setEntries] = useState<HotspotWalledGardenEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportScript, setExportScript] = useState<string>('');
  const [copied, setCopied] = useState(false);

  // New entry form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [entryType, setEntryType] = useState<'DOMAIN' | 'IP'>('DOMAIN');
  const [hostOrAddress, setHostOrAddress] = useState('');
  const [description, setDescription] = useState('');
  const [purpose, setPurpose] = useState<'PAYMENT' | 'PORTAL' | 'CUSTOM'>('PAYMENT');
  const [savingEntry, setSavingEntry] = useState(false);

  const fetchData = useCallback(async () => {
    if (!selectedCompany) return;
    try {
      setLoading(true);
      const [entriesData, scriptData] = await Promise.all([
        apiFetch<HotspotWalledGardenEntry[]>(`/payments/walled-garden/?company_id=${selectedCompany.id}`).catch(() => []),
        apiFetch<{ script: string }>(`/payments/walled-garden/export-routeros/?company_id=${selectedCompany.id}`).catch(() => ({ script: '' })),
      ]);

      setEntries(entriesData || []);
      setExportScript(scriptData?.script || '');
    } catch (err) {
      console.error('Failed to load walled garden entries', err);
    } finally {
      setLoading(false);
    }
  }, [selectedCompany]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleApplyPreset = async (presetName: string) => {
    if (!selectedCompany) return;
    try {
      setLoading(true);
      await apiFetch(`/payments/walled-garden/presets/apply/?company_id=${selectedCompany.id}`, {
        method: 'POST',
        body: JSON.stringify({
          company_id: selectedCompany.id,
          preset_name: presetName,
        }),
      });
      await fetchData();
    } catch (err) {
      console.error('Failed to apply preset', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEntry = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCompany || !hostOrAddress.trim()) return;

    try {
      setSavingEntry(true);
      const payload: Record<string, unknown> = {
        company_id: selectedCompany.id,
        entry_type: entryType,
        purpose,
        description: description.trim(),
        is_active: true,
      };
      if (entryType === 'DOMAIN') {
        payload.host = hostOrAddress.trim();
      } else {
        payload.address = hostOrAddress.trim();
      }

      await apiFetch(`/payments/walled-garden/?company_id=${selectedCompany.id}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      setHostOrAddress('');
      setDescription('');
      setShowAddForm(false);
      await fetchData();
    } catch (err) {
      console.error('Failed to create walled garden entry', err);
    } finally {
      setSavingEntry(false);
    }
  };

  const handleDeleteEntry = async (id: string) => {
    if (!selectedCompany) return;
    try {
      await apiFetch(`/payments/walled-garden/${id}/?company_id=${selectedCompany.id}`, {
        method: 'DELETE',
      });
      await fetchData();
    } catch (err) {
      console.error('Failed to delete walled garden entry', err);
    }
  };

  const handleCopyScript = () => {
    navigator.clipboard.writeText(exportScript);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadRsc = () => {
    const blob = new Blob([exportScript], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `walled-garden-${selectedCompany?.name.toLowerCase().replace(/\s+/g, '-') || 'config'}.rsc`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-primary" />
            <span>HotSpot Walled Garden (Allowlist)</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Allow unauthenticated mobile users to reach Snippe payment servers and captive portal without internet.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => handleApplyPreset('Snippe Payments')}>
            <Sparkles className="h-4 w-4 mr-1.5 text-amber-500" />
            Apply Snippe Preset
          </Button>
          <Button size="sm" onClick={() => setShowAddForm(!showAddForm)}>
            <Plus className="h-4 w-4 mr-1.5" />
            Add Custom Rule
          </Button>
        </div>
      </div>

      {/* Add Rule Form Modal / Inline */}
      {showAddForm && (
        <Card className="border-border bg-card shadow-sm animate-in fade-in duration-150">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold">Add Walled Garden Rule</CardTitle>
            <CardDescription className="text-xs">
              Configure a hostname or IP address that unauthenticated clients can browse freely.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleCreateEntry}>
            <CardContent className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-foreground">Rule Type</label>
                  <Select
                    value={entryType}
                    onChange={(e) => setEntryType(e.target.value as 'DOMAIN' | 'IP')}
                    className="h-9 text-xs"
                  >
                    <option value="DOMAIN">Domain (dst-host)</option>
                    <option value="IP">IP / Subnet (dst-address)</option>
                  </Select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-foreground">
                    {entryType === 'DOMAIN' ? 'Host Domain' : 'IP / Subnet'}
                  </label>
                  <Input
                    required
                    placeholder={entryType === 'DOMAIN' ? 'e.g. api.snippe.sh' : 'e.g. 10.5.50.254'}
                    value={hostOrAddress}
                    onChange={(e) => setHostOrAddress(e.target.value)}
                    className="h-9 text-xs font-mono"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-foreground">Purpose</label>
                  <Select
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value as 'PAYMENT' | 'PORTAL' | 'CUSTOM')}
                    className="h-9 text-xs"
                  >
                    <option value="PAYMENT">Payment Provider</option>
                    <option value="PORTAL">Captive Portal</option>
                    <option value="CUSTOM">Custom Domain</option>
                  </Select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-foreground">Description / Comment</label>
                <Input
                  placeholder="e.g. Snippe API Gateway for mobile money"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="h-9 text-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowAddForm(false)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={savingEntry || !hostOrAddress.trim()}>
                  {savingEntry ? 'Saving…' : 'Save Rule'}
                </Button>
              </div>
            </CardContent>
          </form>
        </Card>
      )}

      {/* Rules Table */}
      <Card className="border-border shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-muted/50 text-muted-foreground font-semibold uppercase tracking-wider border-b">
              <tr>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Target (Host / Address)</th>
                <th className="py-3 px-4">Purpose</th>
                <th className="py-3 px-4">Description</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted-foreground">
                    <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-primary" />
                    <span>Loading allowlist rules…</span>
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted-foreground">
                    No allowlist rules configured. Click <strong>Apply Snippe Preset</strong> to auto-configure.
                  </td>
                </tr>
              ) : (
                entries.map((item) => (
                  <tr key={item.id} className="hover:bg-muted/30 transition-colors">
                    <td className="py-3 px-4">
                      <Badge variant="outline" className="font-semibold text-[10px]">
                        {item.entry_type}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-foreground">
                      {item.host || item.address}
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        className={`text-[10px] font-bold ${
                          item.purpose === 'PAYMENT'
                            ? 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                            : item.purpose === 'PORTAL'
                            ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {item.purpose}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {item.description || '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
                        onClick={() => handleDeleteEntry(item.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* RouterOS Script Exporter */}
      <Card className="border-border shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div className="space-y-1">
            <CardTitle className="text-base flex items-center gap-2">
              <Globe className="h-5 w-5 text-primary" />
              <span>MikroTik RouterOS Synchronization Script</span>
            </CardTitle>
            <CardDescription className="text-xs">
              Execute these commands on your MikroTik terminal to allow customers to reach Snippe before login.
            </CardDescription>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleCopyScript}>
              {copied ? <Check className="h-3.5 w-3.5 mr-1.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5 mr-1.5" />}
              <span>{copied ? 'Copied!' : 'Copy Script'}</span>
            </Button>
            <Button size="sm" onClick={handleDownloadRsc}>
              <Download className="h-3.5 w-3.5 mr-1.5" />
              <span>Download .rsc</span>
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          <pre className="p-4 rounded-xl bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto border border-slate-800 leading-relaxed">
            {exportScript || '# No active walled garden rules found.'}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
