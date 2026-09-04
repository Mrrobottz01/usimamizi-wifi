import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiFetch } from '../../lib/api-client';
import { AccessPurchase, PaymentTransaction } from '../../types';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Select } from '../../components/ui/select';
import {
  CreditCard,
  DollarSign,
  CheckCircle2,
  Clock,
  Search,
  RefreshCw,
  ShoppingBag,
  TrendingUp,
} from 'lucide-react';

interface PaymentSummary {
  today_revenue: number;
  total_revenue: number;
  completed_count: number;
  pending_count: number;
  failed_count: number;
  top_plans: Array<{ plan__name: string; revenue: number; count: number }>;
}

export function PaymentsPage() {
  const { selectedCompany } = useAuth();

  const [summary, setSummary] = useState<PaymentSummary | null>(null);
  const [purchases, setPurchases] = useState<AccessPurchase[]>([]);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  const fetchData = useCallback(async () => {
    if (!selectedCompany) return;
    try {
      setLoading(true);
      const companyId = selectedCompany.id;

      let purchasesUrl = `/payments/purchases/?company_id=${companyId}`;
      let txnsUrl = `/payments/?company_id=${companyId}`;
      if (statusFilter !== 'ALL') {
        purchasesUrl += `&status=${statusFilter}`;
        txnsUrl += `&status=${statusFilter}`;
      }
      if (search.trim()) {
        purchasesUrl += `&search=${encodeURIComponent(search.trim())}`;
        txnsUrl += `&search=${encodeURIComponent(search.trim())}`;
      }

      const [summaryRes, purchasesRes, txnsRes] = await Promise.all([
        apiFetch<PaymentSummary>(`/payments/reports/summary/?company_id=${companyId}`).catch(() => null),
        apiFetch<{ results: AccessPurchase[] }>(purchasesUrl).catch(() => ({ results: [] })),
        apiFetch<{ results: PaymentTransaction[] }>(txnsUrl).catch(() => ({ results: [] })),
      ]);

      if (summaryRes) {
        setSummary(summaryRes);
      }
      setPurchases(purchasesRes?.results || []);
      setTransactions(txnsRes?.results || []);
    } catch (err) {
      console.error('Failed to load payment records', err);
    } finally {
      setLoading(false);
    }
  }, [selectedCompany, statusFilter, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'FULFILLED':
      case 'COMPLETED':
        return <Badge className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 font-bold">COMPLETED</Badge>;
      case 'PAYMENT_PENDING':
      case 'PENDING':
      case 'PROCESSING':
        return <Badge className="bg-amber-500/10 text-amber-500 border border-amber-500/20 font-bold">PENDING</Badge>;
      case 'FAILED':
      case 'EXPIRED':
      case 'CANCELLED':
        return <Badge className="bg-rose-500/10 text-rose-500 border border-rose-500/20 font-bold">{status}</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <CreditCard className="h-6 w-6 text-primary" />
            <span>Payments & Self-Service Orders</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            Track customer mobile money purchases, Snippe transactions, and live revenue.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Today's Revenue
            </CardTitle>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
              <DollarSign className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground font-mono">
              TZS {summary ? summary.today_revenue.toLocaleString() : '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-emerald-500" />
              <span>Captured today via Snippe</span>
            </p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Total Revenue
            </CardTitle>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
              <TrendingUp className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground font-mono">
              TZS {summary ? summary.total_revenue.toLocaleString() : '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {summary ? summary.completed_count : 0} completed orders
            </p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Completed Orders
            </CardTitle>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-600 font-mono">
              {summary ? summary.completed_count : 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Access granted & SMS delivered
            </p>
          </CardContent>
        </Card>

        <Card className="border-border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Pending / In-Flight
            </CardTitle>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500">
              <Clock className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-500 font-mono">
              {summary ? summary.pending_count : 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Awaiting USSD customer PIN
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="purchases" className="w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b">
          <TabsList className="bg-muted">
            <TabsTrigger value="purchases" className="flex items-center gap-1.5 font-semibold text-xs">
              <ShoppingBag className="h-4 w-4" />
              <span>Customer Orders ({purchases.length})</span>
            </TabsTrigger>
            <TabsTrigger value="transactions" className="flex items-center gap-1.5 font-semibold text-xs">
              <CreditCard className="h-4 w-4" />
              <span>Snippe Transactions ({transactions.length})</span>
            </TabsTrigger>
          </TabsList>

          {/* Search & Status Filter */}
          <div className="flex items-center gap-2">
            <div className="relative w-48 sm:w-60">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search phone or ref…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 h-9 text-xs"
              />
            </div>
            <div className="w-32">
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="h-9 text-xs"
              >
                <option value="ALL">All Status</option>
                <option value="COMPLETED">Completed</option>
                <option value="PENDING">Pending</option>
                <option value="FAILED">Failed</option>
              </Select>
            </div>
          </div>
        </div>

        {/* Tab 1: Access Purchases */}
        <TabsContent value="purchases" className="pt-4">
          <Card className="border-border shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 text-muted-foreground font-semibold uppercase tracking-wider border-b">
                  <tr>
                    <th className="py-3 px-4">Order Ref</th>
                    <th className="py-3 px-4">Customer Phone</th>
                    <th className="py-3 px-4">Package Plan</th>
                    <th className="py-3 px-4">Amount</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Voucher Code</th>
                    <th className="py-3 px-4">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {purchases.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground">
                        No customer purchase orders found matching your query.
                      </td>
                    </tr>
                  ) : (
                    purchases.map((pur) => (
                      <tr key={pur.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-foreground">
                          {pur.reference}
                        </td>
                        <td className="py-3 px-4 font-medium text-foreground">
                          {pur.customer_phone}
                        </td>
                        <td className="py-3 px-4 text-foreground font-semibold">
                          {pur.plan_name}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-foreground">
                          TZS {parseFloat(pur.amount).toLocaleString()}
                        </td>
                        <td className="py-3 px-4">
                          {getStatusBadge(pur.status)}
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-primary">
                          {pur.voucher_code || '—'}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {new Date(pur.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>

        {/* Tab 2: Payment Transactions */}
        <TabsContent value="transactions" className="pt-4">
          <Card className="border-border shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-muted/50 text-muted-foreground font-semibold uppercase tracking-wider border-b">
                  <tr>
                    <th className="py-3 px-4">Internal Ref</th>
                    <th className="py-3 px-4">Provider Ref</th>
                    <th className="py-3 px-4">Provider</th>
                    <th className="py-3 px-4">Amount</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Customer</th>
                    <th className="py-3 px-4">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {transactions.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground">
                        No financial transactions found.
                      </td>
                    </tr>
                  ) : (
                    transactions.map((txn) => (
                      <tr key={txn.id} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3 px-4 font-mono font-semibold text-foreground">
                          {txn.internal_reference}
                        </td>
                        <td className="py-3 px-4 font-mono text-muted-foreground">
                          {txn.provider_reference || '—'}
                        </td>
                        <td className="py-3 px-4">
                          <Badge variant="outline" className="font-semibold text-[10px]">
                            {txn.provider}
                          </Badge>
                        </td>
                        <td className="py-3 px-4 font-mono font-bold text-foreground">
                          TZS {parseFloat(txn.amount).toLocaleString()}
                        </td>
                        <td className="py-3 px-4">
                          {getStatusBadge(txn.status)}
                        </td>
                        <td className="py-3 px-4 text-foreground">
                          {txn.customer_phone || '—'}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground">
                          {new Date(txn.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
