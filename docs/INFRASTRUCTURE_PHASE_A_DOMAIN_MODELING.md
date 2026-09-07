# Usimamizi Wi-Fi: Infrastructure Refactor — Phase A: Core Domain Modeling

**Status:** Completed & Verified  
**Date:** September 2026  
**Target:** Formalize `Company ──► Location ──► Router ──► [RadiusClient, Hotspot]`  
**Execution Strategy:** Additive, non-destructive, migration-safe, backward-compatible  

---

## 1. Executive Summary

Phase A establishes the formal physical and network infrastructure domain hierarchy for Usimamizi Wi-Fi. Prior to this phase, the platform operated on flat singleton assumptions where captive portal branding was conflated with router network topology, and locations and physical routers did not exist as first-class database entities.

Phase A introduces dedicated `Location` and `Router` domains, binds `RadiusClient` 1:1 with `Router`, associates `HotspotConfiguration` with its hosting `Router` and physical `Location`, and links `RouterUplinkProfile` to `Router`.

Zero existing records were destroyed or altered in an incompatible way. All existing public portal slugs, SSIDs, and router login URLs were strictly preserved.

---

## 2. Infrastructure Hierarchy: Before vs. After

### Before (Flat Singleton Architecture)
```text
Company
 ├── HotspotConfiguration (Single default hotspot per company via .first())
 ├── RouterUplinkProfile (Company-scoped, hardcoded wlan2 / 10.5.50.1)
 ├── RadiusClient (NAS IP only, unlinked to physical router)
 └── AntiTetheringPolicy (1:1 with HotspotConfiguration)
```

### After (Hierarchical Production Architecture)
```text
Company
 └── Location (Physical venue / branch e.g. Kariakoo Flagship Branch)
      ├── Metadata: Address, Region, District, Lat/Lng, Timezone, Contact, Status
      │
      └── Router (Physical / logical appliance e.g. MikroTik hAP ac lite)
           ├── Hardware & OS: Vendor, Model, Serial, Architecture, RouterOS Version
           ├── Management Plane: Management IP, API Port, TLS flag, Encrypted Password
           ├── Telemetry: Cached System Resources, Health Status, Last Seen
           ├── RadiusClient (1:1 AAA NAS link for FreeRADIUS)
           ├── RouterUplinkProfile(s) (Saved station WAN profiles)
           │
           └── HotspotConfiguration(s) (Customer access service)
                ├── Binding: Interface (bridgeLocal), Server Name, Gateway IP, Subnet
                ├── Public Access: Slug (/p/:slug), SSID, Portal Branding, Handoff URL
                ├── Policy: Anti-Tethering Policy (TTL locks & drops)
                └── Walled Garden Entries (Pre-auth domain/IP allowlists)
```

---

## 3. New & Modified Models

### 3.1 `Location` Model (`apps/locations/models.py`)
- **Table:** `locations`
- **Fields:**
  - `id`: UUID primary key
  - `company`: `ForeignKey(Company, on_delete=CASCADE, related_name='locations')`
  - `name`: `CharField(max_length=255)`
  - `code`: `CharField(max_length=64)` (Unique per company)
  - `region`: `CharField(max_length=128, blank=True)` (e.g. Dar es Salaam, Arusha)
  - `district`: `CharField(max_length=128, blank=True)`
  - `address`: `TextField(blank=True)`
  - `latitude`, `longitude`: `DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)` (Validated ranges)
  - `timezone`: `CharField(default='Africa/Dar_es_Salaam')`
  - `status`: `ACTIVE`, `INACTIVE`, `MAINTENANCE`
  - `contact_person`, `contact_phone`: `CharField(blank=True)`
  - `is_active`: `BooleanField(default=True, db_index=True)`
- **Auto-Generation:** `generate_location_code(company, name)` generates human-readable codes (e.g., `LOC-DAR-001`, `LOC-MAIN-001`).

### 3.2 `Router` Model (`apps/routers/models.py`)
- **Table:** `routers`
- **Fields:**
  - `id`: UUID primary key
  - `company`: `ForeignKey(Company, on_delete=CASCADE, related_name='routers')`
  - `location`: `ForeignKey(Location, on_delete=PROTECT, related_name='routers')`
  - `name`: `CharField(max_length=255)`
  - `identity`: `CharField(max_length=255, blank=True)` (MikroTik `/system identity`)
  - `vendor`: `CharField(default='MikroTik')`
  - `model`: `CharField(blank=True)` (e.g., `hAP ac lite`, `RB4011iGS+`)
  - `serial_number`: `CharField(blank=True, db_index=True)`
  - `management_ip`: `GenericIPAddressField` (Management address)
  - `api_port`: `PositiveIntegerField(default=8728)`
  - `use_tls`: `BooleanField(default=False)`
  - `api_username`: `CharField(default='admin')`
  - `api_password_encrypted`: `TextField(blank=True)` (Encrypted at rest via AES-128-CBC)
  - `routeros_version`, `architecture`, `firmware_version`: `CharField(blank=True)`
  - `health_status`: `ONLINE`, `OFFLINE`, `DEGRADED`, `UNREACHABLE`, `UNKNOWN` (default: `UNKNOWN`)
  - `last_seen_at`: `DateTimeField(null=True, blank=True)`
  - `system_resources`: `JSONField(default=dict, blank=True)`
  - `is_active`: `BooleanField(default=True, db_index=True)`
- **Security:** Reuses existing `apps.core.security` (`encrypt_secret` / `decrypt_secret`). Passwords are never serialized or returned unmasked.
- **Cross-Tenant Validation:** Clean validation prevents attaching a `Location` from another company to a `Router`.

### 3.3 Modified `RadiusClient` (`apps/radius/models.py`)
- Added `router`: `OneToOneField('routers.Router', on_delete=SET_NULL, null=True, blank=True, related_name='radius_client')`.
- Fully preserves existing `nas_ip`, `nas_identifier`, and encrypted shared secrets.

### 3.4 Modified `HotspotConfiguration` (`apps/companies/models.py`)
- Added `location`: `ForeignKey('locations.Location', on_delete=SET_NULL, null=True, blank=True, related_name='hotspots')`.
- Added `router`: `ForeignKey('routers.Router', on_delete=SET_NULL, null=True, blank=True, related_name='hotspots')`.
- Added network binding fields:
  - `interface_name`: `CharField(default='bridgeLocal')`
  - `server_name`: `CharField(default='hotspot1')`
  - `gateway_ip`: `GenericIPAddressField(null=True, blank=True)`
  - `subnet_mask`: `CharField(default='255.255.255.0')`
- Added performance indexes: `(company, router)`, `(company, location)`, `(company, slug)`.
- Added cross-tenant validation ensuring `location` and `router` belong to the same company.

### 3.5 Modified `RouterUplinkProfile` (`apps/companies/models.py`)
- Added `router`: `ForeignKey('routers.Router', on_delete=SET_NULL, null=True, blank=True, related_name='uplink_profiles')`.

---

## 4. Migration Sequence & Data Backfill Rules

The migration was split into clear schema and data phases:

```text
1. locations.0001_initial
   └── Creates 'locations' table with spatial validation and unique code constraints.

2. routers.0001_initial
   └── Creates 'routers' table with encrypted credentials and telemetry storage.

3. radius.0003_radiusclient_router
   └── Adds nullable 'router' OneToOneField to 'radius_clients'.

4. companies.0005_hotspot_location_router_network_fields
   └── Adds nullable 'location', 'router', and network binding fields to 'hotspot_configurations'
   └── Adds nullable 'router' ForeignKey to 'router_uplink_profiles'.

5. companies.0006_backfill_infrastructure (Data Migration)
   └── For each Company: seeds exactly one Location ("<Company> Main Site", code "LOC-MAIN-001").
   └── For each RadiusClient: creates a Router with location=default_location and links 1:1.
   └── For each HotspotConfiguration: links to default_location, primary_router, and sets gateway_ip="10.5.50.1".
   └── For each RouterUplinkProfile: links to primary_router when deterministic.
```

### Safety & Invariants
- **No Hardware Calls:** The data migration makes zero network requests and does not interact with RouterOS sockets or external APIs.
- **Idempotency:** Safe to run multiple times without duplicating locations or routers.
- **Slugs & URLs Preserved:** Captive portal URLs (e.g. `/p/usimamizi-lab`) and router handoffs (`http://10.5.50.1/login`) remain 100% untouched.

---

## 5. Data Counts Verification (Zero Data Loss)

Database record counts were audited before and after applying Phase A migrations:

| Entity | Count Before Migration | Count After Migration | Status |
| :--- | :---: | :---: | :--- |
| `Company` | 1 | 1 | Preserved |
| `CompanyMembership` | 1 | 1 | Preserved |
| **`Location`** | **0** | **1** | **New Seeded Infrastructure** |
| **`Router`** | **0** | **5** | **New Backfilled Fleet** |
| `HotspotConfiguration` | 1 | 1 | Preserved & Linked |
| `RouterUplinkProfile` | 3 | 3 | Preserved & Linked |
| `AntiTetheringPolicy` | 1 | 1 | Preserved |
| `RadiusClient` | 5 | 5 | Preserved & Linked 1:1 |
| `EntitlementDevice` | 15 | 15 | Preserved |
| `RadiusAccountingLog` | 169 | 169 | Preserved |
| `Plan` | 2 | 2 | Preserved |
| `VoucherBatch` | 11 | 11 | Preserved |
| `Voucher` | 46 | 46 | Preserved |
| `AccessEntitlement` | 25 | 25 | Preserved |
| `HotspotSession` | 13 | 13 | Preserved |
| `AccessPurchase` | 16 | 16 | Preserved |
| `PaymentTransaction` | 16 | 16 | Preserved |
| `PaymentProviderConfiguration` | 1 | 1 | Preserved |
| `HotspotWalledGardenEntry` | 4 | 4 | Preserved |
| `Customer` | 0 | 0 | Preserved |
| `CustomerDevice` | 0 | 0 | Preserved |
| `Subscription` | 0 | 0 | Preserved |

---

## 6. Test & Regression Verification

### 6.1 Phase A Test Suite (`15/15 Passed`)
- `apps/locations/tests/test_locations.py`:
  - `test_create_location_with_code_generation`: Verified code generation (`LOC-CLO-001`).
  - `test_location_company_isolation`: Verified multi-tenant scoping.
  - `test_location_code_uniqueness_within_company`: Verified collision safety.
  - `test_location_coordinate_validation`: Verified lat/lng boundary checks.
  - `test_generate_location_code_increment`: Verified sequence numbers.
- `apps/routers/tests/test_routers.py`:
  - `test_create_router_and_credential_encryption`: Verified at-rest AES encryption for API passwords.
  - `test_router_location_company_consistency`: Verified cross-tenant rejection.
  - `test_router_radius_client_relationship`: Verified 1:1 link with `RadiusClient`.
  - `test_multiple_routers_at_single_location`: Verified multi-router venue topology.
  - `test_router_api_port_validation`: Verified port boundaries (1-65535).
- `apps/companies/tests/test_infrastructure_hierarchy.py`:
  - `test_hotspot_linked_to_router_and_location`: Verified full hierarchy linkages.
  - `test_one_router_hosts_multiple_hotspots`: Verified 1 Router $\rightarrow$ Multiple HotSpots (Guest, VIP, Staff).
  - `test_hotspot_location_router_company_consistency`: Verified cross-tenant rejection.
  - `test_existing_hotspot_singleton_query_compatibility`: Verified legacy `.first()` queries.
  - `test_router_uplink_profile_linked_to_router`: Verified uplink profile router relationship.

### 6.2 Full Platform Regression Suite (`140/140 Passed`)
- **Total Backend Tests:** **140 passed in 18.29s (100% passing)**.
- **Frontend Checks:** `npm run typecheck` (0 errors), `npm run build` (production build successful).

---

## 7. Known Temporary Compromises (Intentional for Phase A)

1. **`management_ip = nas_ip` Migration Fallback:** For backfilled routers, `management_ip` was initialized to `nas_ip` (`10.5.50.1`, `192.168.88.1`, etc.). Phase B will allow configuring distinct management and NAS IPs.
2. **`RouterUplinkProfile.password` Plaintext:** Preserved existing plaintext storage in Phase A to ensure zero disruption to live uplink switching. Password encryption is slated for Phase B.
3. **Legacy Service Compatibility:** Service functions in `portal_services.py` and `uplink_services.py` still use `.first()` or fallback constants for lab hardware until Phase B and C refactor their call signatures.

---

## 8. Acceptance Matrix

| Acceptance Item | Status | Verification Detail |
| :--- | :---: | :--- |
| **Location model** | **PASSED** | Defined in `apps.locations`, validated, indexed. |
| **Router model** | **PASSED** | Defined in `apps.routers`, encrypted passwords, telemetry. |
| **Company $\rightarrow$ Location** | **PASSED** | `company.locations.all()` works cleanly. |
| **Location $\rightarrow$ Router** | **PASSED** | `location.routers.all()` supports multi-router venues. |
| **Router $\leftrightarrow$ RadiusClient** | **PASSED** | 1:1 relationship established and bidirectional. |
| **Router $\rightarrow$ Multiple Hotspots** | **PASSED** | 1 Router hosting Guest, VIP, and Staff verified in tests. |
| **Hotspot $\rightarrow$ Location** | **PASSED** | Linked with company consistency checks. |
| **Existing hotspot data preserved** | **PASSED** | Branding, welcome text, colors, language untouched. |
| **Existing slug preserved** | **PASSED** | `usimamizi-lab` unchanged; captive portal routes functional. |
| **Existing SSID preserved** | **PASSED** | `Usimamizi-WiFi-Lab` unchanged. |
| **Existing portal handoff preserved** | **PASSED** | `http://10.5.50.1/login` untouched. |
| **RouterUplinkProfile relationship** | **PASSED** | Nullable `router` FK added; existing queries functional. |
| **AntiTethering compatibility** | **PASSED** | All anti-tethering tests pass; policy attached to hotspot. |
| **Walled Garden compatibility** | **PASSED** | All walled garden preset and export tests pass. |
| **Multi-company isolation** | **PASSED** | Tested in `test_locations.py` and `test_routers.py`. |
| **Migration safety & reversibility** | **PASSED** | Applied with `OK`, zero data loss verified. |
| **Regression suite** | **PASSED** | 140/140 tests pass (100%). |
| **No existing data loss** | **PASSED** | Exact row count comparison verified. |
| **Documentation** | **PASSED** | Full documentation in this file. |

---

## 9. Next Steps: Phase B Prerequisites

Phase A has successfully established the physical and network domain models in the database. When Phase B begins:
1. **Router Inventory & Credentials Hardening:** Move RouterOS API credentials out of environment variables and into encrypted `Router.api_password_encrypted`.
2. **Uplink WAN Scoping:** Scope `RouterUplinkProfile` directly to `Router` and encrypt Wi-Fi passwords at rest.
3. **Async Health Checks:** Implement a background Celery task to probe router reachability, update `health_status`, and cache CPU/memory telemetry without blocking Django worker threads.
