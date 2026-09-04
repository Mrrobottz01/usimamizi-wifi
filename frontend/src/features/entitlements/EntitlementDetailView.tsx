import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { AccessEntitlementDetail } from '../../types';
import {
  X,
  Key,
  CheckCircle2,
  XCircle,
  Clock,
  Gauge,
  Database,
  Smartphone,
  Layers,
  PauseCircle,
  PlayCircle,
  ShieldAlert,
  Ticket,
  ArrowRight,
  Info
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface EntitlementDetailViewProps {
  item: AccessEntitlementDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onSuspend: (item: AccessEntitlementDetail) => void;
  onResume: (item: AccessEntitlementDetail) => void;
  onRevoke: (item: AccessEntitlementDetail) => void;
}

export function EntitlementDetailView({
  item,
  isOpen,
  onClose,
  onSuspend,
  onResume,
  onRevoke,
}: EntitlementDetailViewProps) {
  if (!isOpen || !item) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return <Badge variant="success">Active</Badge>;
      case 'SUSPENDED':
        return <Badge variant="warning">Suspended</Badge>;
      case 'EXPIRED':
        return <Badge variant="secondary">Expired</Badge>;
      case 'REVOKED':
        return <Badge variant="destructive">Revoked</Badge>;
      case 'PENDING':
      default:
        return <Badge variant="outline">Pending</Badge>;
    }
  };

  const formatBytes = (bytes?: number | null) => {
    if (bytes === undefined || bytes === null) return 'Unlimited';
    if (bytes === 0) return '0 MB';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(1)} GB`;
    }
    return `${mb.toFixed(0)} MB`;
  };

  const formatSeconds = (seconds?: number | null) => {
    if (seconds === undefined || seconds === null) return 'Continuous Wall-Clock';
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 sm:p-6 overflow-y-auto">
      <div className="relative w-full max-w-3xl rounded-xl border border-border bg-card shadow-2xl text-card-foreground my-8 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Key className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-foreground font-mono">{item.reference}</h3>
                {getStatusBadge(item.status)}
              </div>
              <p className="text-xs text-muted-foreground">
                Source: <span className="font-semibold text-foreground">{item.source_type}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Authorization State Card */}
          <div
            className={`rounded-lg border p-4 flex items-center justify-between ${
              item.is_authorizable
                ? 'border-emerald-200 bg-emerald-50/20 dark:border-emerald-900/40 dark:bg-emerald-950/10'
                : 'border-rose-200 bg-rose-50/20 dark:border-rose-900/40 dark:bg-rose-950/10'
            }`}
          >
            <div className="flex items-center space-x-3">
              {item.is_authorizable ? (
                <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <XCircle className="h-6 w-6 text-rose-600 dark:text-rose-400" />
              )}
              <div>
                <h4 className="text-sm font-bold text-foreground">
                  Network Authorization Status: {item.authorization_status}
                </h4>
                <p className="text-xs text-muted-foreground">
                  {item.is_authorizable
                    ? 'Valid for network access and session initialization.'
                    : `Network login requests will be denied (Reason: ${item.authorization_status}).`}
                </p>
              </div>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" /> Validity Mode
              </span>
              <div className="mt-1 text-xs font-bold text-foreground">{item.validity_mode}</div>
            </div>
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Gauge className="h-3 w-3" /> Bandwidth Limit
              </span>
              <div className="mt-1 text-xs font-bold text-foreground">
                {item.download_speed_kbps ? `${item.download_speed_kbps / 1024}M / ${item.upload_speed_kbps ? item.upload_speed_kbps / 1024 : 0}M` : 'Unlimited'}
              </div>
            </div>
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Database className="h-3 w-3" /> Data Limit
              </span>
              <div className="mt-1 text-xs font-bold text-foreground">{formatBytes(item.data_limit_bytes)}</div>
            </div>
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground flex items-center gap-1">
                <Smartphone className="h-3 w-3" /> Max Devices
              </span>
              <div className="mt-1 text-xs font-bold text-foreground">
                {item.max_devices} device(s) / {item.simultaneous_sessions} session(s)
              </div>
            </div>
          </div>

          {/* Associated Voucher / Plan Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Plan Info */}
            <div className="rounded-lg border border-border p-4 bg-muted/20 space-y-2">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Access Plan</span>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold text-foreground">{item.plan_name}</div>
                  <div className="text-xs text-muted-foreground font-mono">Code: {item.plan_code}</div>
                </div>
                {item.plan_snapshot?.price !== undefined && (
                  <Badge variant="outline" className="font-mono text-xs">
                    {String(item.plan_snapshot.price)} {String(item.plan_snapshot.currency || 'TZS')}
                  </Badge>
                )}
              </div>
            </div>

            {/* Voucher Info */}
            <div className="rounded-lg border border-border p-4 bg-muted/20 space-y-2">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Associated Instrument</span>
              {item.voucher_code ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Ticket className="h-4 w-4 text-primary" />
                    <span className="text-sm font-bold font-mono text-foreground">{item.voucher_code}</span>
                  </div>
                  {item.voucher_id && (
                    <Link to="/vouchers" className="text-xs font-semibold text-primary hover:underline inline-flex items-center">
                      Voucher Batches <ArrowRight className="ml-1 h-3 w-3" />
                    </Link>
                  )}
                </div>
              ) : (
                <div className="text-xs text-muted-foreground italic">
                  Granted via {item.source_type} (No voucher token).
                </div>
              )}
            </div>
          </div>

          {/* Quota & Consumption Status */}
          <div className="rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5" /> Quota & Session Consumption
              </h4>
              <span className="text-[11px] text-muted-foreground">Stored State</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3 rounded bg-muted/30 border border-border/50">
                <div className="text-muted-foreground mb-1">Data Consumed:</div>
                <div className="text-sm font-bold text-foreground">
                  {formatBytes(item.data_used_bytes)} / {formatBytes(item.data_limit_bytes)}
                </div>
              </div>
              <div className="p-3 rounded bg-muted/30 border border-border/50">
                <div className="text-muted-foreground mb-1">Usage Time Consumed:</div>
                <div className="text-sm font-bold text-foreground">
                  {formatSeconds(item.usage_time_used_seconds)} / {formatSeconds(item.usage_time_limit_seconds)}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-2">
              <Info className="h-3.5 w-3.5 text-primary shrink-0" />
              <span>Usage tracking updates in real-time once central session accounting is enabled.</span>
            </div>
          </div>

          {/* Timestamps & Life Bounds */}
          <div className="rounded-lg border border-border p-4 space-y-2 text-xs">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5" /> Lifecycle Timestamps
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div>
                <span className="text-muted-foreground">Created:</span>{' '}
                <span className="font-semibold text-foreground">{new Date(item.created_at).toLocaleString()}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Activated:</span>{' '}
                <span className="font-semibold text-foreground">
                  {item.activated_at ? new Date(item.activated_at).toLocaleString() : 'Pending'}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">Expires:</span>{' '}
                <span className="font-semibold text-foreground">
                  {item.expires_at ? new Date(item.expires_at).toLocaleString() : 'Never / Usage Based'}
                </span>
              </div>
            </div>

            {item.suspended_at && (
              <div className="mt-2 rounded bg-amber-50 dark:bg-amber-950/40 p-2.5 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-900/50">
                <span className="font-bold">Suspended on:</span> {new Date(item.suspended_at).toLocaleString()}
                {item.suspension_reason && <div>Reason: {item.suspension_reason}</div>}
              </div>
            )}

            {item.revoked_at && (
              <div className="mt-2 rounded bg-destructive/10 p-2.5 text-destructive border border-destructive/20">
                <span className="font-bold">Revoked on:</span> {new Date(item.revoked_at).toLocaleString()}
                {item.revocation_reason && <div>Reason: {item.revocation_reason}</div>}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4 bg-muted/20">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
          <div className="flex items-center space-x-2">
            {item.status === 'ACTIVE' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSuspend(item)}
                className="text-amber-600 border-amber-200 hover:bg-amber-50 dark:hover:bg-amber-950"
              >
                <PauseCircle className="mr-1.5 h-4 w-4" /> Suspend
              </Button>
            )}
            {item.status === 'SUSPENDED' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onResume(item)}
                className="text-emerald-600 border-emerald-200 hover:bg-emerald-50 dark:hover:bg-emerald-950"
              >
                <PlayCircle className="mr-1.5 h-4 w-4" /> Resume
              </Button>
            )}
            {['PENDING', 'ACTIVE', 'SUSPENDED'].includes(item.status) && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onRevoke(item)}
              >
                <ShieldAlert className="mr-1.5 h-4 w-4" /> Revoke
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
