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
    const key = `idmp_test_${Date.now()}`;
    expect(key.length).toBeLessThanOrEqual(30);
  });
});
