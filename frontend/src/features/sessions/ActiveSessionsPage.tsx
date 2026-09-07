import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiClient } from '../../lib/api-client';
import { HotspotSession, SessionSummaryMetrics, SessionStatus, SessionDisconnectRequest } from '../../types';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import {
  Activity,
  Search,
  RefreshCw,
  Clock,
  Wifi,
  ChevronLeft,
  ChevronRight,
  Router as RouterIcon,
  PowerOff,
  History,
  AlertTriangle,
  X,
  CheckCircle2,
  XCircle,
  Smartphone,
} from 'lucide-react';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
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

function getStatusBadge(status: SessionStatus) {
  switch (status) {
    case 'ACTIVE':
      return <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30">Active</Badge>;
    case 'STOPPED':
      return <Badge variant="outline" className="text-muted-foreground border-border">Stopped</Badge>;
    case 'STALE':
      return <Badge className="bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30">Stale</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

interface PaginatedSessionsResponse {
  results: HotspotSession[];
  count: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary?: SessionSummaryMetrics;
}

export const ActiveSessionsPage: React.FC = () => {
  const { selectedCompany } = useAuth();
  const companyId = selectedCompany?.id;

  const [sessions, setSessions] = useState<HotspotSession[]>([]);
  const [metrics, setMetrics] = useState<SessionSummaryMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Disconnect Modal State
  const [disconnectSession, setDisconnectSession] = useState<HotspotSession | null>(null);
  const [disconnectReason, setDisconnectReason] = useState('Customer support request');
  const [disconnecting, setDisconnecting] = useState(false);
  const [disconnectError, setDisconnectError] = useState('');

  // Disconnect History State
  const [historySession, setHistorySession] = useState<HotspotSession | null>(null);
  const [historyList, setHistoryList] = useState<SessionDisconnectRequest[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchSessions = useCallback(async () => {
    if (!companyId) return;
    try {
      setLoading(true);
      const params = new URLSearchParams({
        company_id: companyId,
        page: page.toString(),
        page_size: '15',
      });
      if (selectedStatus !== 'ALL') {
        params.append('status', selectedStatus);
      }
      if (searchTerm.trim()) {
        params.append('search', searchTerm.trim());
      }

      const res = await apiClient.get<PaginatedSessionsResponse>(`/api/v1/sessions/?${params.toString()}`);
      const data = res.data;
      setSessions(data.results || []);
      setTotalPages(data.total_pages || 1);
      setTotalCount(data.count || 0);
      if (data.summary) {
        setMetrics(data.summary);
      }
    } catch (err) {
      console.error('Failed to fetch sessions', err);
    } finally {
      setLoading(false);
    }
  }, [companyId, page, selectedStatus, searchTerm]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleDisconnect = async () => {
    if (!disconnectSession || !companyId) return;
    if (!disconnectReason.trim()) {
      setDisconnectError('Please provide a reason for terminating this session.');
      return;
    }

    try {
      setDisconnecting(true);
      setDisconnectError('');
      await apiClient.post(`/api/v1/sessions/${disconnectSession.id}/disconnect/?company_id=${companyId}`, {
        reason: disconnectReason.trim(),
      });
      setDisconnectSession(null);
      setDisconnectReason('Customer support request');
      fetchSessions();
    } catch (err: unknown) {
      let msg = 'Failed to transmit RADIUS Disconnect-Request.';
      if (err && typeof err === 'object' && 'response' in err) {
        const res = (err as { response?: { data?: { detail?: string; message?: string } } }).response;
        msg = res?.data?.detail || res?.data?.message || msg;
      }
      setDisconnectError(msg);
    } finally {
      setDisconnecting(false);
    }
  };

  const openHistory = async (sess: HotspotSession) => {
    if (!companyId) return;
    setHistorySession(sess);
    setHistoryLoading(true);
    try {
      const res = await apiClient.get<SessionDisconnectRequest[]>(
        `/api/v1/sessions/${sess.id}/disconnect-history/?company_id=${companyId}`
      );
      setHistoryList(res.data || []);
    } catch (err) {
      console.error('Failed to load disconnect history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            Active & Historical Sessions
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time connection monitoring, RADIUS accounting, and live session disconnect controls (RFC 3576).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchSessions()}
            disabled={loading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border p-4 bg-card shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Total Sessions</div>
          <div className="text-2xl font-bold text-foreground mt-1">{metrics?.total_sessions ?? '—'}</div>
        </div>
        <div className="rounded-xl border border-border p-4 bg-card shadow-sm border-l-4 border-l-emerald-500">
          <div className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Active Online</div>
          <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{metrics?.active ?? '—'}</div>
        </div>
        <div className="rounded-xl border border-border p-4 bg-card shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Stopped</div>
          <div className="text-2xl font-bold text-foreground mt-1">{metrics?.stopped ?? '—'}</div>
        </div>
        <div className="rounded-xl border border-border p-4 bg-card shadow-sm">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Stale / Disconnected</div>
          <div className="text-2xl font-bold text-foreground mt-1">{metrics?.stale ?? '—'}</div>
        </div>
      </div>

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Status Pills */}
        <div className="flex items-center gap-1 overflow-x-auto pb-2 sm:pb-0">
          {['ALL', 'ACTIVE', 'STOPPED', 'STALE'].map((tab) => (
            <button
              key={tab}
              onClick={() => {
                setSelectedStatus(tab);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                selectedStatus === tab
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              {tab === 'ALL' ? 'All Sessions' : tab}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search MAC, user, router, IP..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            className="pl-9 text-xs"
          />
        </div>
      </div>

      {/* Table / Cards Container */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {loading && sessions.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-2">
            <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            Loading hotspot connection sessions...
          </div>
        ) : sessions.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted-foreground flex flex-col items-center justify-center gap-2">
            <Wifi className="h-8 w-8 text-muted-foreground/50" />
            No sessions match your search or filter criteria.
          </div>
        ) : (
          <>
            {/* Desktop Table View */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold uppercase tracking-wider">
                    <th className="py-3 px-4">User / Access Code</th>
                    <th className="py-3 px-4">Device & IP</th>
                    <th className="py-3 px-4">Plan</th>
                    <th className="py-3 px-4">NAS / Router</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4 text-right">Data Usage</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {sessions.map((sess) => (
                    <tr key={sess.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-3 px-4 font-medium text-foreground">
                        <div className="font-mono font-bold text-foreground">{sess.username}</div>
                        <div className="text-[11px] text-muted-foreground font-mono">{sess.entitlement_reference}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5 font-medium text-foreground">
                          <Smartphone className="h-3.5 w-3.5 text-primary shrink-0" />
                          <span className="font-semibold text-sm">{sess.device_name || 'Generic Device'}</span>
                        </div>
                        <div className="font-mono text-[11px] text-muted-foreground mt-0.5">{sess.mac_address}</div>
                        <div className="text-[11px] text-muted-foreground font-mono">{sess.ip_address || '—'}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-medium text-foreground">{sess.plan_name || 'Standard Access'}</span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <RouterIcon className="h-3.5 w-3.5 text-muted-foreground/70" />
                          <span>{sess.radius_client_name}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          {getStatusBadge(sess.status)}
                          {sess.latest_disconnect_status && (
                            <span className="text-[10px] text-muted-foreground font-mono">
                              ({sess.latest_disconnect_status})
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3 text-muted-foreground" />
                          {formatDuration(sess.session_seconds)}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-mono">
                        <div className="font-bold text-foreground">{formatBytes(sess.total_bytes)}</div>
                        <div className="text-[10px] text-muted-foreground">
                          ↓ {formatBytes(sess.output_bytes)} / ↑ {formatBytes(sess.input_bytes)}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {sess.status === 'ACTIVE' && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setDisconnectSession(sess);
                                setDisconnectError('');
                              }}
                              className="h-7 px-2.5 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30 border-rose-200 dark:border-rose-900/50"
                            >
                              <PowerOff className="h-3.5 w-3.5 mr-1" />
                              Disconnect
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openHistory(sess)}
                            className="h-7 px-2 text-muted-foreground hover:text-foreground"
                            title="Disconnect History"
                          >
                            <History className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Card Layout (<= 390px / < md) */}
            <div className="md:hidden divide-y divide-border">
              {sessions.map((sess) => (
                <div key={sess.id} className="p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-mono font-bold text-sm text-foreground">{sess.username}</div>
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground mt-0.5">
                        <Smartphone className="h-3 w-3 text-primary shrink-0" />
                        <span>{sess.device_name || 'Generic Device'}</span>
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono mt-0.5">{sess.mac_address} • {sess.ip_address || '—'}</div>
                    </div>
                    <div className="flex items-center gap-1">
                      {getStatusBadge(sess.status)}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded border border-border p-2 bg-muted/20">
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold block">Duration</span>
                      <span className="font-mono font-medium text-foreground">{formatDuration(sess.session_seconds)}</span>
                    </div>
                    <div className="rounded border border-border p-2 bg-muted/20">
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold block">Data Transferred</span>
                      <span className="font-mono font-bold text-foreground">{formatBytes(sess.total_bytes)}</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-1 border-t border-border/50">
                    <span className="truncate max-w-[150px] text-muted-foreground">{sess.radius_client_name}</span>
                    <div className="flex items-center gap-2">
                      {sess.status === 'ACTIVE' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setDisconnectSession(sess);
                            setDisconnectError('');
                          }}
                          className="h-7 px-2 text-xs text-rose-600 border-rose-200 dark:border-rose-900/50"
                        >
                          <PowerOff className="h-3 w-3 mr-1" />
                          Disconnect
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openHistory(sess)}
                        className="h-7 px-1.5 text-muted-foreground"
                      >
                        <History className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Pagination Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-muted/20 text-xs text-muted-foreground">
          <div>
            Showing <span className="font-medium text-foreground">{sessions.length}</span> of <span className="font-medium text-foreground">{totalCount}</span> sessions
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="h-8 px-2"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="font-medium text-foreground">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="h-8 px-2"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Disconnect Confirmation Modal */}
      {disconnectSession && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-bold">
                <AlertTriangle className="h-5 w-5" />
                <span>Disconnect Active Session</span>
              </div>
              <button
                onClick={() => setDisconnectSession(null)}
                disabled={disconnecting}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-muted/40 rounded-lg space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">User / Voucher:</span>
                  <span className="font-mono font-bold text-foreground">{disconnectSession.username}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Device MAC:</span>
                  <span className="font-mono text-foreground">{disconnectSession.mac_address}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">IP Address:</span>
                  <span className="font-mono text-foreground">{disconnectSession.ip_address || '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">NAS Router:</span>
                  <span className="text-foreground">{disconnectSession.radius_client_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Connected Duration:</span>
                  <span className="font-mono text-foreground">{formatDuration(disconnectSession.session_seconds)}</span>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-foreground block">
                  Termination Reason <span className="text-rose-500">*</span>
                </label>
                <Input
                  value={disconnectReason}
                  onChange={(e) => setDisconnectReason(e.target.value)}
                  placeholder="e.g. Customer support request, manual admin kick..."
                  disabled={disconnecting}
                  className="text-xs"
                />
              </div>

              {disconnectError && (
                <div className="p-2.5 bg-rose-500/15 border border-rose-500/30 text-rose-600 dark:text-rose-400 rounded-lg text-xs">
                  {disconnectError}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDisconnectSession(null)}
                disabled={disconnecting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDisconnect}
                disabled={disconnecting}
                className="flex items-center gap-1.5"
              >
                {disconnecting ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Disconnecting…
                  </>
                ) : (
                  <>
                    <PowerOff className="h-3.5 w-3.5" />
                    Disconnect Session
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Disconnect History Modal */}
      {historySession && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2 text-foreground font-bold">
                <History className="h-5 w-5 text-primary" />
                <span>Disconnect History & Evidence</span>
              </div>
              <button
                onClick={() => setHistorySession(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="text-xs text-muted-foreground">
                Session: <span className="font-mono font-bold text-foreground">{historySession.username}</span> ({historySession.mac_address})
              </div>

              {historyLoading ? (
                <div className="py-8 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                  Loading history records...
                </div>
              ) : historyList.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No dynamic disconnect requests have been sent for this session.
                </div>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {historyList.map((req) => (
                    <div key={req.id} className="rounded-lg border border-border p-3 bg-muted/20 space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-foreground">{req.trigger_type}</span>
                        <Badge
                          variant="outline"
                          className={
                            req.status === 'ACKNOWLEDGED'
                              ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                              : req.status === 'TIMEOUT' || req.status === 'FAILED'
                              ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30'
                              : 'bg-muted text-muted-foreground'
                          }
                        >
                          {req.status === 'ACKNOWLEDGED' && <CheckCircle2 className="h-3 w-3 mr-1" />}
                          {(req.status === 'FAILED' || req.status === 'TIMEOUT') && <XCircle className="h-3 w-3 mr-1" />}
                          {req.status}
                        </Badge>
                      </div>
                      <div className="text-muted-foreground">{req.reason || 'No reason provided'}</div>
                      <div className="flex items-center justify-between text-[11px] text-muted-foreground/80 pt-1 border-t border-border/40 font-mono">
                        <span>Attempts: {req.attempt_count}</span>
                        <span>{new Date(req.requested_at).toLocaleString()}</span>
                      </div>
                      {req.response_message && (
                        <div className="text-[11px] font-mono text-muted-foreground bg-muted/40 p-1.5 rounded">
                          {req.response_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-3 border-t border-border">
              <Button variant="outline" size="sm" onClick={() => setHistorySession(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
