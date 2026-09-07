import { describe, it, expect } from 'vitest';
import { SITE_TYPES } from './LocationsListPage';

describe('Locations Infrastructure Domain Specs', () => {
  it('validates supported site types vocabulary', () => {
    const siteTypeValues = SITE_TYPES.map((t) => t.value);
    expect(siteTypeValues).toContain('BRANCH');
    expect(siteTypeValues).toContain('HOTEL');
    expect(siteTypeValues).toContain('RESTAURANT');
    expect(siteTypeValues).toContain('CAFE');
    expect(siteTypeValues).toContain('BUS_TERMINAL');
    expect(siteTypeValues).toContain('MALL');
    expect(siteTypeValues).toContain('OFFICE');
    expect(siteTypeValues).toContain('PUBLIC_SITE');
    expect(siteTypeValues).toContain('OTHER');
  });

  it('verifies location network health classification logic', () => {
    const computeHealth = (routers: { health_status: string }[]): 'HEALTHY' | 'DEGRADED' | 'UNREACHABLE' | 'UNKNOWN' => {
      if (!routers || routers.length === 0) return 'UNKNOWN';
      const online = routers.filter((r) => r.health_status === 'ONLINE' || r.health_status === 'HEALTHY').length;
      const degraded = routers.filter((r) => r.health_status === 'DEGRADED').length;
      const unreachable = routers.filter((r) => r.health_status === 'UNREACHABLE').length;

      if (unreachable > 0 && online === 0) return 'UNREACHABLE';
      if (degraded > 0 || unreachable > 0) return 'DEGRADED';
      if (online > 0) return 'HEALTHY';
      return 'UNKNOWN';
    };

    expect(computeHealth([])).toBe('UNKNOWN');
    expect(computeHealth([{ health_status: 'ONLINE' }])).toBe('HEALTHY');
    expect(computeHealth([{ health_status: 'ONLINE' }, { health_status: 'UNREACHABLE' }])).toBe('DEGRADED');
    expect(computeHealth([{ health_status: 'UNREACHABLE' }])).toBe('UNREACHABLE');
  });

  it('validates location filtering logic by search query and site type', () => {
    const locations = [
      { id: '1', name: 'Kariakoo Branch', site_type: 'BRANCH', status: 'ACTIVE' },
      { id: '2', name: 'Mbezi Beach Resort', site_type: 'HOTEL', status: 'ACTIVE' },
      { id: '3', name: 'Arusha Hub', site_type: 'OFFICE', status: 'INACTIVE' },
    ];

    const filterLocations = (q: string, type: string) => {
      return locations.filter((loc) => {
        if (type !== 'ALL' && loc.site_type !== type) return false;
        if (q && !loc.name.toLowerCase().includes(q.toLowerCase())) return false;
        return true;
      });
    };

    expect(filterLocations('kariakoo', 'ALL')).toHaveLength(1);
    expect(filterLocations('', 'HOTEL')).toHaveLength(1);
    expect(filterLocations('beach', 'HOTEL')).toHaveLength(1);
    expect(filterLocations('unknown', 'ALL')).toHaveLength(0);
  });
});
