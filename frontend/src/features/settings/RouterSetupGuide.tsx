import { useState } from 'react';
import {
  Terminal,
  Copy,
  Check,
  Server,
  Wifi,
  Globe,
  ShieldCheck,
  Zap,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sliders,
  Cable,
  Radio
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs';

export function RouterSetupGuide() {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  // Dynamic Generator State
  const [genRouterUser, setGenRouterUser] = useState('router2');
  const [genRouterIp, setGenRouterIp] = useState('10.8.0.3');
  const [genVpsIp, setGenVpsIp] = useState('23.95.130.161');
  const [genRadiusSecret, setGenRadiusSecret] = useState('UsimamiziRadiusSecret2026!');
  const [genTunnelSecret, setGenTunnelSecret] = useState('UsimamiziRouterSecret2026!');
  const [genHotspotInterface, setGenHotspotInterface] = useState('bridgeLocal');

  const handleCopy = (text: string, sectionId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(sectionId);
    setTimeout(() => setCopiedSection(null), 2500);
  };

  const dynamicBootstrapScript = `# ===============================================================
# USIMAMIZI WI-FI: AUTOMATED HARDWARE BOOTSTRAP FOR ${genRouterUser.toUpperCase()}
# Generated for VPS Gateway: ${genVpsIp} | Tunnel IP: ${genRouterIp}
# ===============================================================

# 1. Establish Encrypted Reverse L2TP Management Tunnel
/interface l2tp-client remove [find name="usimamizi-tunnel"]
/interface l2tp-client add name="usimamizi-tunnel" \\
    connect-to=${genVpsIp} \\
    user="${genRouterUser}" \\
    password="${genTunnelSecret}" \\
    profile=default-encryption \\
    keepalive-timeout=60 \\
    allow=pap,chap,mschap1,mschap2 \\
    disabled=no

# 2. Configure Central FreeRADIUS AAA & RFC 3576 CoA Client
/radius incoming set accept=yes port=3799
/radius remove [find comment~"Usimamizi"]
/radius add service=hotspot \\
    address=10.8.0.1 \\
    secret="${genRadiusSecret}" \\
    authentication-port=1812 \\
    accounting-port=1813 \\
    timeout=3000ms \\
    comment="Usimamizi Central AAA (${genRouterUser})"

# 3. HotSpot Server RADIUS Integration & Interim Accounting
/ip hotspot profile set [find] \\
    use-radius=yes \\
    radius-accounting=yes \\
    radius-interim-update=60s \\
    login-by=http-chap,http-pap,cookie,mac-cookie \\
    split-user-domain=no

# 4. Walled Garden Rules (Snippe Payments & Portal)
/ip hotspot walled-garden remove [find comment~"Usimamizi"]
/ip hotspot walled-garden add dst-host="*swahilicode.tech" action=allow comment="Usimamizi Portal"
/ip hotspot walled-garden add dst-host="*snippe.sh" action=allow comment="Snippe API"
/ip hotspot walled-garden add dst-host="*snippe.me" action=allow comment="Snippe Checkout"
/ip hotspot walled-garden ip add dst-address=${genVpsIp} action=accept comment="Usimamizi VPS IP"
/ip hotspot walled-garden ip add dst-port=8728-8729 protocol=tcp action=accept comment="Allow API"

# 5. Anti-Tethering Lock (Mangle TTL=1)
/ip firewall mangle remove [find comment~"Usimamizi"]
/ip firewall mangle add chain=postrouting out-interface=${genHotspotInterface} \\
    action=change-ttl new-ttl=set:1 passthrough=yes \\
    comment="Usimamizi: Anti-Tethering Lock"

:log info "Usimamizi Router ${genRouterUser} bootstrap applied successfully!"`;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Architecture Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-900 via-blue-900 to-slate-950 p-6 sm:p-8 text-white border border-indigo-800/40 shadow-xl">
        <div className="relative z-10 space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/30 text-xs font-semibold">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            Zero Public IP Architecture • Works on ANY ISP
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            MikroTik Hardware & Network Deployment Guide
          </h2>
          <p className="text-sm text-blue-200/90 max-w-3xl leading-relaxed">
            Every MikroTik router in your fleet connects outbound to your cloud VPS via an encrypted L2TP tunnel. 
            Because connections dial outward from the router, you <strong>never need a public IP, static IP, or port forwarding</strong> from local ISPs (Vodacom, Airtel, Halotel, TTCL, Starlink, or 4G LTE).
          </p>

          {/* Quick Flow Visualization */}
          <div className="pt-4 grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex flex-col items-center text-center">
              <Server className="w-5 h-5 text-indigo-300 mb-1" />
              <span className="font-bold">Cloud VPS</span>
              <span className="text-[11px] text-blue-200 font-mono">23.95.130.161</span>
              <span className="text-[10px] text-emerald-300 mt-1">FreeRADIUS & API</span>
            </div>
            <div className="p-3 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex flex-col items-center text-center">
              <ShieldCheck className="w-5 h-5 text-emerald-400 mb-1" />
              <span className="font-bold">L2TP Tunnel</span>
              <span className="text-[11px] text-blue-200 font-mono">10.8.0.1 ↔ 10.8.0.x</span>
              <span className="text-[10px] text-blue-200 mt-1">Encrypted Tunnel</span>
            </div>
            <div className="p-3 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex flex-col items-center text-center">
              <Globe className="w-5 h-5 text-amber-300 mb-1" />
              <span className="font-bold">Any Upstream ISP</span>
              <span className="text-[11px] text-blue-200">Fiber, 4G/5G, Starlink</span>
              <span className="text-[10px] text-amber-300 mt-1">Auto DHCP / Failover</span>
            </div>
            <div className="p-3 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex flex-col items-center text-center">
              <Wifi className="w-5 h-5 text-purple-300 mb-1" />
              <span className="font-bold">HotSpot Gateway</span>
              <span className="text-[11px] text-blue-200 font-mono">10.5.50.1</span>
              <span className="text-[10px] text-purple-200 mt-1">Captive & Voucher Auth</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Guide Tabs */}
      <Tabs defaultValue="add-router" className="w-full">
        <TabsList className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-muted p-1 rounded-xl">
          <TabsTrigger value="add-router" className="text-xs font-semibold gap-1.5">
            <Server className="w-3.5 h-3.5" /> 1. Add New Router (2 Min)
          </TabsTrigger>
          <TabsTrigger value="isp-switching" className="text-xs font-semibold gap-1.5">
            <Globe className="w-3.5 h-3.5" /> 2. Moving ISPs & Uplinks
          </TabsTrigger>
          <TabsTrigger value="generator" className="text-xs font-semibold gap-1.5">
            <Sliders className="w-3.5 h-3.5" /> 3. Script Generator
          </TabsTrigger>
          <TabsTrigger value="troubleshooting" className="text-xs font-semibold gap-1.5">
            <HelpCircle className="w-3.5 h-3.5" /> 4. Field Troubleshooting
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: ADDING A NEW ROUTER */}
        <TabsContent value="add-router" className="space-y-6 pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                How to Add Any New MikroTik Router in 3 Easy Steps
              </CardTitle>
              <CardDescription>
                Follow this exact 3-step checklist whenever deploying an additional router (e.g. Router 2, Router 3, or a new customer site).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Step 1 */}
              <div className="flex gap-4 p-4 rounded-xl border border-border bg-card">
                <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center shrink-0">
                  1
                </div>
                <div className="space-y-2 flex-1">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-foreground">Register Router in Dashboard</h4>
                    <Badge variant="outline">Step 1</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Go to <strong>Routers ➔ Register Router</strong>:
                  </p>
                  <ul className="text-xs text-muted-foreground list-disc list-inside space-y-1">
                    <li><strong>Device Name:</strong> Give it a descriptive name (e.g. <code>Branch Office Router</code>)</li>
                    <li><strong>Management IP:</strong> Set to the next tunnel IP: <code>10.8.0.3</code> (Router 3: <code>10.8.0.4</code>, etc.)</li>
                    <li><strong>API Port:</strong> <code>8728</code> | <strong>API Username:</strong> <code>admin</code></li>
                  </ul>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex gap-4 p-4 rounded-xl border border-border bg-card">
                <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center shrink-0">
                  2
                </div>
                <div className="space-y-2 flex-1">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-foreground">Add Router Credentials to VPS L2TP Server</h4>
                    <Badge variant="outline">Step 2</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Run this single command on your cloud VPS (<code>root@racknerd-036a7ae</code>):
                  </p>
                  <div className="relative">
                    <pre className="p-3 rounded-lg bg-gray-950 text-green-400 font-mono text-xs overflow-x-auto border border-gray-800">
                      {`echo "router2 * UsimamiziRouterSecret2026! 10.8.0.3" | sudo tee -a /etc/ppp/chap-secrets`}
                    </pre>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="absolute top-1 right-1 h-7 text-xs text-gray-300 hover:text-white"
                      onClick={() => handleCopy('echo "router2 * UsimamiziRouterSecret2026! 10.8.0.3" | sudo tee -a /etc/ppp/chap-secrets', 'step2')}
                    >
                      {copiedSection === 'step2' ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </Button>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    <em>(For router 3, simply change <code>router2</code> to <code>router3</code> and <code>10.8.0.3</code> to <code>10.8.0.4</code>)</em>
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex gap-4 p-4 rounded-xl border border-border bg-card">
                <div className="w-8 h-8 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center shrink-0">
                  3
                </div>
                <div className="space-y-2 flex-1">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-foreground">Paste 1 Command into MikroTik Winbox Terminal</h4>
                    <Badge variant="outline">Step 3</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Open <strong>Winbox ➔ New Terminal</strong> on the new router, and paste:
                  </p>
                  <div className="relative">
                    <pre className="p-3 rounded-lg bg-gray-950 text-green-400 font-mono text-xs overflow-x-auto border border-gray-800">
{`/interface l2tp-client add name="usimamizi-tunnel" connect-to=23.95.130.161 user="router2" password="UsimamiziRouterSecret2026!" profile=default-encryption keepalive-timeout=60 disabled=no
/radius add service=hotspot address=10.8.0.1 secret="UsimamiziRadiusSecret2026!" authentication-port=1812 accounting-port=1813 comment="Usimamizi Central AAA"`}
                    </pre>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="absolute top-1 right-1 h-7 text-xs text-gray-300 hover:text-white"
                      onClick={() => handleCopy(`/interface l2tp-client add name="usimamizi-tunnel" connect-to=23.95.130.161 user="router2" password="UsimamiziRouterSecret2026!" profile=default-encryption keepalive-timeout=60 disabled=no\n/radius add service=hotspot address=10.8.0.1 secret="UsimamiziRadiusSecret2026!" authentication-port=1812 accounting-port=1813 comment="Usimamizi Central AAA"`, 'step3')}
                    >
                      {copiedSection === 'step3' ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </Button>
                  </div>
                  <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1 mt-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Instantly connects! The router will appear ONLINE in your dashboard within 5 seconds.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 2: MOVING BETWEEN ISPS & NETWORKS */}
        <TabsContent value="isp-switching" className="space-y-6 pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Globe className="w-5 h-5 text-blue-500" />
                Moving Between ISPs (Office, Home, Starlink, Mobile Hotspot)
              </CardTitle>
              <CardDescription>
                How your MikroTik automatically reconnects when plugged into different networks or Internet providers.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Method 1: Ethernet Cable */}
                <div className="p-5 rounded-xl border border-border bg-card space-y-3">
                  <div className="flex items-center gap-2 text-sm font-bold text-foreground">
                    <Cable className="w-4 h-4 text-emerald-500" />
                    Method A: Ethernet Cable (ether1)
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Plug an Ethernet cable from your ISP router (Vodacom Fiber, TTCL, Starlink, etc.) into <strong>Port 1 (ether1)</strong> of the MikroTik.
                  </p>
                  <div className="p-3 rounded-lg bg-muted/60 text-xs space-y-1">
                    <div className="font-semibold text-foreground">How it works:</div>
                    <p className="text-muted-foreground text-[11px]">
                      MikroTik runs a DHCP client on <code>ether1</code> with <code>add-default-route=yes</code>. It grabs a local IP, sets the default gateway, and establishes the tunnel to <code>23.95.130.161</code> within ~5 seconds.
                    </p>
                  </div>
                  <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[11px]">
                    100% Plug & Play • No Reconfiguration Needed
                  </Badge>
                </div>

                {/* Method 2: Wireless Station Uplink */}
                <div className="p-5 rounded-xl border border-border bg-card space-y-3">
                  <div className="flex items-center gap-2 text-sm font-bold text-foreground">
                    <Radio className="w-4 h-4 text-blue-500" />
                    Method B: Wireless Uplink (wlan2 Station)
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Connect the MikroTik wirelessly to any nearby 2.4GHz or 5GHz Wi-Fi (e.g. Airtel 5G, phone hotspot, or venue Wi-Fi).
                  </p>
                  <div className="p-3 rounded-lg bg-muted/60 text-xs space-y-1">
                    <div className="font-semibold text-foreground">How to switch Wi-Fi:</div>
                    <ol className="text-muted-foreground text-[11px] list-decimal list-inside space-y-0.5">
                      <li>Go to <strong>Routers ➔ [Your Router] ➔ Interfaces & WAN</strong>.</li>
                      <li>Click <strong>Scan Nearby Networks</strong>.</li>
                      <li>Click any detected SSID, enter the Wi-Fi password, and click <strong>Connect</strong>.</li>
                    </ol>
                  </div>
                  <Badge variant="outline" className="bg-blue-500/10 text-blue-600 border-blue-500/20 text-[11px]">
                    Switches Remotely from Dashboard
                  </Badge>
                </div>
              </div>

              {/* Automatic Failover Note */}
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-200 text-xs space-y-1.5">
                <div className="font-bold flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  Dual-WAN Redundancy (Fiber Primary + 4G/Wi-Fi Backup)
                </div>
                <p className="text-[11px] leading-relaxed">
                  You can leave Ethernet (Port 1) plugged in while also having <code>wlan2</code> configured to your backup 4G router. If your office fiber goes down, the MikroTik automatically routes packets through the backup Wi-Fi uplink, keeping your Hotspot vouchers and portal online without human intervention!
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: DYNAMIC SCRIPT GENERATOR */}
        <TabsContent value="generator" className="space-y-6 pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Sliders className="w-5 h-5 text-purple-500" />
                Custom Router Bootstrap Script Generator
              </CardTitle>
              <CardDescription>
                Customize parameters below to generate a tailored, production-ready RouterOS script for any new router.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Form inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Router Username</label>
                  <input
                    type="text"
                    value={genRouterUser}
                    onChange={(e) => setGenRouterUser(e.target.value)}
                    className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-border bg-background"
                    placeholder="router2"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Assigned Tunnel IP</label>
                  <input
                    type="text"
                    value={genRouterIp}
                    onChange={(e) => setGenRouterIp(e.target.value)}
                    className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-border bg-background"
                    placeholder="10.8.0.3"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">VPS Server IP</label>
                  <input
                    type="text"
                    value={genVpsIp}
                    onChange={(e) => setGenVpsIp(e.target.value)}
                    className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-border bg-background"
                    placeholder="23.95.130.161"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">L2TP Tunnel Secret</label>
                  <input
                    type="text"
                    value={genTunnelSecret}
                    onChange={(e) => setGenTunnelSecret(e.target.value)}
                    className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-border bg-background"
                    placeholder="UsimamiziRouterSecret2026!"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">RADIUS AAA Secret</label>
                  <input
                    type="text"
                    value={genRadiusSecret}
                    onChange={(e) => setGenRadiusSecret(e.target.value)}
                    className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-border bg-background"
                    placeholder="UsimamiziRadiusSecret2026!"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-foreground block mb-1">Hotspot Bridge / Interface</label>
                  <input
                    type="text"
                    value={genHotspotInterface}
                    onChange={(e) => setGenHotspotInterface(e.target.value)}
                    className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-border bg-background"
                    placeholder="bridgeLocal"
                  />
                </div>
              </div>

              {/* Generated Script Box */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                    <Terminal className="w-4 h-4 text-emerald-500" />
                    Paste into Winbox ➔ New Terminal:
                  </span>
                  <Button
                    size="sm"
                    onClick={() => handleCopy(dynamicBootstrapScript, 'genScript')}
                    className="h-8 gap-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    {copiedSection === 'genScript' ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-green-300" /> Copied Script!
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" /> Copy Full Script
                      </>
                    )}
                  </Button>
                </div>
                <pre className="p-4 rounded-xl bg-gray-950 text-green-400 font-mono text-xs overflow-x-auto max-h-96 border border-gray-800 leading-relaxed select-all">
                  {dynamicBootstrapScript}
                </pre>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: FIELD TROUBLESHOOTING */}
        <TabsContent value="troubleshooting" className="space-y-6 pt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <HelpCircle className="w-5 h-5 text-amber-500" />
                Field Technician Troubleshooting Matrix
              </CardTitle>
              <CardDescription>
                Quick solutions for the most common field installation scenarios.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Problem 1 */}
              <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                <div className="font-bold text-sm text-foreground flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                  Router status shows "Unreachable" or "Connection Failed"
                </div>
                <div className="text-xs text-muted-foreground space-y-1 pl-6">
                  <p><strong>Cause:</strong> The router does not have internet access, or the L2TP tunnel client is not running.</p>
                  <p><strong>Fix:</strong> In Winbox Terminal on the router, run:</p>
                  <pre className="p-2 rounded bg-muted font-mono text-[11px] text-foreground mt-1">
{`/ip dhcp-client print
/ping 8.8.8.8 count=3
/interface l2tp-client print`}
                  </pre>
                  <p className="text-[11px] mt-1">
                    If <code>/interface l2tp-client print</code> does not show <strong>R (Running)</strong>, verify that the router can ping <code>23.95.130.161</code>.
                  </p>
                </div>
              </div>

              {/* Problem 2 */}
              <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                <div className="font-bold text-sm text-foreground flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
                  Active Wi-Fi says "Disconnected" in Interfaces & WAN tab
                </div>
                <div className="text-xs text-muted-foreground space-y-1 pl-6">
                  <p><strong>Normal behavior:</strong> If the router is plugged in via <strong>Ethernet Cable (Port 1)</strong>, the Wi-Fi station (<code>wlan2</code>) is idle. Look at <strong>Active Uplink (WAN)</strong> which will show <code>Ethernet Wired (ether1)</code> and <strong>Internet Health: ONLINE</strong>.</p>
                </div>
              </div>

              {/* Problem 3 */}
              <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                <div className="font-bold text-sm text-foreground flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-blue-500 shrink-0" />
                  Customer connects to Wi-Fi but Captive Portal login does not pop up
                </div>
                <div className="text-xs text-muted-foreground space-y-1 pl-6">
                  <p><strong>Cause:</strong> DNS or Walled Garden rule missing, or client is trying to reach an HTTPS site before login.</p>
                  <p><strong>Fix:</strong> Instruct client to open browser and type <code>http://wifi.swahilicode.tech</code> or <code>http://10.5.50.1</code>. Ensure the Walled Garden has <code>*swahilicode.tech</code> whitelisted.</p>
                </div>
              </div>

              {/* Problem 4 */}
              <div className="p-4 rounded-xl border border-border bg-card space-y-2">
                <div className="font-bold text-sm text-foreground flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-purple-500 shrink-0" />
                  Customer enters voucher code but gets "Radius server is not responding"
                </div>
                <div className="text-xs text-muted-foreground space-y-1 pl-6">
                  <p><strong>Cause:</strong> FreeRADIUS service on VPS is stopped or tunnel IP <code>10.8.0.1</code> is unreachable.</p>
                  <p><strong>Fix:</strong> On VPS, run <code>sudo systemctl restart freeradius</code>. On MikroTik, run <code>/ping 10.8.0.1 count=3</code>.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
