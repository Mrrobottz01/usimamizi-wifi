# HotSpot Portal Resolution & Multi-Tenancy

Resolution mechanics and security boundaries for multi-tenant HotSpots in **Usimamizi Wi-Fi** (Phase 6).

---

## 1. HotSpot Resolution Flow

When a user lands on `/p/{hotspot_slug}`:
1. The frontend requests `GET /api/v1/public/hotspots/{slug}/portal/`.
2. Backend queries `HotspotConfiguration.objects.select_related('company').filter(slug__iexact=slug)`.
3. If not found: returns HTTP 404 (`HOTSPOT_NOT_FOUND`).
4. If `is_active == False`: returns HTTP 403 (`HOTSPOT_INACTIVE`).
5. If valid: returns public branding tokens (business name, logo, accent color, headline, welcome text, support phone, default language, router login URL).

---

## 2. Public Safe Token Surface

The public config serializer explicitly filters out:
- Internal UUIDs of companies
- RADIUS shared secrets
- SMS provider API credentials
- Admin member details
