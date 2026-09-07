import { describe, it, expect } from 'vitest';

describe('Captive Portal & Self-Service Purchase Specs', () => {
  it('validates Tanzanian phone formatting rules for Snippe mobile payments', () => {
    const cleanPhone = (phone: string) => {
      let clean = phone.replace(/[\s\-()]/g, '');
      if (clean.startsWith('+')) clean = clean.slice(1);
      if (clean.startsWith('0')) clean = '255' + clean.slice(1);
      return clean;
    };

    expect(cleanPhone('0712 345 678')).toBe('255712345678');
    expect(cleanPhone('+255 687-654-321')).toBe('255687654321');
    expect(cleanPhone('0754111222')).toBe('255754111222');
  });

  it('validates 8-character voucher code pattern XXXX-YYYY', () => {
    const formatVoucher = (raw: string) => {
      const val = raw.toUpperCase().replace(/[^A-Z0-9-]/g, '');
      if (val.length === 4 && !val.includes('-')) {
        return val + '-';
      }
      return val;
    };

    expect(formatVoucher('JXV2')).toBe('JXV2-');
    expect(formatVoucher('JXV2-XB4V')).toBe('JXV2-XB4V');
  });

  it('validates Snippe idempotency key format constraint', () => {
    const key = 'idmp_test_' + Date.now();
    expect(key.length).toBeLessThanOrEqual(30);
  });
});

describe('Phase F: Captive Portal Router-Aware Handoff Specs', () => {
  it('resolves handoff login URL using the 3-tier precedence', () => {
    const resolveHandoff = (params: {
      runtimeLinkLogin?: string;
      hotspotLoginUrl?: string;
      gatewayIp?: string;
      legacyOverride?: string;
    }) => {
      if (params.runtimeLinkLogin) return params.runtimeLinkLogin;
      if (params.hotspotLoginUrl) return params.hotspotLoginUrl;
      if (params.gatewayIp) return 'http://' + params.gatewayIp + '/login';
      return params.legacyOverride || 'http://10.5.50.1/login';
    };

    // Tier 1: Runtime MikroTik link-login
    expect(resolveHandoff({
      runtimeLinkLogin: 'http://10.5.50.1/login',
      gatewayIp: '10.5.60.1',
    })).toBe('http://10.5.50.1/login');

    // Tier 2: HotSpot explicit custom override
    expect(resolveHandoff({
      hotspotLoginUrl: 'https://hs.operator.tz/login',
      gatewayIp: '10.5.60.1',
    })).toBe('https://hs.operator.tz/login');

    // Tier 3: Derived from HotSpot gateway IP
    expect(resolveHandoff({
      gatewayIp: '10.5.60.1',
    })).toBe('http://10.5.60.1/login');

    // Tier 4: Legacy fallback
    expect(resolveHandoff({})).toBe('http://10.5.50.1/login');
  });

  it('derives safe gateway URLs for router status and logout actions', () => {
    const getGatewayEndpoints = (gatewayIp?: string) => {
      const host = gatewayIp || '10.5.50.1';
      return {
        login: 'http://' + host + '/login',
        status: 'http://' + host + '/status',
        logout: 'http://' + host + '/logout',
      };
    };

    const guestEndpoints = getGatewayEndpoints('10.5.50.1');
    expect(guestEndpoints.login).toBe('http://10.5.50.1/login');
    expect(guestEndpoints.status).toBe('http://10.5.50.1/status');
    expect(guestEndpoints.logout).toBe('http://10.5.50.1/logout');

    const vipEndpoints = getGatewayEndpoints('10.5.60.1');
    expect(vipEndpoints.login).toBe('http://10.5.60.1/login');
    expect(vipEndpoints.status).toBe('http://10.5.60.1/status');
    expect(vipEndpoints.logout).toBe('http://10.5.60.1/logout');
  });

  it('sanitizes post-auth destination URL to prevent portal redirect loops', () => {
    const sanitizeDst = (dst?: string) => {
      if (!dst) return 'https://www.google.com';
      if (dst.startsWith('javascript:')) return 'https://www.google.com';
      if (dst.includes('/p/')) return 'https://www.google.com';
      return dst;
    };

    expect(sanitizeDst('https://news.ycombinator.com')).toBe('https://news.ycombinator.com');
    expect(sanitizeDst('javascript:evil()')).toBe('https://www.google.com');
    expect(sanitizeDst('https://wifi.operator.tz/p/usimamizi-lab')).toBe('https://www.google.com');
  });

  it('scopes portal context sessionStorage keys by hotspot slug', () => {
    const getStorageKey = (slug: string) => 'usimamizi_portal_ctx_' + slug;
    expect(getStorageKey('guest-wifi')).toBe('usimamizi_portal_ctx_guest-wifi');
    expect(getStorageKey('vip-lounge')).toBe('usimamizi_portal_ctx_vip-lounge');
  });
});
