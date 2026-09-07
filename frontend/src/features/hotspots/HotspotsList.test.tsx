import { describe, it, expect } from 'vitest';

describe('Hotspots Fleet & Multi-Profile Specs', () => {
  it('generates URL-safe portal slugs from hotspot name', () => {
    const generateSlug = (name: string) => {
      return name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/(^-|-$)/g, '');
    };

    expect(generateSlug('Mbezi Resort Guest WiFi')).toBe('mbezi-resort-guest-wifi');
    expect(generateSlug('Kariakoo Branch #1 (VIP)')).toBe('kariakoo-branch-1-vip');
    expect(generateSlug('  Airport_Terminal_Free  ')).toBe('airport-terminal-free');
  });

  it('filters routers by selected location for dependent dropdowns', () => {
    const routers = [
      { id: 'r1', location_id: 'loc_kariakoo', name: 'Kariakoo Gateway' },
      { id: 'r2', location_id: 'loc_mbezi', name: 'Mbezi Gateway' },
      { id: 'r3', location_id: 'loc_kariakoo', name: 'Kariakoo Secondary' },
    ];

    const getAvailableRouters = (locId: string) => {
      if (!locId) return routers;
      return routers.filter((r) => r.location_id === locId);
    };

    expect(getAvailableRouters('loc_kariakoo')).toHaveLength(2);
    expect(getAvailableRouters('loc_mbezi')).toHaveLength(1);
    expect(getAvailableRouters('')).toHaveLength(3);
  });

  it('verifies plan inheritance rule: empty assigned plans inherits all active company plans', () => {
    const allCompanyPlans = [
      { id: 'p1', name: '1 Hour Pass', is_active: true },
      { id: 'p2', name: '24 Hour Pass', is_active: true },
      { id: 'p3', name: 'Archived Plan', is_active: false },
    ];

    const getEffectivePlans = (assignedPlanIds: string[]) => {
      const activePlans = allCompanyPlans.filter((p) => p.is_active);
      if (!assignedPlanIds || assignedPlanIds.length === 0) {
        return activePlans;
      }
      return activePlans.filter((p) => assignedPlanIds.includes(p.id));
    };

    // No plans assigned => inherits all active
    expect(getEffectivePlans([])).toHaveLength(2);
    // Explicit 1 plan assigned => only that 1 active plan
    expect(getEffectivePlans(['p1'])).toHaveLength(1);
    expect(getEffectivePlans(['p1'])[0].id).toBe('p1');
  });
});
