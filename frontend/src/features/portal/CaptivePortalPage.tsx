import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import {
  PublicHotspotConfig,
  PublicPlan,
  PublicPurchaseStatusResponse,
  PublicVoucherRedeemResponse,
  CustomerSessionStatus,
  PortalHandoffStatus,
  PublicPortalContextResponse,
} from '../../types';
import {
  Wifi,
  Lock,
  ArrowRight,
  Phone,
  CheckCircle2,
  AlertCircle,
  Clock,
  Activity,
  Globe,
  Power,
  RefreshCw,
  HelpCircle,
  CreditCard,
  Ticket,
  Smartphone,
  Zap,
} from 'lucide-react';

function formatBytes(bytes?: number): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function formatRemainingSeconds(seconds?: number): string {
  if (!seconds || seconds <= 0) return '0s';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (hrs > 0) return `${hrs}h ${mins}m`;
  return `${mins}m`;
}

export const CaptivePortalPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams] = useSearchParams();

  // RouterOS parameters from captive redirect
  const routerLinkLogin = searchParams.get('link-login') || searchParams.get('link-login-only') || '';

  const [hotspot, setHotspot] = useState<PublicHotspotConfig | null>(null);
  const [plans, setPlans] = useState<PublicPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [lang, setLang] = useState<'EN' | 'SW'>('SW');

  // Context & handoff state
  const [contextToken, setContextToken] = useState<string>('');
  const [loginUrl, setLoginUrl] = useState<string>('');
  const [destinationUrl, setDestinationUrl] = useState<string>('https://www.google.com');
  const [handoffStatus, setHandoffStatus] = useState<PortalHandoffStatus>('IDLE');

  // Tab: 'buy' (Self-Service Mobile Money) or 'voucher' (Code Entry)
  const [activeTab, setActiveTab] = useState<'buy' | 'voucher'>('buy');

  // Voucher tab state
  const [voucherCode, setVoucherCode] = useState('');
  const [submittingVoucher, setSubmittingVoucher] = useState(false);
  const [voucherError, setVoucherError] = useState('');

  // Buy package tab state
  const [selectedPlanId, setSelectedPlanId] = useState<string>('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [initiatingPurchase, setInitiatingPurchase] = useState(false);
  const [purchaseError, setPurchaseError] = useState('');

  // Purchase in-flight status & polling
  const [activePurchase, setActivePurchase] = useState<PublicPurchaseStatusResponse | null>(null);
  const [isPollingPurchase, setIsPollingPurchase] = useState(false);

  // Post-login / Status state
  const [connectedSession, setConnectedSession] = useState<{
    voucher: string;
    entitlementRef?: string;
    planName?: string;
    remainingSeconds?: number;
    remainingDataBytes?: number;
  } | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  const routerFormRef = useRef<HTMLFormElement>(null);
  const [handoffCredentials, setHandoffCredentials] = useState<{ username: string; password: string; actionUrl: string } | null>(null);

  // Fetch HotSpot config and context
  const fetchHotspotConfigAndPlans = useCallback(async () => {
    if (!slug) return;
    try {
      setLoading(true);
      setNotFound(false);

      const linkLoginParam = searchParams.get('link-login') || searchParams.get('link-login-only') || '';
      const linkOrigParam = searchParams.get('link-orig') || searchParams.get('dst') || '';
      const macParam = searchParams.get('mac') || '';
      const ipParam = searchParams.get('ip') || '';

      const storageKey = `usimamizi_portal_ctx_${slug}`;
      let cachedCtx: Record<string, string> | null = null;
      try {
        const raw = sessionStorage.getItem(storageKey);
        if (raw) cachedCtx = JSON.parse(raw);
      } catch {
        // ignore
      }

      const payload = {
        link_login: linkLoginParam || cachedCtx?.link_login || '',
        link_orig: linkOrigParam || cachedCtx?.link_orig || '',
        mac: macParam || cachedCtx?.mac || '',
        ip: ipParam || cachedCtx?.ip || '',
      };

      const contextRes = await fetch(`/api/v1/public/hotspots/${slug}/portal-context/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (contextRes.ok) {
        const ctxData: PublicPortalContextResponse = await contextRes.json();
        setHotspot(ctxData.hotspot);
        setPlans(ctxData.plans || []);
        if (ctxData.plans && ctxData.plans.length > 0) {
          setSelectedPlanId(ctxData.plans[0].id);
        }
        setContextToken(ctxData.context_token || '');
        setLoginUrl(ctxData.login_url || '');
        if (ctxData.session_context?.link_orig) {
          setDestinationUrl(ctxData.session_context.link_orig);
        }
        if (ctxData.hotspot.default_language) {
          setLang(ctxData.hotspot.default_language);
        }
        try {
          sessionStorage.setItem(storageKey, JSON.stringify({
            context_token: ctxData.context_token,
            link_login: ctxData.login_url,
            link_orig: ctxData.session_context?.link_orig,
            mac: ctxData.session_context?.mac,
            ip: ctxData.session_context?.ip,
          }));
        } catch {
          // ignore
        }
      } else {
        const [portalRes, plansRes] = await Promise.all([
          fetch(`/api/v1/public/hotspots/${slug}/portal/`),
          fetch(`/api/v1/public/hotspots/${slug}/plans/`),
        ]);

        if (!portalRes.ok) {
          setNotFound(true);
          return;
        }
        const portalData: PublicHotspotConfig = await portalRes.json();
        setHotspot(portalData);
        if (portalData.login_url) setLoginUrl(portalData.login_url);
        if (portalData.context_token) setContextToken(portalData.context_token);
        if (portalData.default_language) setLang(portalData.default_language);

        if (plansRes.ok) {
          const plansData: PublicPlan[] = await plansRes.json();
          setPlans(plansData);
          if (plansData.length > 0) {
            setSelectedPlanId(plansData[0].id);
          }
        }
      }

      // Check for active session from URL query params or localStorage
      const statusParam = searchParams.get('status');
      const voucherParam = searchParams.get('voucher') || searchParams.get('session');
      const activeSessionKey = `usimamizi_active_session_${slug}`;

      let candidateVoucher = voucherParam;
      if (!candidateVoucher) {
        try {
          const cachedSession = localStorage.getItem(activeSessionKey);
          if (cachedSession) {
            const parsed = JSON.parse(cachedSession);
            if (parsed?.voucher) candidateVoucher = parsed.voucher;
          }
        } catch {
          // ignore
        }
      }

      if (candidateVoucher) {
        try {
          const statusRes = await fetch(
            `/api/v1/public/hotspots/${slug}/status/?username=${encodeURIComponent(candidateVoucher)}`
          );
          if (statusRes.ok) {
            const statusData: CustomerSessionStatus = await statusRes.json();
            if (
              statusData.connected ||
              statusParam === 'connected' ||
              (statusData.remaining_seconds && statusData.remaining_seconds > 0)
            ) {
              setConnectedSession({
                voucher: candidateVoucher,
                planName: statusData.plan_name,
                remainingSeconds: statusData.remaining_seconds,
                remainingDataBytes: statusData.remaining_data_bytes,
              });
              setHandoffStatus('CONNECTED');
              localStorage.setItem(activeSessionKey, JSON.stringify({ voucher: candidateVoucher }));
            } else {
              localStorage.removeItem(activeSessionKey);
            }
          }
        } catch {
          // ignore status fetch error
        }
      }
    } catch (err) {
      console.error('Failed to load hotspot config and plans', err);
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  }, [slug, searchParams]);

  useEffect(() => {
    fetchHotspotConfigAndPlans();
  }, [fetchHotspotConfigAndPlans]);

  // Submit RouterOS login form when handoff credentials are ready
  useEffect(() => {
    if (handoffCredentials && routerFormRef.current) {
      try {
        routerFormRef.current.submit();
      } catch (err) {
        console.warn('Router login form auto-submit deferred:', err);
      }
    }
  }, [handoffCredentials]);

  // Safe router handoff trigger
  const triggerHandoff = useCallback((username: string, password: string, actionUrlOverride?: string) => {
    const targetActionUrl =
      actionUrlOverride ||
      loginUrl ||
      routerLinkLogin ||
      hotspot?.login_url ||
      hotspot?.router_login_url ||
      (hotspot?.gateway_ip ? `http://${hotspot.gateway_ip}/login` : 'http://10.5.50.1/login');

    setHandoffStatus('ACTIVATING');
    setHandoffCredentials({
      username,
      password,
      actionUrl: targetActionUrl,
    });

    if (slug) {
      try {
        localStorage.setItem(`usimamizi_active_session_${slug}`, JSON.stringify({ voucher: username }));
      } catch {
        // ignore
      }
    }

    // Safety fallback: if top-level navigation has not redirected after 6s, show manual retry
    setTimeout(() => {
      setHandoffStatus((prev) => (prev === 'ACTIVATING' ? 'FAILED' : prev));
    }, 6000);
  }, [loginUrl, routerLinkLogin, hotspot, slug]);

  // Polling for active purchase
  useEffect(() => {
    if (!isPollingPurchase || !activePurchase) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/public/purchases/${activePurchase.reference}/status/`);
        if (res.ok) {
          const statusData: PublicPurchaseStatusResponse = await res.json();
          setActivePurchase(statusData);

          if (statusData.status === 'FULFILLED') {
            setIsPollingPurchase(false);
            const accessCode = statusData.voucher_code;
            if (accessCode && hotspot) {
              setConnectedSession({
                voucher: accessCode,
                planName: statusData.plan_name,
              });
              const targetActionUrl =
                statusData.router_login_url ||
                loginUrl ||
                routerLinkLogin ||
                hotspot.login_url ||
                hotspot.router_login_url;
              triggerHandoff(accessCode, accessCode, targetActionUrl);
            }
          } else if (statusData.status === 'FAILED' || statusData.status === 'EXPIRED') {
            setIsPollingPurchase(false);
            setPurchaseError(
              statusData.error_message ||
              (lang === 'SW' ? 'Malipo yameshindikana. Tafadhali jaribu tena.' : 'Payment failed or timed out. Please try again.')
            );
          }
        }
      } catch (pollErr) {
        console.error('Error polling purchase status', pollErr);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [isPollingPurchase, activePurchase, hotspot, routerLinkLogin, loginUrl, lang, triggerHandoff]);

  const handleVoucherChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
    if (val.length === 4 && !val.includes('-') && voucherCode.length === 3) {
      val = val + '-';
    }
    setVoucherCode(val);
    setVoucherError('');
  };

  const handleConnectVoucher = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!voucherCode.trim() || !hotspot || submittingVoucher) return;

    try {
      setSubmittingVoucher(true);
      setVoucherError('');

      const res = await fetch(`/api/v1/public/hotspots/${hotspot.slug}/voucher/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voucher_code: voucherCode.trim(),
          language: lang,
          context_token: contextToken,
          link_login: loginUrl || routerLinkLogin,
        }),
      });

      const data: PublicVoucherRedeemResponse = await res.json();
      if (res.ok && data.success && data.username && data.password) {
        setConnectedSession({
          voucher: data.username,
          entitlementRef: data.entitlement_reference,
          planName: data.plan_name,
          remainingSeconds: data.remaining_seconds,
          remainingDataBytes: data.remaining_data_bytes,
        });

        const targetActionUrl =
          data.router_login_url ||
          loginUrl ||
          hotspot.login_url ||
          hotspot.router_login_url;
        triggerHandoff(data.username, data.password, targetActionUrl);
      } else {
        setVoucherError(data.message || (lang === 'SW' ? 'Vocha si sahihi.' : 'Invalid voucher code.'));
      }
    } catch (err: unknown) {
      let msg = lang === 'SW' ? 'Imeshindwa kuthibitisha vocha. Tafadhali jaribu tena.' : 'Failed to validate voucher. Please try again.';
      if (err && typeof err === 'object' && 'message' in err) {
        msg = (err as { message?: string }).message || msg;
      }
      setVoucherError(msg);
    } finally {
      setSubmittingVoucher(false);
    }
  };

  const handleInitiatePurchase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlanId || !customerPhone.trim() || !hotspot || initiatingPurchase) return;

    try {
      setInitiatingPurchase(true);
      setPurchaseError('');

      const res = await fetch(`/api/v1/public/hotspots/${hotspot.slug}/purchases/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: selectedPlanId,
          customer_phone: customerPhone.trim(),
          client_mac: searchParams.get('mac') || '',
          ip_address: searchParams.get('ip') || null,
        }),
      });

      const data = await res.json();
      if (res.ok && data.purchase_reference) {
        setActivePurchase({
          reference: data.purchase_reference,
          status: data.status,
          amount: String(data.amount),
          currency: data.currency,
          customer_phone: data.customer_phone,
          plan_name: plans.find((p) => p.id === selectedPlanId)?.name || 'Wi-Fi Package',
          checkout_url: data.checkout_url,
          created_at: new Date().toISOString(),
        });
        setIsPollingPurchase(true);
      } else {
        setPurchaseError(data.detail || (lang === 'SW' ? 'Imeshindwa kutuma ombi la malipo.' : 'Failed to initiate mobile money payment.'));
      }
    } catch (err: unknown) {
      let msg = lang === 'SW' ? 'Hitilafu ya mtandao. Tafadhali jaribu tena.' : 'Network error. Please try again.';
      if (err && typeof err === 'object' && 'message' in err) {
        msg = (err as { message?: string }).message || msg;
      }
      setPurchaseError(msg);
    } finally {
      setInitiatingPurchase(false);
    }
  };

  const checkLiveStatus = async () => {
    if (!connectedSession || !hotspot) return;
    try {
      setStatusLoading(true);
      const res = await fetch(`/api/v1/public/hotspots/${hotspot.slug}/status/?username=${encodeURIComponent(connectedSession.voucher)}`);
      if (res.ok) {
        const data: CustomerSessionStatus = await res.json();
        setConnectedSession((prev) => (prev ? {
          ...prev,
          planName: data.plan_name || prev.planName,
          remainingSeconds: data.remaining_seconds !== undefined ? data.remaining_seconds : prev.remainingSeconds,
          remainingDataBytes: data.remaining_data_bytes !== undefined ? data.remaining_data_bytes : prev.remainingDataBytes,
        } : null));
      }
    } catch (err) {
      console.error('Status check error', err);
    } finally {
      setStatusLoading(false);
    }
  };

  // Live countdown timer for active session
  useEffect(() => {
    if (!connectedSession || connectedSession.remainingSeconds === undefined || connectedSession.remainingSeconds <= 0) return;
    const timer = setInterval(() => {
      setConnectedSession((prev) => {
        if (!prev || prev.remainingSeconds === undefined || prev.remainingSeconds <= 0) return prev;
        return { ...prev, remainingSeconds: Math.max(0, prev.remainingSeconds - 1) };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [connectedSession?.remainingSeconds]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-slate-100">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500 mb-3" />
        <p className="text-xs text-slate-400 font-medium">
          {lang === 'SW' ? 'Inapakia Tovuti ya Wi-Fi…' : 'Connecting to Wi-Fi Portal…'}
        </p>
      </div>
    );
  }

  if (notFound || !hotspot) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-center">
        <div className="max-w-sm w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
          <div className="w-12 h-12 rounded-full bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h1 className="text-lg font-bold text-slate-100">HotSpot Not Found</h1>
          <p className="text-xs text-slate-400 leading-relaxed">
            The requested Wi-Fi portal is inactive or does not exist. Please reconnect to the Wi-Fi network.
          </p>
        </div>
      </div>
    );
  }

  const brandColor = hotspot.primary_color || '#2563eb';
  const brandName = hotspot.brand_name || hotspot.name || hotspot.company_name;
  const gatewayHost = hotspot.gateway_ip || '10.5.50.1';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between items-center p-4 sm:p-6 selection:bg-blue-600 selection:text-white">
      {/* Direct RouterOS Login Form for top-level navigation handoff */}
      {handoffCredentials && (
        <form
          ref={routerFormRef}
          method="POST"
          action={handoffCredentials.actionUrl}
          className="hidden"
        >
          <input type="hidden" name="username" value={handoffCredentials.username} />
          <input type="hidden" name="password" value={handoffCredentials.password} />
          <input
            type="hidden"
            name="dst"
            value={`${window.location.origin}/p/${slug}?status=connected&voucher=${encodeURIComponent(handoffCredentials.username)}`}
          />
        </form>
      )}

      {/* Top Bar: SSID badge & Language Switcher */}
      <div className="w-full max-w-md flex items-center justify-between text-xs text-slate-400 pt-2 pb-4">
        <div className="flex items-center gap-1.5 font-medium">
          <Wifi className="h-3.5 w-3.5 text-emerald-400" />
          <span className="truncate max-w-[200px]">{hotspot.ssid}</span>
        </div>

        <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5">
          <button
            type="button"
            onClick={() => setLang('EN')}
            className={`px-2 py-0.5 rounded text-[11px] font-bold transition-colors ${
              lang === 'EN' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => setLang('SW')}
            className={`px-2 py-0.5 rounded text-[11px] font-bold transition-colors ${
              lang === 'SW' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            SW
          </button>
        </div>
      </div>

      {/* Main Portal Container */}
      <div className="w-full max-w-md my-auto">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-5 sm:p-6 space-y-5">
          {/* Header Branding */}
          <div className="text-center space-y-1.5">
            {hotspot.logo_url ? (
              <img src={hotspot.logo_url} alt={brandName} className="h-12 max-w-[160px] mx-auto object-contain mb-1" />
            ) : (
              <div
                style={{ backgroundColor: `${brandColor}20`, color: brandColor, borderColor: `${brandColor}40` }}
                className="w-12 h-12 rounded-2xl border flex items-center justify-center mx-auto shadow-inner mb-2"
              >
                <Wifi className="h-6 w-6" />
              </div>
            )}

            <h1 className="text-base font-bold tracking-tight text-slate-100">{brandName}</h1>
            <p className="text-xs text-slate-400 leading-relaxed px-1">
              {hotspot.welcome_text || (lang === 'SW' ? 'Nunua kifurushi au weka vocha kuanza kutumia intaneti.' : 'Purchase a package or enter your voucher code.')}
            </p>
          </div>

          {/* Screen 1: Activation In-Progress State */}
          {handoffStatus === 'ACTIVATING' ? (
            <div className="space-y-4 pt-2 text-center animate-in fade-in zoom-in duration-200">
              <div className="rounded-xl bg-blue-500/10 border border-blue-500/30 p-6 space-y-3.5">
                <RefreshCw className="h-10 w-10 animate-spin text-blue-400 mx-auto" />
                <div>
                  <h2 className="text-sm font-bold text-blue-300">
                    {lang === 'SW' ? 'Inawasha Wi-Fi Yako…' : 'Activating Your Wi-Fi…'}
                  </h2>
                  <p className="text-xs text-slate-300 leading-relaxed mt-1">
                    {lang === 'SW'
                      ? 'Inatuma taarifa kwenye kisanduku cha mtandao. Kama ukurasa haujaondoka, bofya kitufe cha chini:'
                      : 'Connecting your device to the hotspot gateway. If not redirected automatically, tap below:'}
                  </p>
                </div>

                {connectedSession?.voucher && (
                  <div className="text-xs font-mono font-bold text-slate-300 bg-slate-950/60 py-1.5 px-3 rounded-md inline-block border border-slate-800">
                    {connectedSession.voucher}
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => {
                    if (routerFormRef.current) {
                      routerFormRef.current.submit();
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-lg active:scale-[0.98] transition-all"
                >
                  <span>{lang === 'SW' ? 'Unganisha Sasa (Bofya Hapa)' : 'Complete Connection (Tap Here)'}</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          ) : handoffStatus === 'FAILED' ? (
            /* Screen 2: Handoff Failure & Safe Retry State */
            <div className="space-y-4 pt-1 animate-in fade-in zoom-in duration-200">
              <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-5 text-center space-y-2.5">
                <AlertCircle className="h-8 w-8 text-amber-400 mx-auto" />
                <h2 className="text-sm font-bold text-amber-300">
                  {lang === 'SW' ? 'Kifurushi Kiko Tayari' : 'Access Ready, Pending Router Handoff'}
                </h2>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {lang === 'SW'
                    ? 'Kifurushi chako kimewezeshwa, lakini kisanduku hakijaunganisha kiotomatiki. Bonyeza kitufe hapa chini kurudia muunganisho bila malipo mapya.'
                    : 'Your access pass is activated, but the router could not complete the connection automatically. Click below to retry.'}
                </p>
                {connectedSession?.voucher && (
                  <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-2.5 mt-2">
                    <p className="text-[11px] text-slate-400 font-medium">
                      {lang === 'SW' ? 'Nambari Yako ya Kuingia:' : 'Your Access Passcode:'}
                    </p>
                    <p className="text-sm font-mono font-bold text-blue-400 tracking-wider">
                      {connectedSession.voucher}
                    </p>
                  </div>
                )}
              </div>

              <div className="space-y-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    if (connectedSession) {
                      triggerHandoff(connectedSession.voucher, connectedSession.voucher);
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md transition-all"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>{lang === 'SW' ? 'Rudia Kuunganisha (Retry)' : 'Retry Connection'}</span>
                </button>

                <a
                  href={`/p/${slug}/account`}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs font-semibold transition-colors"
                >
                  <span>{lang === 'SW' ? 'Fungua Akaunti Yangu' : 'Go to My Account'}</span>
                </a>
              </div>
            </div>
          ) : connectedSession && (handoffStatus === 'CONNECTED' || handoffStatus === 'IDLE') ? (
            /* Screen 3: Connected State Screen */
            <div className="space-y-4 pt-1 animate-in fade-in zoom-in duration-200">
              <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-4 text-center space-y-2">
                <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto" />
                <div>
                  <h2 className="text-sm font-bold text-emerald-400">
                    {lang === 'SW' ? 'Umeunganishwa Kikamilifu!' : 'Connected to Internet'}
                  </h2>
                  <p className="text-xs text-slate-300 font-mono font-bold mt-1 tracking-wider bg-slate-950/60 py-1 px-3 rounded-md inline-block border border-slate-800">
                    {connectedSession.voucher}
                  </p>
                </div>
              </div>

              <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-3.5 space-y-2.5 text-xs">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <Activity className="h-3.5 w-3.5 text-blue-400" />
                    {lang === 'SW' ? 'Kifurushi' : 'Package'}
                  </span>
                  <span className="font-semibold text-slate-200">{connectedSession.planName || 'High-Speed Wi-Fi'}</span>
                </div>

                {connectedSession.remainingSeconds !== undefined && connectedSession.remainingSeconds !== null && (
                  <div className="flex items-center justify-between text-slate-400 pt-2 border-t border-slate-800/60">
                    <span className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-amber-400" />
                      {lang === 'SW' ? 'Muda Uliobaki' : 'Time Remaining'}
                    </span>
                    <span className="font-mono font-bold text-slate-200">
                      {formatRemainingSeconds(connectedSession.remainingSeconds)}
                    </span>
                  </div>
                )}

                {connectedSession.remainingDataBytes !== undefined && connectedSession.remainingDataBytes !== null && (
                  <div className="flex items-center justify-between text-slate-400 pt-2 border-t border-slate-800/60">
                    <span className="flex items-center gap-1.5">
                      <Globe className="h-3.5 w-3.5 text-emerald-400" />
                      {lang === 'SW' ? 'Bando Lililobaki' : 'Data Remaining'}
                    </span>
                    <span className="font-mono font-bold text-slate-200">
                      {formatBytes(connectedSession.remainingDataBytes)}
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-2 pt-1">
                <a
                  href={destinationUrl || 'https://www.google.com'}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md transition-all"
                >
                  <Globe className="h-4 w-4" />
                  <span>{lang === 'SW' ? 'Fungua Intaneti (Anza Kutumia)' : 'Start Browsing (Open Web)'}</span>
                </a>

                <button
                  type="button"
                  onClick={() => {
                    if (connectedSession) {
                      triggerHandoff(connectedSession.voucher, connectedSession.voucher);
                    }
                  }}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 text-slate-400 hover:text-slate-200 text-[11px] font-medium"
                >
                  <RefreshCw className="h-3 w-3 text-blue-400" />
                  <span>{lang === 'SW' ? 'Rudia kutuma muunganisho kwa Kisanduku' : 'Re-send Router Login'}</span>
                </button>

                <a
                  href={`http://${gatewayHost}/logout`}
                  onClick={() => {
                    try {
                      if (slug) localStorage.removeItem(`usimamizi_active_session_${slug}`);
                    } catch {
                      // ignore
                    }
                  }}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 text-xs font-semibold transition-colors"
                >
                  <Power className="h-3.5 w-3.5" />
                  <span>{lang === 'SW' ? 'Toka kwenye Mtandao (Logout)' : 'Disconnect Session'}</span>
                </a>

                <button
                  type="button"
                  onClick={checkLiveStatus}
                  disabled={statusLoading}
                  className="w-full flex items-center justify-center gap-1.5 py-1 text-slate-400 hover:text-slate-200 text-[11px] font-medium"
                >
                  <RefreshCw className={`h-3 w-3 ${statusLoading ? 'animate-spin text-blue-400' : 'text-blue-400'}`} />
                  <span>{lang === 'SW' ? 'Hakiki Hali ya Muunganisho (Refresh)' : 'Refresh Status'}</span>
                </button>

                <a
                  href={`http://${gatewayHost}/status`}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full flex items-center justify-center gap-1.5 py-1 text-slate-500 hover:text-slate-300 text-[10px] font-medium underline underline-offset-2"
                >
                  <Activity className="h-3 w-3 text-emerald-400" />
                  <span>{lang === 'SW' ? `Ukurasa wa Moja kwa Moja wa Router (${gatewayHost}/status)` : `Router Live Status Page (${gatewayHost}/status)`}</span>
                </a>

                <button
                  type="button"
                  onClick={() => setHandoffStatus('FAILED')}
                  className="w-full py-1 text-slate-500 hover:text-amber-400 text-[10px] font-medium transition-colors"
                >
                  {lang === 'SW' ? 'Tatizo la kuunganisha? Bonyeza hapa' : 'Trouble connecting? Click here'}
                </button>
              </div>
            </div>
          ) : activePurchase && isPollingPurchase ? (
            /* Screen 4: USSD Payment Prompt & Polling Screen */
            <div className="space-y-4 pt-1 text-center animate-in fade-in duration-200">
              <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 space-y-3">
                <div className="relative w-12 h-12 mx-auto flex items-center justify-center">
                  <Smartphone className="h-8 w-8 text-blue-400 animate-pulse" />
                  <span className="absolute -top-1 -right-1 flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                  </span>
                </div>

                <div>
                  <h3 className="text-sm font-bold text-blue-300">
                    {lang === 'SW' ? 'Ombi la Malipo Limetumwa!' : 'Payment Prompt Sent!'}
                  </h3>
                  <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                    {lang === 'SW'
                      ? `Tafadhali angalia simu yako (${activePurchase.customer_phone}) na uweke PIN yako ya Tigopesa, M-Pesa, au Airtel Money kuidhinisha TZS ${parseFloat(activePurchase.amount).toLocaleString()}.`
                      : `Please check your phone (${activePurchase.customer_phone}) and enter your Mobile Money PIN to authorize TZS ${parseFloat(activePurchase.amount).toLocaleString()}.`}
                  </p>
                </div>

                <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400 font-medium">
                  <RefreshCw className="h-3.5 w-3.5 animate-spin text-blue-400" />
                  <span>{lang === 'SW' ? 'Inasubiri uthibitisho wa malipo…' : 'Waiting for network confirmation…'}</span>
                </div>
              </div>

              {activePurchase.checkout_url && (
                <a
                  href={activePurchase.checkout_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block text-xs font-semibold text-blue-400 underline hover:text-blue-300"
                >
                  {lang === 'SW' ? 'Fungua Ukurasa wa Malipo' : 'Open Hosted Payment Link'}
                </a>
              )}

              <button
                type="button"
                onClick={() => {
                  setIsPollingPurchase(false);
                  setActivePurchase(null);
                }}
                className="text-xs text-slate-400 hover:text-slate-200 underline pt-1"
              >
                {lang === 'SW' ? 'Ghairi au Jaribu Nambari Nyingine' : 'Cancel or Change Phone'}
              </button>
            </div>
          ) : (
            /* Screen 5: Purchase vs Voucher Tabs */
            <div className="space-y-4">
              <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
                <button
                  type="button"
                  onClick={() => setActiveTab('buy')}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-all ${
                    activeTab === 'buy' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <CreditCard className="h-3.5 w-3.5" />
                  <span>{lang === 'SW' ? 'Nunua Kifurushi' : 'Buy Package'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('voucher')}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-bold transition-all ${
                    activeTab === 'voucher' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Ticket className="h-3.5 w-3.5" />
                  <span>{lang === 'SW' ? 'Nina Vocha' : 'Have a Voucher'}</span>
                </button>
              </div>

              {activeTab === 'buy' ? (
                /* Buy Internet Package Form */
                <form onSubmit={handleInitiatePurchase} className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300 block">
                      {lang === 'SW' ? 'Chagua Kifurushi cha Intaneti' : 'Select Internet Package'}
                    </label>

                    {plans.length === 0 ? (
                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-center text-xs text-slate-400">
                        {lang === 'SW' ? 'Hakuna vifurushi vinavyopatikana hivi sasa.' : 'No packages currently available for purchase.'}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-1">
                        {plans.map((plan) => {
                          const isSelected = selectedPlanId === plan.id;
                          return (
                            <div
                              key={plan.id}
                              onClick={() => setSelectedPlanId(plan.id)}
                              className={`cursor-pointer p-3 rounded-xl border text-xs transition-all flex items-center justify-between ${
                                isSelected
                                  ? 'bg-blue-600/10 border-blue-500 shadow-sm'
                                  : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                              }`}
                            >
                              <div className="space-y-0.5">
                                <div className="font-bold text-slate-100 flex items-center gap-1.5">
                                  <span>{plan.name}</span>
                                  {plan.download_speed_kbps && (
                                    <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.2 rounded">
                                      {plan.download_speed_kbps >= 1000
                                        ? `${(plan.download_speed_kbps / 1000).toFixed(0)} Mbps`
                                        : `${plan.download_speed_kbps} Kbps`}
                                    </span>
                                  )}
                                </div>
                                <div className="text-[11px] text-slate-400">
                                  {plan.duration_value} {plan.duration_unit.toLowerCase()} •{' '}
                                  {plan.data_limit_bytes ? formatBytes(plan.data_limit_bytes) : (lang === 'SW' ? 'Bila Kikomo' : 'Unlimited')}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="font-bold text-sm text-blue-400">
                                  {parseFloat(plan.price).toLocaleString()} {plan.currency}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Mobile Money Phone Input */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-slate-300">
                        {lang === 'SW' ? 'Nambari ya Simu (M-Pesa, Airtel, Yas, Halotel)' : 'Mobile Money Phone Number'}
                      </label>
                    </div>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                        <Smartphone className="h-4 w-4" />
                      </div>
                      <input
                        type="tel"
                        required
                        value={customerPhone}
                        onChange={(e) => setCustomerPhone(e.target.value)}
                        placeholder="0712 345 678 au 0687..."
                        className="w-full pl-9 pr-3 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder:text-slate-600 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <p className="text-[10px] text-slate-400">
                      {lang === 'SW'
                        ? 'Utapokea ujumbe kwenye simu yako kuthibitisha malipo kwa PIN yako.'
                        : 'You will receive an automatic prompt on your phone to enter your PIN.'}
                    </p>
                  </div>

                  {purchaseError && (
                    <div className="p-3 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-start gap-2 text-xs text-rose-300">
                      <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                      <span>{purchaseError}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={initiatingPurchase || !selectedPlanId || !customerPhone.trim()}
                    style={{ backgroundColor: brandColor }}
                    className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-white font-bold text-xs shadow-lg hover:opacity-90 active:scale-[0.99] disabled:opacity-50 transition-all"
                  >
                    {initiatingPurchase ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>{lang === 'SW' ? 'Inatuma Ombi la Malipo…' : 'Sending Payment Request…'}</span>
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4" />
                        <span>{lang === 'SW' ? 'Lipa kwa Simu & Unganisha' : 'Pay via Mobile Money & Connect'}</span>
                      </>
                    )}
                  </button>
                </form>
              ) : (
                /* Voucher Code Entry Form */
                <form onSubmit={handleConnectVoucher} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-300 block">
                      {lang === 'SW' ? 'Weka Nambari ya Vocha' : 'Enter Voucher Code'}
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                        <Lock className="h-4 w-4" />
                      </div>
                      <input
                        type="text"
                        required
                        value={voucherCode}
                        onChange={handleVoucherChange}
                        placeholder="XXXX-XXXX"
                        maxLength={16}
                        autoFocus
                        autoComplete="off"
                        className="w-full pl-10 pr-3 py-3 bg-slate-950 border border-slate-700/80 rounded-xl text-slate-100 placeholder:text-slate-600 font-mono font-bold tracking-widest text-center text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-inner"
                      />
                    </div>
                  </div>

                  {voucherError && (
                    <div className="p-3 bg-rose-500/15 border border-rose-500/30 rounded-xl flex items-start gap-2.5 text-xs text-rose-300">
                      <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                      <span>{voucherError}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={submittingVoucher || !voucherCode.trim()}
                    style={{ backgroundColor: brandColor }}
                    className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-white font-bold text-xs shadow-lg hover:opacity-90 active:scale-[0.99] disabled:opacity-50 transition-all"
                  >
                    {submittingVoucher ? (
                      <>
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        <span>{lang === 'SW' ? 'Inaunganisha…' : 'Connecting…'}</span>
                      </>
                    ) : (
                      <>
                        <span>{lang === 'SW' ? 'Unganisha Intaneti' : 'Connect Wi-Fi'}</span>
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* Support Contact */}
              {hotspot.support_phone && (
                <div className="pt-2 text-center text-xs text-slate-400 border-t border-slate-800/80">
                  <div className="flex items-center justify-center gap-1 text-[11px] text-slate-500 mb-1">
                    <HelpCircle className="h-3 w-3" />
                    <span>{lang === 'SW' ? 'Unahitaji msaada?' : 'Need support?'}</span>
                  </div>
                  <a
                    href={`tel:${hotspot.support_phone}`}
                    className="inline-flex items-center gap-1.5 font-semibold text-slate-300 hover:text-blue-400 transition-colors"
                  >
                    <Phone className="h-3 w-3 text-blue-400" />
                    <span>{hotspot.support_phone}</span>
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="w-full max-w-md text-center py-4 space-y-1.5">
        <div className="flex items-center justify-center gap-3 text-[11px] text-slate-500">
          {hotspot.terms_url && (
            <a href={hotspot.terms_url} target="_blank" rel="noreferrer" className="hover:text-slate-300 transition-colors">
              {lang === 'SW' ? 'Vigezo na Masharti' : 'Terms'}
            </a>
          )}
          {hotspot.terms_url && hotspot.privacy_url && <span>•</span>}
          {hotspot.privacy_url && (
            <a href={hotspot.privacy_url} target="_blank" rel="noreferrer" className="hover:text-slate-300 transition-colors">
              {lang === 'SW' ? 'Faragha' : 'Privacy'}
            </a>
          )}
        </div>
        <p className="text-[10px] text-slate-600 tracking-wide">
          Powered by <span className="font-semibold text-slate-500">Usimamizi Wi-Fi</span>
        </p>
      </footer>
    </div>
  );
};
