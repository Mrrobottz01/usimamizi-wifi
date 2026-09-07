import { describe, it, expect } from 'vitest';

describe('Routers Fleet & Telemetry Specs', () => {
  it('determines standard MikroTik API ports based on TLS setting', () => {
    const getSuggestedPort = (useTls: boolean, currentPort: number) => {
      if (useTls && currentPort === 8728) return 8729;
      if (!useTls && currentPort === 8729) return 8728;
      return currentPort;
    };

    expect(getSuggestedPort(true, 8728)).toBe(8729);
    expect(getSuggestedPort(false, 8729)).toBe(8728);
    expect(getSuggestedPort(true, 9999)).toBe(9999);
  });

  it('calculates memory usage percentages accurately from bytes telemetry', () => {
    const calcMemUsage = (freeBytes: number, totalBytes: number): number => {
      if (!totalBytes || totalBytes <= 0) return 0;
      return Math.round(((totalBytes - freeBytes) / totalBytes) * 100);
    };

    // 64MB total, 32MB free => 50%
    expect(calcMemUsage(33554432, 67108864)).toBe(50);
    // 128MB total, 32MB free => 75%
    expect(calcMemUsage(33554432, 134217728)).toBe(75);
  });

  it('aggregates router fleet metrics correctly', () => {
    const routers = [
      { id: '1', health_status: 'ONLINE' },
      { id: '2', health_status: 'HEALTHY' },
      { id: '3', health_status: 'DEGRADED' },
      { id: '4', health_status: 'UNREACHABLE' },
      { id: '5', health_status: 'UNKNOWN' },
    ];

    const counts = {
      total: routers.length,
      online: routers.filter((r) => r.health_status === 'ONLINE' || r.health_status === 'HEALTHY').length,
      degraded: routers.filter((r) => r.health_status === 'DEGRADED').length,
      unreachable: routers.filter((r) => r.health_status === 'UNREACHABLE').length,
    };

    expect(counts.total).toBe(5);
    expect(counts.online).toBe(2);
    expect(counts.degraded).toBe(1);
    expect(counts.unreachable).toBe(1);
  });
});
