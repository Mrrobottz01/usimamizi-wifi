import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Wifi,
  Smartphone,
  CreditCard,
  Clock,
  LogOut,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { CustomerDevice, Plan, Subscription } from '../../types';
import { apiClient } from '../../lib/api-client';

const TOKEN_KEY = 'usimamizi_customer_portal_token';

interface PortalMe {
  id: string;
  normalized_phone: string;
  full_name?: string;
  language: 'EN' | 'SW';
  company_name: string;
}

export const CustomerPortalPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const activeSlug = slug || 'default';

  // Auth State
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [phone, setPhone] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpStep, setOtpStep] = useState<'PHONE' | 'CODE'>('PHONE');
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState<number>(0);

  // Authenticated State
  const [me, setMe] = useState<PortalMe | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [devices, setDevices] = useState<CustomerDevice[]>([]);
  const [availablePlans, setAvailablePlans] = useState<Plan[]>([]);
  const [loadingDashboard, setLoadingDashboard] = useState(false);

  // Countdown timer state
  const [remainingSecs, setRemainingSecs] = useState<number>(0);

  // Payment / Renew State
  const [isRenewing, setIsRenewing] = useState(false);
  const [renewPlanId, setRenewPlanId] = useState<string>('');
  const [renewMethod, setRenewMethod] = useState<'MPESA' | 'AIRTEL_MONEY' | 'MIXX'>('MPESA');
  const [renewStatusMsg, setRenewStatusMsg] = useState<string | null>(null);

  // Cooldown timer interval
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  // Subscription remaining seconds countdown interval
  useEffect(() => {
    if (remainingSecs <= 0) return;
    const interval = setInterval(() => {
      setRemainingSecs((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [remainingSecs]);

  // Request OTP
  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setOtpError(null);
    if (!phone.trim()) {
      setOtpError('Tafadhali weka namba ya simu / Please enter your phone number.');
      return;
    }

    setOtpLoading(true);
    try {
      await apiClient.post('/api/v1/public/customer/request-otp/', {
        phone: phone.trim(),
        slug: activeSlug,
      });
      setOtpStep('CODE');
      setCooldown(60);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Failed to send verification code. Please retry.';
      setOtpError(detail);
      if (err.response?.data?.cooldown_remaining) {
        setCooldown(err.response.data.cooldown_remaining);
      }
    } finally {
      setOtpLoading(false);
    }
  };

  // Verify OTP
  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setOtpError(null);
    if (!otpCode.trim() || otpCode.trim().length !== 6) {
      setOtpError('Tafadhali weka namba 6 za uthibitisho / Enter the 6-digit code.');
      return;
    }

    setOtpLoading(true);
    try {
      const res = await apiClient.post<{ token: string; customer: any }>('/api/v1/public/customer/verify-otp/', {
        phone: phone.trim(),
        code: otpCode.trim(),
        slug: activeSlug,
      });

      const authToken = res.data.token;
      localStorage.setItem(TOKEN_KEY, authToken);
      setToken(authToken);
      setOtpStep('PHONE');
      setOtpCode('');
    } catch (err: any) {
      setOtpError(err.response?.data?.detail || 'Invalid or expired code.');
    } finally {
      setOtpLoading(false);
    }
  };

  // Fetch Authenticated Dashboard Data
  const fetchDashboard = useCallback(async () => {
    if (!token) return;
    setLoadingDashboard(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };

      const [meRes, subRes, devRes] = await Promise.all([
        apiClient.get<PortalMe>('/api/v1/public/customer/me/', { headers }),
        apiClient.get<{ subscription: Subscription | null }>('/api/v1/public/customer/subscription/', { headers }),
        apiClient.get<CustomerDevice[]>('/api/v1/public/customer/devices/', { headers }),
      ]);

      setMe(meRes.data);
      if (subRes.data.subscription) {
        setSubscription(subRes.data.subscription);
        setRemainingSecs(subRes.data.subscription.remaining_seconds);
      } else {
        setSubscription(null);
        setRemainingSecs(0);
      }
      setDevices(devRes.data);

      // Fetch public hotspot plans
      try {
        const plansRes = await apiClient.get<Plan[]>(`/api/v1/public/hotspots/${activeSlug}/plans/`);
        setAvailablePlans(plansRes.data);
      } catch {
        // Fallback plans
      }
    } catch (err: any) {
      if (err.response?.status === 401) {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      }
    } finally {
      setLoadingDashboard(false);
    }
  }, [token, activeSlug]);

  useEffect(() => {
    if (token) {
      fetchDashboard();
    }
  }, [token, fetchDashboard]);

  // Handle Disconnect Device
  const handleDisconnectDevice = async (mac: string) => {
    if (!token) return;
    try {
      await apiClient.post(
        '/api/v1/public/customer/disconnect-device/',
        { mac_address: mac },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchDashboard();
    } catch (err: any) {
      console.error('Failed to disconnect device', err);
    }
  };

  // Handle Self-Service Renew
  const handleRenew = async () => {
    if (!token) return;
    setIsRenewing(true);
    setRenewStatusMsg(null);
    try {
      await apiClient.post(
        '/api/v1/public/customer/renew/',
        {
          plan_id: renewPlanId || (subscription ? subscription.plan_id : undefined),
          payment_method: renewMethod,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setRenewStatusMsg('Ombi la malipo limetumwa! Weka PIN yako ya simu / Payment prompt sent to your phone. Enter PIN to complete.');
      // Refresh after short delay
      setTimeout(() => {
        fetchDashboard();
      }, 5000);
    } catch (err: any) {
      setRenewStatusMsg(err.response?.data?.detail || 'Imeshindikana kuanzisha malipo / Payment request failed.');
    } finally {
      setIsRenewing(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setMe(null);
    setSubscription(null);
  };

  const formatCountdown = (totalSeconds: number) => {
    if (totalSeconds <= 0) return '00:00:00';
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  // Unauthenticated OTP Screen
  if (!token) {
    return (
      <div className="min-h-screen bg-background flex flex-col justify-center items-center p-4">
        <div className="w-full max-w-sm bg-card border border-border rounded-2xl shadow-xl overflow-hidden p-6 sm:p-8 space-y-6">
          {/* Brand Header */}
          <div className="text-center space-y-2">
            <div className="h-12 w-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mx-auto shadow-sm">
              <Wifi className="h-6 w-6" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Akaunti Yangu ya Wi-Fi</h1>
            <p className="text-xs text-muted-foreground">
              Customer Self-Service & Subscription Management
            </p>
          </div>

          {otpError && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{otpError}</span>
            </div>
          )}

          {otpStep === 'PHONE' ? (
            <form onSubmit={handleRequestOTP} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Namba ya Simu / Phone Number
                </label>
                <div className="relative">
                  <Smartphone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <input
                    type="tel"
                    required
                    placeholder="07XXXXXXXX au 06XXXXXXXX"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full pl-9 pr-4 py-2.5 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Tutakutumia namba ya uthibitisho kwa ujumbe mfupi (SMS).
                </p>
              </div>

              <button
                type="submit"
                disabled={otpLoading || cooldown > 0}
                className="w-full py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {otpLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <span>Tuma Nambari / Get OTP</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOTP} className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-foreground">
                    Namba ya Uthibitisho (Nambari 6)
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setOtpStep('PHONE');
                      setOtpError(null);
                    }}
                    className="text-xs text-primary hover:underline"
                  >
                    Badili Namba
                  </button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    required
                    maxLength={6}
                    placeholder="123456"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    className="w-full pl-9 pr-4 py-2.5 text-base font-mono text-center tracking-widest rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Ujumbe umetumwa kwa {phone}. Nambari inatumika kwa dakika 5.
                </p>
              </div>

              <button
                type="submit"
                disabled={otpLoading}
                className="w-full py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {otpLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <span>Thibitisha & Fungua / Verify</span>
                    <CheckCircle2 className="h-4 w-4" />
                  </>
                )}
              </button>

              <div className="text-center pt-2">
                {cooldown > 0 ? (
                  <span className="text-xs text-muted-foreground">
                    Unaweza kuomba tena baada ya sekunde {cooldown}
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={handleRequestOTP}
                    className="text-xs text-primary hover:underline font-medium"
                  >
                    Hujapata ujumbe? Bonyeza kutumiwa tena
                  </button>
                )}
              </div>
            </form>
          )}

          <div className="text-center text-[11px] text-muted-foreground border-t border-border pt-4">
            Usimamizi Wi-Fi • Powered by FreeRADIUS & MikroTik
          </div>
        </div>
      </div>
    );
  }

  // Authenticated Portal Dashboard
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center shadow-sm">
              <Wifi className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-foreground leading-none">
                {me?.company_name || 'Usimamizi Wi-Fi'}
              </div>
              <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                {me?.normalized_phone}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchDashboard()}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              title="Refresh status"
            >
              <RefreshCw className={`h-4 w-4 ${loadingDashboard ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
              title="Sign Out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area (Mobile-First) */}
      <main className="max-w-xl mx-auto p-4 space-y-5 pb-12">
        {/* Active Subscription Countdown Card */}
        <div className="p-6 rounded-2xl border border-border bg-gradient-to-br from-card to-accent/20 shadow-md relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Clock className="h-4 w-4 text-primary" />
              <span>Muda Uliobaki / Remaining Time</span>
            </div>
            {subscription && (
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
                subscription.status === 'ACTIVE'
                  ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                  : subscription.status === 'GRACE'
                  ? 'bg-amber-500/15 text-amber-500 border border-amber-500/30'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {subscription.status}
              </span>
            )}
          </div>

          {subscription && remainingSecs > 0 ? (
            <div className="space-y-4">
              <div className="text-center py-2">
                <div className="text-4xl sm:text-5xl font-black font-mono tracking-tight text-foreground">
                  {formatCountdown(remainingSecs)}
                </div>
                <div className="text-sm font-semibold text-primary mt-1">
                  Kifurushi: {subscription.plan_name}
                </div>
              </div>

              <div className="text-xs text-muted-foreground text-center border-t border-border/50 pt-3">
                Mwisho wa Kifurushi / Expiration:{' '}
                <span className="font-semibold text-foreground font-mono">
                  {subscription.current_period_end ? new Date(subscription.current_period_end).toLocaleString() : '—'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center py-6 space-y-2">
              <Zap className="h-10 w-10 text-amber-500 mx-auto opacity-70" />
              <div className="text-base font-bold text-foreground">Hauna Kifurushi Kinachotumika</div>
              <p className="text-xs text-muted-foreground">
                Huna muda wa intaneti unaotumika hivi sasa. Chagua kifurushi hapa chini kuanza.
              </p>
            </div>
          )}
        </div>

        {/* Quick Renewal / Purchase Push Card */}
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-primary" />
              <span>Nunua au Ongeza Kifurushi / Renew</span>
            </h2>
            <span className="text-[11px] text-emerald-500 font-semibold flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Muda haulipuki bure
            </span>
          </div>

          {renewStatusMsg && (
            <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-xs text-foreground flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-primary shrink-0" />
              <span>{renewStatusMsg}</span>
            </div>
          )}

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-muted-foreground mb-1">
                Chagua Kifurushi / Select Plan
              </label>
              <select
                value={renewPlanId || (subscription?.plan_id || '')}
                onChange={(e) => setRenewPlanId(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-xl border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {subscription && (
                  <option value={subscription.plan_id}>
                    Kifurushi Changu: {subscription.plan_name} ({subscription.plan_currency} {subscription.plan_price})
                  </option>
                )}
                {availablePlans.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {p.currency} {Number(p.price).toLocaleString()} ({p.duration_value} {p.duration_unit})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-muted-foreground mb-1">
                Njia ya Malipo / Mobile Money
              </label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setRenewMethod('MPESA')}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all ${
                    renewMethod === 'MPESA'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-background text-muted-foreground hover:text-foreground'
                  }`}
                >
                  M-Pesa
                </button>
                <button
                  type="button"
                  onClick={() => setRenewMethod('AIRTEL_MONEY')}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all ${
                    renewMethod === 'AIRTEL_MONEY'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-background text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Airtel
                </button>
                <button
                  type="button"
                  onClick={() => setRenewMethod('MIXX')}
                  className={`py-2 px-3 rounded-xl border text-xs font-semibold transition-all ${
                    renewMethod === 'MIXX'
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-background text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Mixx / Yas
                </button>
              </div>
            </div>

            <button
              onClick={handleRenew}
              disabled={isRenewing}
              className="w-full py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50 mt-2"
            >
              {isRenewing ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Lipa kwa Simu / Pay with Mobile Money</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </div>

        {/* My Connected Devices Section */}
        <div className="p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
              <Smartphone className="h-4 w-4 text-primary" />
              <span>Vifaa Vyangu / Connected Devices ({devices.length})</span>
            </h2>
          </div>

          <div className="space-y-2.5">
            {devices.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">
                Bado haujaunganisha kifaa chochote.
              </p>
            ) : (
              devices.map((dev) => (
                <div
                  key={dev.id}
                  className="flex items-center justify-between p-3 rounded-xl bg-muted/40 border border-border text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="font-semibold text-foreground flex items-center gap-1.5">
                      <Smartphone className="h-3.5 w-3.5 text-primary" />
                      <span>{dev.device_name || dev.device_type}</span>
                    </div>
                    <div className="font-mono text-[11px] text-muted-foreground">{dev.mac_address}</div>
                  </div>

                  <button
                    onClick={() => handleDisconnectDevice(dev.mac_address)}
                    className="px-2.5 py-1.5 rounded-lg border border-border text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 transition-colors text-[11px] font-semibold"
                    title="Tenganisha kifaa hiki ili uweze kutumia simu au kompyuta nyingine"
                  >
                    Tenganisha
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
};
