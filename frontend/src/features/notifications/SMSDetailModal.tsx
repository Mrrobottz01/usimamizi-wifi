import { useState } from 'react';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { SMSDeliveryAttempt, SMSHistoryDetail } from '../../types';
import {
  X,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  Ticket,
  MessageSquare,
  Layers,
  ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';

interface SMSDetailModalProps {
  item: SMSHistoryDetail | null;
  isOpen: boolean;
  onClose: () => void;
  onRetry: (id: string) => Promise<void>;
}

export function SMSDetailModal({ item, isOpen, onClose, onRetry }: SMSDetailModalProps) {
  const [retrying, setRetrying] = useState(false);

  if (!isOpen || !item) return null;

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await onRetry(item.id);
    } finally {
      setRetrying(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DELIVERED':
        return <Badge variant="success">Delivered</Badge>;
      case 'SENT':
        return <Badge variant="secondary">Sent (Queued)</Badge>;
      case 'SENDING':
        return <Badge variant="warning">Sending</Badge>;
      case 'FAILED':
        return <Badge variant="destructive">Failed</Badge>;
      case 'QUEUED':
      default:
        return <Badge variant="outline">Queued</Badge>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 sm:p-6 overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-xl border border-border bg-card shadow-2xl text-card-foreground my-8 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <MessageSquare className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">SMS Delivery Details</h3>
              <p className="text-xs text-muted-foreground font-mono">ID: {item.id}</p>
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
          {/* Key Overview Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground">Status</span>
              <div className="mt-1">{getStatusBadge(item.status)}</div>
            </div>
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground">Recipient</span>
              <div className="mt-1 font-mono text-xs font-semibold text-foreground">
                {item.phone_normalized || item.recipient}
              </div>
            </div>
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground">Message Type</span>
              <div className="mt-1 text-xs font-semibold text-foreground">{item.message_type}</div>
            </div>
            <div className="rounded-lg border border-border/70 p-3 bg-muted/30">
              <span className="text-[11px] font-medium text-muted-foreground">Total Attempts</span>
              <div className="mt-1 text-xs font-bold text-foreground">{item.attempts?.length || 1} attempt(s)</div>
            </div>
          </div>

          {/* Rendered Message Text */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Rendered SMS Content</h4>
            <div className="rounded-lg border border-border bg-muted/40 p-3.5 font-mono text-xs text-foreground whitespace-pre-wrap leading-relaxed">
              {item.rendered_content || 'No message content available.'}
            </div>
          </div>

          {/* Voucher Relationship */}
          {item.voucher_code && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Associated Wi-Fi Voucher</h4>
              <div className="rounded-lg border border-border p-3.5 bg-primary/5 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/10 text-primary">
                    <Ticket className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-bold font-mono text-foreground">{item.voucher_code}</div>
                    <div className="text-xs text-muted-foreground">
                      Plan: <span className="font-semibold text-foreground">{item.plan_name || 'Standard'}</span>
                    </div>
                  </div>
                </div>
                {item.voucher_batch_id && (
                  <Link
                    to={`/vouchers/batches/${item.voucher_batch_id}`}
                    className="inline-flex items-center text-xs font-semibold text-primary hover:underline"
                  >
                    View Batch <ArrowRight className="ml-1 h-3.5 w-3.5" />
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* Delivery Attempts & Failover Timeline */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5" /> Multi-Provider Delivery Timeline
              </h4>
              <span className="text-[11px] text-muted-foreground">Chronological Failover</span>
            </div>

            <div className="space-y-3">
              {item.attempts && item.attempts.length > 0 ? (
                item.attempts.map((attempt: SMSDeliveryAttempt) => {
                  const isSuccess = attempt.status === 'SUCCESS';
                  return (
                    <div
                      key={attempt.id || attempt.attempt_number}
                      className={`rounded-lg border p-3.5 transition ${
                        isSuccess
                          ? 'border-emerald-200 bg-emerald-50/20 dark:border-emerald-900/40 dark:bg-emerald-950/10'
                          : 'border-rose-200 bg-rose-50/20 dark:border-rose-900/40 dark:bg-rose-950/10'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-muted text-[11px] font-bold">
                            #{attempt.attempt_number}
                          </span>
                          <span className="font-bold text-sm text-foreground uppercase">{attempt.provider_code}</span>
                          {attempt.sender_id && (
                            <Badge variant="outline" className="text-[10px] py-0 px-1.5 font-mono">
                              Sender: {attempt.sender_id}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          {isSuccess ? (
                            <Badge variant="success" className="flex items-center gap-1">
                              <CheckCircle2 className="h-3 w-3" /> Success
                            </Badge>
                          ) : (
                            <Badge variant="destructive" className="flex items-center gap-1">
                              <XCircle className="h-3 w-3" /> Failed
                            </Badge>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-muted-foreground pt-1 border-t border-border/50">
                        <div>
                          <span className="font-medium">Started:</span>{' '}
                          {attempt.started_at ? new Date(attempt.started_at).toLocaleString() : 'N/A'}
                        </div>
                        <div>
                          <span className="font-medium">Provider Ref:</span>{' '}
                          <code className="font-mono text-[11px] text-foreground">
                            {attempt.provider_reference || 'None'}
                          </code>
                        </div>
                      </div>

                      {!isSuccess && attempt.failure_reason && (
                        <div className="mt-2 rounded bg-rose-50 dark:bg-rose-950/50 p-2 text-xs text-rose-700 dark:text-rose-300 font-mono">
                          <div className="font-semibold">{attempt.failure_category || 'ERROR'}:</div>
                          <div>{attempt.failure_reason}</div>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-muted-foreground italic p-3 text-center border border-dashed rounded-lg">
                  No delivery attempts recorded yet.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between border-t border-border px-6 py-4 bg-muted/20">
          <div className="flex items-center text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5 mr-1" />
            Created: {new Date(item.created_at).toLocaleString()}
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
            {item.can_retry && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleRetry}
                disabled={retrying}
                className="bg-primary text-primary-foreground"
              >
                <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${retrying ? 'animate-spin' : ''}`} />
                {retrying ? 'Retrying...' : 'Retry Delivery'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
