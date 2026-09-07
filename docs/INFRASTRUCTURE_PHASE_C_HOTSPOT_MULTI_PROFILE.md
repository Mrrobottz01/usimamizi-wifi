# Usimamizi Wi-Fi — Phase C: HotSpot Multi-Profile & Decoupling Documentation

## 1. Executive Summary

Phase C establishes multi-profile HotSpot capability across the Usimamizi Wi-Fi platform. Prior to this phase, the platform assumed a singleton HotSpot configuration per company (`.first()`), with hardcoded lab SSIDs and global firewall tags.

With Phase C complete, the platform now fully supports:
- **Multiple HotSpot profiles per Router and Location** (e.g. Guest Wi-Fi, Staff Wi-Fi, VIP Lounge).
- **Explicit default HotSpot designation** with strict database-level unique constraints.
- **Per-HotSpot plan scoping** (only designated internet packages are presented on specific HotSpots, with graceful fallback to all company active plans).
- **HotSpot-attributed sessions** (`HotspotSession.hotspot`).
- **Decoupled printable vouchers and SMS notifications** dynamically using the active HotSpot's SSID and domain.
- **Isolated Anti-Tethering policies** tagged with `:hotspot_id` and interface targeting (`hotspot.interface_name`).
- **Complete backward compatibility** for existing captive portal routes (`/p/usimamizi-lab`) and legacy endpoints (`/api/v1/settings/hotspot/`).

---

## 2. Infrastructure Hierarchy

The full infrastructure hierarchy established across Phases A, B, and C is now:

```text
Company (Tenant)
└── Location (Physical Venue)
    └── Router (MikroTik RouterOS Node)
        ├── RadiusClient (AAA Gateway)
        ├── RouterUplinkProfile(s) (Failover WANs)
        └── HotspotConfiguration(s)
            ├── Hotspot A (e.g. "Public Guest", SSID: Guest-WiFi, VLAN 10)
            │   ├── Scoped Plans: [1 Hour Pass, 1 Day Pass]
            │   └── Anti-Tethering Tag: USIMAMIZI_ANTI_TETHER_TTL_LOCK:<uuid_a>
            └── Hotspot B (e.g. "VIP Lounge", SSID: VIP-Lounge, VLAN 20)
                ├── Scoped Plans: [VIP Unlimited Weekly]
                └── Anti-Tethering Tag: USIMAMIZI_ANTI_TETHER_TTL_LOCK:<uuid_b>
```

---

## 3. Database Schema & Migration Details

### 3.1 HotspotConfiguration Model Additions (`apps/companies/models.py`)
- **`is_default` (`models.BooleanField(default=False, db_index=True)`)**:
  - Designates the primary/default HotSpot for a company.
  - Enforced by a partial unique constraint:
    ```python
    models.UniqueConstraint(
        fields=['company'],
        condition=models.Q(is_default=True),
        name='unique_default_hotspot_per_company'
    )
    ```
- **`plans` (`models.ManyToManyField('plans.Plan', blank=True, related_name='hotspots')`)**:
  - M2M relation permitting explicit plan assignment per HotSpot profile.
- **`Company.default_hotspot` property**:
  - Fast accessor resolving the default HotSpot without `.first()` singleton ambiguity.

### 3.2 HotspotSession Attribution (`apps/hotspot_sessions/models.py`)
- **`hotspot` (`models.ForeignKey('companies.HotspotConfiguration', null=True, blank=True, on_delete=models.SET_NULL, related_name='sessions')`)**:
  - Provides direct session-to-hotspot attribution for reporting, analytics, and deletion safety checks.
  - Indexed together with `status`: `models.Index(fields=['hotspot', 'status'])`.

### 3.3 Applied Migrations
1. `companies.0010_hotspotconfiguration_is_default_and_more.py` — Schema additions (`is_default`, `plans`, `unique_default_hotspot_per_company`).
2. `companies.0011_backfill_default_hotspot.py` — Data migration backfilling `is_default=True` for existing active HotSpots.
3. `hotspot_sessions.0004_hotspotsession_hotspot_and_more.py` — Added `hotspot` foreign key and indexes to `HotspotSession`.

---

## 4. Service Decoupling

All helper services in `apps/companies/services/portal_services.py` were refactored to eliminate singleton lookups:

| Helper Function | Signature | Description |
|---|---|---|
| `get_default_hotspot` | `(company: Company) -> Optional[HotspotConfiguration]` | Resolves the designated default HotSpot for a company (`is_default=True`). Falls back to the oldest active HotSpot if none is designated default. |
| `get_hotspot_by_slug` | `(slug: str, company: Optional[Company] = None) -> Optional[HotspotConfiguration]` | Looks up an active HotSpot by its unique portal slug. |
| `get_hotspot_by_id` | `(hotspot_id: Any, company: Optional[Company] = None) -> Optional[HotspotConfiguration]` | Looks up an active HotSpot by its primary key UUID. |
| `get_plans_for_hotspot` | `(hotspot: HotspotConfiguration, include_inactive: bool = False)` | Returns assigned plans if explicit plans exist; otherwise falls back to all active company plans. |
| `get_or_create_default_hotspot` | `(company: Company) -> HotspotConfiguration` | Deprecated fallback maintaining backward compatibility for legacy non-GET paths. |

---

## 5. HotSpot Management REST API

Mounted under `/api/v1/hotspots/`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/hotspots/` | List company HotSpots with filters (`router`, `location`, `is_active`). |
| `POST` | `/api/v1/hotspots/` | Create a new HotSpot configuration with location, router, and branding tokens. Supports both `router` / `router_id` and `location` / `location_id`. |
| `GET` | `/api/v1/hotspots/<uuid:hotspot_id>/` | Detailed view including plan summary list, hosting router, location, and active session count. |
| `PATCH` | `/api/v1/hotspots/<uuid:hotspot_id>/` | Partial update of HotSpot attributes, network interfaces, and captive portal branding. |
| `DELETE` | `/api/v1/hotspots/<uuid:hotspot_id>/` | Safe deletion: if the HotSpot has linked purchases or sessions, it is automatically deactivated (`is_active = False`) to protect financial and audit integrity. Unreferenced HotSpots are cleanly deleted. |
| `POST` | `/api/v1/hotspots/<uuid:hotspot_id>/set-default/` | Atomically unset previous default and designate target HotSpot as `is_default = True`. |
| `GET` | `/api/v1/hotspots/<uuid:hotspot_id>/plans/` | List internet packages currently available on this HotSpot. |
| `POST` | `/api/v1/hotspots/<uuid:hotspot_id>/plans/` | Assign specific plan IDs (`{"plan_ids": ["<uuid>", ...]}`) to this HotSpot. |

---

## 6. Decoupled Subsystems

### 6.1 Captive Portal & Purchase Flow
- **`PublicHotspotPlansView` (`/api/v1/public/hotspots/{slug}/plans/`)**:
  - Uses `get_plans_for_hotspot(hotspot)` to present only the plans scoped to that captive portal slug.
- **`PublicInitiatePurchaseView` (`/api/v1/public/hotspots/{slug}/purchases/`)**:
  - Strictly validates that the requested plan is assigned to that HotSpot (`get_plans_for_hotspot(hotspot).filter(id=plan_id).exists()`), rejecting unassigned plans with `404 PLAN_NOT_FOUND`.
- **Customer Self-Service Portal (`apps/customers/api/public_views.py`)**:
  - Decoupled from database-wide `.first()` queries. Resolves HotSpot by slug, or falls back to `get_default_hotspot(company)`.

### 6.2 Printable Vouchers & SMS Notifications
- **Printable Vouchers (`apps/vouchers/services/voucher_services.py`)**:
  - `get_printable_voucher_cards(batch, hotspot=...)` accepts an optional `hotspot`.
  - Dynamically uses `hotspot.ssid`, `hotspot.slug`, and DNS/gateway address instead of hardcoded strings.
- **SMS Notifications (`apps/notifications/services/sms_services.py`)**:
  - `send_voucher_sms(voucher=..., recipient_phone=..., company=..., hotspot=...)` dynamically injects `hotspot.ssid` into templates and fallback SMS messages.

### 6.3 Anti-Tethering Rule Isolation & Interface Targeting
- **HotSpot Rule Isolation (`apps/companies/services/anti_tethering_services.py`)**:
  - Firewall mangle and filter rule comments now include `:hotspot_id` suffixes:
    - Mangle TTL Lock: `USIMAMIZI_ANTI_TETHER_TTL_LOCK:{hotspot_id}`
    - Filter TTL 63: `USIMAMIZI_ANTI_TETHER_TTL63:{hotspot_id}`
    - Filter TTL 127: `USIMAMIZI_ANTI_TETHER_TTL127:{hotspot_id}`
  - Target interface is dynamically chosen from `hotspot.interface_name` (e.g. `vlan-guest`, `bridgeLocal`).
  - Legacy un-suffixed tags and existing lab rules are adopted seamlessly by the default HotSpot without duplication.
  - Removing a policy on HotSpot A leaves HotSpot B's rules on the same router completely intact.

---

## 7. Verification & Quality Assurance

1. **Automated Backend Test Suite**:
   - `test_hotspot_multi_profile.py`: 7 tests passing (default HotSpot resolution, unique constraint, plan scoping, public purchase validation, CRUD API, tenant isolation, voucher/SMS scoping, anti-tethering rule isolation).
   - `test_anti_tethering.py`: 9 tests passing.
   - `vouchers`, `payments`, `notifications`: 57 tests passing.
   - **Full backend regression suite: 157 passed, 0 failed (100% pass rate).**
2. **Frontend Build Verification**:
   - `npm run build` in `frontend/` completed in 7.12s with 0 errors.
3. **Data Integrity Verification**:
   - Pre- and post-migration database counts confirmed 100% retention:
     - Companies: 1
     - Locations: 1
     - Routers: 5
     - RadiusClients: 5
     - HotspotConfigurations: 1 (`Usimamizi Lab HotSpot`, `slug="usimamizi-lab"`, `is_default=True`)
     - RouterUplinkProfiles: 3
     - Plans: 2
     - AccessPurchases: 16
     - PaymentTransactions: 16
     - VoucherBatches: 11
     - Vouchers: 46
     - AccessEntitlements: 25
     - HotspotSessions: 13
     - HotspotWalledGardenEntries: 4
     - AntiTetheringPolicies: 1
