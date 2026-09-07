# Usimamizi Wi-Fi — Phase D: Location Services & Site Hierarchy

## 1. Executive Summary

Phase D elevates the Location entity into a full production operational site model. It establishes physical deployment context (branches, venues, hotels, transit hubs, and commercial locations) across multi-tenant companies while cleanly decoupling physical premises from logical network devices (Router) and captive service zones (HotspotConfiguration).

This implementation adhered strictly to all architectural mandates:
- Zero Live Polling on Read: Location list and detail endpoints derive network health entirely from cached router states and aggregated database counters. They never dial RouterOS API ports (TCP 8728/8729).
- Relocation Cascades: Moving a router between locations updates both the router and all hosted HotSpots atomically under an explicit audit trail (ROUTER_MOVED_LOCATION), preserving historical access purchases and sessions intact.
- Safe Lifecycle Guard: Deleting a location in use safely transitions it to INACTIVE (is_active=False) to prevent orphaned network dependencies. Unreferenced locations can be permanently deleted.
- Strict Multi-Tenancy: All selectors, APIs, subresource lookups, and mutation services are enforced at the company boundary.

---

## 2. Domain Model Enhancements

### apps.locations.models.Location
- site_type: Operational categorization using SiteType TextChoices:
  - BRANCH — Retail or corporate branch office
  - HOTEL — Hospitality / hotel venue
  - RESTAURANT — Dining establishment
  - CAFE — Coffee shop / casual dining
  - BUS_TERMINAL — Transit / bus station
  - MALL — Shopping center / mall
  - OFFICE — Commercial office building
  - PUBLIC_SITE — Public square, park, or municipal area
  - OTHER — General custom site
- operating_hours: Human-readable business/operational schedule (e.g. 08:00 - 22:00).
- installation_date: Optional deployment date tracking physical facility commissioning.
- external_reference: External CRM / ERP / billing code cross-reference.
- timezone: Validated against Python standard zoneinfo.available_timezones().
- Database Indexes: Optimized query index on ['company', 'is_active'] alongside existing ['company', 'code'].

---

## 3. Services & Selectors Architecture

### Services (apps.locations.services.location_services)
1. calculate_location_network_health(location):
   - Computes derived health state without any network I/O:
     - OFFLINE: All deployed routers are offline/unreachable.
     - DEGRADED: At least one router is offline or degraded, but some remain online.
     - HEALTHY: All deployed routers are online.
     - UNKNOWN: No routers deployed at this location.
   - Summarizes totals: total_routers, online_routers, degraded_routers, unreachable_routers, total_hotspots, active_sessions.
2. move_router_to_location(*, router, new_location, user):
   - Verifies router and target location belong to the same tenant company.
   - Updates router.location = new_location.
   - Atomically updates all hosted HotSpots: router.hotspots.update(location=new_location).
   - Writes AuditLog entry with action ROUTER_MOVED_LOCATION.
3. safe_delete_location(*, location, user):
   - Inspects reference tree (routers.exists(), hotspots.exists(), HotspotSession via hotspots).
   - If referenced: transitions is_active=False, status=INACTIVE, and logs LOCATION_DEACTIVATED.
   - If unreferenced: executes hard deletion and logs LOCATION_DELETED.
4. deactivate_location / reactivate_location:
   - Administrative lifecycle control with corresponding audit log generation.

### Selectors (apps.locations.selectors.location_selectors)
- get_locations_queryset(company, filters):
  - Single database roundtrip utilizing distinct aggregation (Count(..., distinct=True)):
    - router_count, online_router_count, degraded_router_count, unreachable_router_count
    - hotspot_count, active_hotspot_count, active_session_count
  - High-performance filtering: status, site_type, region, district, is_active.
  - Multi-field search across name, code, region, district, address, contact_person, and external_reference.
  - Whitelisted safe ordering (name, code, created_at, region, status, site_type).

---

## 4. REST API Endpoints (/api/v1/locations/)

| Method | Path | Description |
|---|---|---|
| GET | /api/v1/locations/ | Paginated list with annotated router/hotspot/session counts and derived network health. |
| POST | /api/v1/locations/ | Create location with auto-generated or custom unique code. |
| GET | /api/v1/locations/{id}/ | Full location details with nested network_summary and operational metadata. |
| PATCH/PUT | /api/v1/locations/{id}/ | Update operational site metadata, coordinates, contact info. |
| DELETE | /api/v1/locations/{id}/ | Safe deletion (soft-deactivates if in-use, hard-deletes if unreferenced). |
| POST | /api/v1/locations/{id}/reactivate/ | Reactivate a deactivated location (is_active=True, status=ACTIVE). |
| GET | /api/v1/locations/{id}/routers/ | List all routers deployed at this location. |
| GET | /api/v1/locations/{id}/hotspots/ | List all HotSpot configurations hosted at this location. |
| GET | /api/v1/locations/{id}/sessions/ | List active client sessions running across this location hotspots. |
| POST | /api/v1/locations/{id}/move-router/ | Relocate a router (and its child HotSpots) into this location. |

---

## 5. Test & Validation Evidence

- Unit & Integration Tests: 15 tests in backend/apps/locations/tests/ passing at 100%.
- Regression Test Suite: 167 of 167 total backend tests passing across all apps.
- Frontend Production Build: npm run build cleanly compiled 1,629 modules into production assets with 0 TypeScript or bundling errors.
- Data Preservation: Pre- and post-phase database counts confirmed zero data loss:
  - 1 Company, 1 Location, 5 Routers, 5 RadiusClients, 1 HotspotConfiguration (usimamizi-lab), 3 UplinkProfiles, 46 Vouchers, 25 Entitlements, 16 Purchases/Transactions, 13 Sessions, 4 Walled Garden Entries, 1 Anti-Tethering Policy.
