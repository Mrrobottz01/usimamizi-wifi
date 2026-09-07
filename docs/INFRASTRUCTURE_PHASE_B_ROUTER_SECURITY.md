# Infrastructure Refactor — Phase B: Router Inventory & Credential Hardening

## 1. Executive Summary & Objectives

Following the completed **Phase A (Core Domain Modeling)**, **Phase B (Router Inventory & Credential Hardening)** eliminates global single-router and environment-variable-based management assumptions in Usimamizi Wi-Fi. It introduces a hardened, per-router inventory and security layer that:

1. **Hardens RouterOS Credentials at Rest**: Encrypts RouterOS management passwords and upstream Wi-Fi uplink passwords using AES-128-CBC (`apps.core.security`), strictly preventing plaintext credential leakage in the database, API serializers, or logs.
2. **Eliminates Insecure Defaults**: Completely removes `admin:admin` fallbacks. Connection attempts to uncredentialed routers abort immediately with explicit `ROUTER_CREDENTIALS_NOT_CONFIGURED` exceptions.
3. **Implements Dedicated RouterOS API Client (`RouterOSAPIClient.for_router(router)`)**: Provides timeout-bounded, per-router socket connections with support for TLS/SSL (TCP port 8729) and RouterOS binary sentence framing.
4. **Structured Failure Taxonomy & Live Diagnostics**: Implements `test_router_connection(router)` and `collect_router_telemetry(router)` returning structured diagnostics (`CONNECTED`, `CONNECTION_TIMEOUT`, `CONNECTION_REFUSED`, `HOST_UNREACHABLE`, `AUTHENTICATION_FAILED`, `TLS_ERROR`).
5. **Background Telemetry Polling**: Implements Celery tasks (`poll_router_health_task` and `poll_active_routers_task`) to poll router health, CPU load, uptime, and memory asynchronously, caching results in `router.system_resources` and `router.health_status` without blocking HTTP request threads.
6. **Router-Aware Consumer Refactoring**:
   - Upstream WAN/Wi-Fi switching (`apps.companies.services.uplink_services`) accepts explicit `router: Router` instances and records the hosting router on `RouterUplinkProfile`.
   - Anti-Tethering policy enforcement (`apps.companies.services.anti_tethering_services`) derives router credentials and interface targets directly from `hotspot.router`.
   - Dynamic session disconnect / RFC 3576 (`apps.hotspot_sessions.services.session_control`) resolves active NAS clients directly from `session.hotspot.router.radius_clients`.
7. **Complete REST API Suite**: Exposes `/api/v1/routers/` endpoints for CRUD, credential rotation, connectivity testing, and health monitoring with strict tenant isolation.

---

## 2. Router Model & Credential Encryption Architecture

### 2.1 Router Model Enhancements (`apps.routers.models.Router`)

| Field | Type | Description |
|---|---|---|
| `company` | `ForeignKey(Company)` | Multi-tenant scoping |
| `location` | `ForeignKey(Location)` | Physical site deployment |
| `name` | `CharField(255)` | Human label (e.g. Kariakoo-Main-GW) |
| `identity` | `CharField(255)` | RouterOS system identity (`/system identity`) |
| `management_ip` | `GenericIPAddressField` | IP address for RouterOS API / WinBox |
| `api_port` | `PositiveIntegerField` | 8728 (plain) or 8729 (TLS) |
| `use_tls` | `BooleanField` | RouterOS API-SSL encryption flag |
| `api_username` | `CharField(128)` | API username (default: `admin`) |
| `api_password_encrypted`| `TextField` | AES-128-CBC encrypted ciphertext at rest |
| `uplink_interface_name` | `CharField(64)` | Default upstream station interface (e.g. `wlan2`, `ether1`) |
| `health_status` | `CharField` | `ONLINE`, `OFFLINE`, `DEGRADED`, `UNREACHABLE`, `UNKNOWN` |
| `health_message` | `TextField` | Human-readable diagnosis from last check |
| `last_seen_at` | `DateTimeField` | Timestamp of last successful API response |
| `last_health_check_at` | `DateTimeField` | Timestamp of last connectivity evaluation |
| `system_resources` | `JSONField` | Cached telemetry (CPU load, memory, uptime, latency) |

### 2.2 At-Rest Credential Encryption

Both Router management passwords and upstream Wi-Fi passwords are encrypted transparently using property descriptors:

```python
# apps/routers/models.py
@property
def api_password(self) -> str:
    if not self.api_password_encrypted:
        return ''
    return decrypt_secret(self.api_password_encrypted)

@api_password.setter
def api_password(self, value: str):
    if value:
        self.api_password_encrypted = encrypt_secret(value)
    else:
        self.api_password_encrypted = ''

@property
def has_credentials(self) -> bool:
    return bool(self.api_username and self.api_password_encrypted)
```

```python
# apps/companies/models.py (RouterUplinkProfile)
@property
def password(self) -> str:
    if not self.password_encrypted:
        return ''
    try:
        return decrypt_secret(self.password_encrypted)
    except Exception:
        return ''

@password.setter
def password(self, val: str):
    if val:
        self.password_encrypted = encrypt_secret(val)
    else:
        self.password_encrypted = ''
```

### 2.3 Zero-Leakage Guarantee

- Serializers (`RouterSerializer`, `RouterCreateSerializer`, `RouterCredentialsSerializer`) mark `api_password` as `write_only=True` and NEVER expose `api_password_encrypted`.
- API responses expose only `has_credentials: true/false` so operators know whether credentials have been provisioned without seeing sensitive secrets.

---

## 3. RouterOS API Client & Diagnostics

### 3.1 Hardened Client (`apps.routers.services.router_client.py`)

- Initialized via `RouterOSAPIClient.for_router(router, timeout=4.0)`.
- Enforces credentials presence prior to socket creation.
- Supports TLS via `ssl.create_default_context().wrap_socket(raw_sock)`.
- Handles binary RouterOS sentence length encoding (1, 2, and 3-byte variable lengths).

### 3.2 Structured Failure Taxonomy

| Error Code | Trigger Condition | Mapped Health Status |
|---|---|---|
| `CONNECTED` | Successful login & resource query | `ONLINE` |
| `ROUTER_CREDENTIALS_NOT_CONFIGURED` | Missing username or password | `UNKNOWN` |
| `CONNECTION_TIMEOUT` | Socket connect or login timeout | `UNREACHABLE` |
| `CONNECTION_REFUSED` | Port closed / API service disabled | `UNREACHABLE` |
| `HOST_UNREACHABLE` | No route to host / network down | `UNREACHABLE` |
| `AUTHENTICATION_FAILED` | Invalid credentials / `!trap` | `DEGRADED` |
| `TLS_ERROR` | SSL handshake failure | `DEGRADED` |
| `UNKNOWN_ERROR` | Unhandled OS/network exception | `OFFLINE` |

---

## 4. Background Telemetry & Celery Integration

### 4.1 Tasks (`apps.routers.tasks.py`)

1. **`poll_router_health_task(router_id: str, timeout: float = 4.0)`**:
   - Retrieves active router record.
   - Executes `collect_router_telemetry(router)`.
   - Updates `system_resources`, `health_status`, `health_message`, and timestamps in database.
2. **`poll_active_routers_task()`**:
   - Queries all active routers (`is_active=True`).
   - Dispatches parallel `poll_router_health_task.delay(router_id)` background jobs.

---

## 5. REST API Reference (`/api/v1/routers/`)

Mounted under `/api/v1/routers/`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/routers/` | List company routers (filters: `?location=`, `?health_status=`, `?is_active=`) |
| `POST` | `/api/v1/routers/` | Register new router with optional initial credentials |
| `GET` | `/api/v1/routers/<id>/` | Detailed router view including hardware identity |
| `PATCH` | `/api/v1/routers/<id>/` | Update router configuration (name, location, IP, port, interface) |
| `DELETE` | `/api/v1/routers/<id>/` | Safe deactivation (blocks deletion if active hotspots are hosted) |
| `POST` | `/api/v1/routers/<id>/credentials/` | Set or rotate encrypted API credentials |
| `POST` | `/api/v1/routers/<id>/test-connection/` | Fast live connection test returning diagnostic taxonomy |
| `GET` | `/api/v1/routers/<id>/health/` | Read cached telemetry & status from DB (non-blocking) |
| `POST` | `/api/v1/routers/<id>/refresh-health/` | On-demand live health check & DB cache refresh |

---

## 6. Verification Results

### 6.1 Database Schema Migrations
- `companies.0007_routeruplinkprofile_password_encrypted`: Added encrypted storage.
- `companies.0008_encrypt_uplink_passwords`: Data migration encrypting existing plaintext passwords at rest.
- `companies.0009_remove_routeruplinkprofile_password`: Dropped raw plaintext password column from database.
- `routers.0002_router_health_message_router_last_health_check_at_and_more`: Added health metrics and telemetry tracking fields to Router model.

### 6.2 Test Suite Execution
- **Full Backend Suite**: **150 / 150 passed (100%)** in 15.05s.
- **Router App Tests**: **15 / 15 passed (100%)** covering credentials encryption, connection testing, failure taxonomy, telemetry collection, and all API endpoints.
- **Anti-Tethering Tests**: **9 / 9 passed (100%)** verifying router-aware policy sync and legacy adoption.
- **Frontend Assets**: TypeScript check and Vite production build clean in 5.54s with **0 errors**.

### 6.3 Live Hardware Diagnostics
Tested against physical router record (`MikroTik HotSpot Gateway`, `10.5.50.1:8728`):
- Configured credentials securely via `set_router_credentials`.
- Live diagnostic accurately caught network state (`CONNECTION_TIMEOUT`, latency 2016ms), transitioned router health to `UNREACHABLE`, and cached the structured failure without thread blocking.
