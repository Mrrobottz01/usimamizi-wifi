# Infrastructure Refactor — Phase E: Frontend Inventory & Infrastructure Management

## Executive Summary

Phase E delivers a comprehensive, production-grade operational infrastructure workspace for Usimamizi Wi-Fi. It elevates **Locations**, **Routers**, and **Hotspots** from placeholder screens and singleton settings tabs into full fleet management workspaces featuring rich operational metrics, multi-tab drill-downs, cross-navigation, credential rotation, live connection testing, and mobile captive portal previews.

---

## 1. Information Architecture & Navigation

The platform's primary navigation in `frontend/src/components/layout/Sidebar.tsx` was restructured into clean, enterprise-grade domain categories:

```text
Usimamizi Wi-Fi
├── NETWORK INFRASTRUCTURE
│   ├── Locations          (/locations)      — Physical sites, branches, and venues
│   ├── Routers            (/routers)        — MikroTik hardware fleet, credentials, & telemetry
│   └── Hotspots           (/hotspots)       — Captive portal profiles, SSIDs, & policies
├── OPERATIONS
│   ├── Active Sessions    (/sessions)       — Live authenticated subscriber sessions
│   ├── Customers          (/customers)      — Subscriber accounts & device inventory
│   └── Subscriptions      (/subscriptions)  — Recurring access entitlements
├── BILLING & ACCESS
│   ├── Plans              (/plans)          — Commercial internet bandwidth & time packages
│   ├── Vouchers           (/vouchers)       — Batch generation, tracking, & printables
│   ├── Payments           (/payments)       — Mobile money & card transaction logs
│   ├── Access Entitlements(/entitlements)   — FreeRADIUS AAA authorizations
│   └── Walled Garden      (/walled-garden)  — Pre-authentication domain whitelist
└── SYSTEM
    ├── Reports            (/reports)        — Revenue & network usage analytics
    ├── SMS Delivery Logs  (/sms-history)    — RafikiSMS & Twilio dispatch telemetry
    └── Settings           (/settings)       — Company, branding, payment gateways, & security
```

### Roadmap Cleanup
- All internal development phase badges (`Phase 3`, `Phase 8`, `Phase 9`) have been removed from the navigation and placeholders.
- The sidebar footer was streamlined to display `Usimamizi Wi-Fi v1.0` with the current company context.
- `/settings/hotspot` now issues a clean compatibility redirect to `/hotspots`.

---

## 2. Workspaces & Screen Inventory

### 2.1 Locations Workspace (`/locations` & `/locations/:id`)

- **List View (`LocationsListPage.tsx`)**:
  - **KPI Header**: Total Locations, Active Sites, Online Routers, Connected Users.
  - **Filter Toolbar**: Search query (site name, city, code), Site Type filter (Branch, Hotel, Restaurant, Café, Terminal, Mall, Office, Public, Other), Status filter, Network Health filter (Healthy, Degraded, Unreachable).
  - **Card Grid & Responsive Table**: Displays site type badge, status indicator, health badge, router count, hotspot count, active user count, operational contact, and direct link to detail view.
  - **Add Site Modal**: 3 grouped sections: Site Identity (Name, Code, Type), Physical Address (Street, City, Region, Coordinates), Operational Contact & Notes.
  - **Deactivate / Reactivate**: Safe site lifecycle toggle with cascade warning.

- **Detail View (`LocationDetailPage.tsx`)**:
  - **Header**: Site name, site type badge, operational status badge, computed health status, quick actions ("Edit Site", "Deactivate/Reactivate", "Move Router").
  - **Tab 1: Overview**: Site metadata, network summary counters, physical address card, contact person & emergency phone, operational deployment notes.
  - **Tab 2: Routers**: Tabular inventory of routers installed at this location with management IP, model, API port, TLS status, live health badge, last seen timestamp, and quick link to router detail.
  - **Tab 3: Hotspots**: All captive hotspot services operating under routers at this location with SSID, slug, gateway IP, interface, assigned plans count, and status.
  - **Tab 4: Active Sessions**: Real-time subscriber sessions connected through access points at this site, showing subscriber phone, framed IP, MAC address, plan name, and data usage.
  - **Move Router Modal**: Allows selecting a router from across the tenant company and moving it to this location with atomic reassignment of hosted hotspots.

---

### 2.2 Routers Fleet Workspace (`/routers` & `/routers/:id`)

- **List View (`RoutersListPage.tsx`)**:
  - **Fleet Metrics**: Total Gateways, Online, Degraded, Unreachable.
  - **Filter Toolbar**: Search query (name, identity, IP, serial), Location filter, Health status filter.
  - **Hardware Table**: Router name, RouterOS identity, hardware model, location link, management IP & API port, TLS badge, health badge with error tooltip, system telemetry (CPU load, memory usage, uptime), hosted hotspots count, and last seen timestamp.
  - **Row Quick Actions**: "Manage", "Test Connection", "Refresh Health".
  - **Register Router Modal**: Name, Location selection, Management IP, API Port, TLS toggle (auto-selects port 8728 vs 8729), Username, Password (masked input, never redisplayed), Uplink interface, Model, Serial number. Prompts user to run an immediate connection test upon creation.

- **Detail View (`RouterDetailPage.tsx`)**:
  - **Header**: Router name, RouterOS identity, Location breadcrumb link, Management IP:Port, Health badge, API-SSL badge, RouterOS version.
  - **Quick Action Bar**: "Test Connection" (displays latency in milliseconds and RouterOS identity banner), "Refresh Health", "Update Credentials".
  - **Tab 1: Overview & Telemetry**: CPU load bar, RAM usage bar with MB free/total, Uptime counter, RouterOS firmware badge, Architecture, Device Identity card, Management & API configuration card.
  - **Tab 2: Interfaces & WAN**: Scoped failover uplink manager (`UplinkNetworkSettings`) for managing multi-WAN profiles on this gateway.
  - **Tab 3: Hosted Hotspots**: Grid of captive hotspot servers attached to interfaces on this router, showing interface, gateway IP, subnet, active users, default status, and direct management link.
  - **Tab 4: RADIUS AAA Client**: NAS identifier, NAS IP, shared secret status (masked: `••••••••••••`, encrypted at rest using AES-256-GCM), Auth port (1812 UDP), Acct port (1813 UDP), CoA port (3799 UDP).
  - **Tab 5: Security & Access**: Transport encryption state (TLS API-SSL), credential isolation status.
  - **Update Credentials Modal**: Allows rotating management API username, password, port, and TLS mode without re-registering hardware.

---

### 2.3 Hotspots Fleet Workspace (`/hotspots` & `/hotspots/:id`)

- **List View (`HotspotsListPage.tsx`)**:
  - **Service Metrics**: Total Hotspots, Active Services, Connected Users, Anti-Tethering Protected count.
  - **Filter Toolbar**: Search query (name, SSID, slug, interface), Location filter, Router filter, Status filter.
  - **Service Table**: Hotspot profile name, broadcast SSID, `DEFAULT` badge, Location link, Router link, Interface & Gateway IP, Assigned plans counter, Active subscriber sessions, Anti-tethering protection badge, and Status.
  - **Row Actions**: "Manage", "Set as Default".
  - **Create Hotspot Modal**: Dependent dropdowns (selecting Location automatically filters available Routers; selecting Router auto-populates Location), Profile Name, SSID, URL Portal Slug (auto-generated), Router Interface (`wlan1`, `bridge-hotspot`), Gateway IP, Subnet Mask, Router Login URL, Default Profile toggle.

- **Detail View (`HotspotDetailPage.tsx`)**:
  - **Header**: Profile name, broadcast SSID, `DEFAULT PROFILE` badge, Active/Disabled status, Location link, Router link, "Set as Default" button, "Activate/Deactivate" button, and "Open Live Portal" link (`/portal/:slug`).
  - **Tab 1: Overview & Network**: Network parameters (SSID, slug, interface, gateway IP, subnet mask, login URL), and infrastructure hierarchy attachment.
  - **Tab 2: Portal & Branding**: Full captive portal customization form (Brand name, headline, welcome text, primary accent color picker, support phone, logo URL, router login URL) alongside a **Live Mobile Device Portal Preview** updating in real time.
  - **Tab 3: Plan Assignments**: List of all commercial company plans with checkboxes. Clearly explains the fallback rule: *"When no plans are specifically selected, all active plans from your company are automatically available at this hotspot."* Allows selecting specific plans or clearing selections.
  - **Tab 4: Anti-Tethering Policy**: Embedded `AntiTetheringSettings` component parameterized specifically for this hotspot (`hotspotId={hotspot.id}`), isolating TTL lock rules and counters.
  - **Tab 5: Active Sessions**: Real-time connected user sessions on this hotspot.

---

## 3. Security & Telemetry Safeguards

1. **Zero-Polling Rule**:
   - Component mounts **never** trigger live RouterOS API probes or blocking socket connections.
   - All page views display cached telemetry and database health status instantly without UI latency.
   - Live hardware probes only execute upon explicit operator action ("Test Connection" or "Refresh Health").

2. **Secret Disclosure Protection**:
   - Router API passwords and FreeRADIUS shared secrets are encrypted using AES-256-GCM in PostgreSQL.
   - Neither the backend serializers nor frontend API client ever expose or transmit raw credentials.
   - Credential update inputs use password masking and allow leaving the password blank to retain existing credentials.

3. **Atomic Relocations**:
   - Moving a router between locations updates both the router and all hosted captive hotspot profiles atomically inside a database transaction (`select_for_update`).

---

## 4. Verification & Quality Assurance

### 4.1 Frontend Automated Tests (Vitest)
```bash
npm test --prefix frontend
```
**Results:**
```text
 ✓ src/app/App.test.tsx (1 test)
 ✓ src/features/routers/RoutersList.test.tsx (3 tests)
 ✓ src/features/portal/CaptivePortalPage.test.tsx (3 tests)
 ✓ src/features/hotspots/HotspotsList.test.tsx (3 tests)
 ✓ src/features/locations/LocationsList.test.tsx (3 tests)

 Test Files  5 passed (5)
      Tests  13 passed (13)
   Duration  2.15s
```

### 4.2 Frontend Typecheck
```bash
npm run typecheck --prefix frontend
```
**Results:**
- `tsc --noEmit` passed with **0 errors**.

### 4.3 Production Build
```bash
npm run build --prefix frontend
```
**Results:**
- Vite production build succeeded in 6.59s.

### 4.4 Backend Full Regression Suite (Pytest)
```bash
pytest backend/apps/ -v
```
**Results:**
```text
============================ 167 passed in 19.65s =============================
```
- 100% of all existing platform tests passed with zero regressions across tenant isolation, FreeRADIUS AAA, MikroTik RouterOS API, Snippe payments, RafikiSMS, vouchers, plans, and anti-tethering.
