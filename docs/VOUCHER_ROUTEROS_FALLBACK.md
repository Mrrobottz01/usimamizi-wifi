# RouterOS Local HotSpot Fallback Architecture

## 1. Concept & Rationale

In distributed and rural ISP environments, internet uplink or WAN connectivity between the MikroTik gateway and the central Usimamizi cloud AAA server can occasionally experience interruptions (fiber cuts, cellular modem dropouts, tower power failure).

To guarantee business continuity and uninterrupted offline sales, Usimamizi provides **Local Fallback Vouchers**.

---

## 2. Central SaaS Vouchers vs. Local Fallback Vouchers

| Dimension | Central SaaS Vouchers (`CENTRAL_SAAS`) | Local Fallback Vouchers (`LOCAL_FALLBACK`) |
| :--- | :--- | :--- |
| **Authentication Engine** | Central FreeRADIUS REST API (`api/v1/radius/authorize/`) | Local RouterOS `/ip hotspot user` database |
| **Accounting** | Central cumulative database accounting with byte & time deltas | Local RouterOS `/ip hotspot active` counters |
| **Bandwidth Control** | Dynamic RADIUS `Mikrotik-Rate-Limit` attribute | Pre-configured RouterOS `/ip hotspot user profile` |
| **Session Disconnect** | Remote RFC 3576 Disconnect-Request (POD) via UDP 3799 | Local WinBox/CLI manual session termination |
| **Export Status Badge** | `Active Cloud` | `Exported (.rsc)` |
| **Typical Deployment** | 99% of normal operations | Emergency offline fallback batches pre-loaded on router |

---

## 3. RouterOS Export Script Specification (`.rsc`)

When a batch is exported via the Voucher Hub or API endpoint `/api/v1/voucher-batches/{id}/export-routeros/`:
1. The batch and its constituent vouchers are tagged with `export_status = EXPORTED_ROUTEROS`.
2. A RouterOS CLI command script is synthesized:

```routeros
# ===================================================================
# USIMAMIZI WI-FI - ROUTEROS LOCAL HOTSPOT FALLBACK USER EXPORT
# SOURCE: USIMAMIZI_LOCAL_FALLBACK | BATCH: VB-20260904-8BQDQC
# PLAN: 3 Minutes Test Pass (3min-test)
# GENERATED AT: 2026-09-04T20:37:09+00:00
# TOTAL USERS: 5
# NOTE: Use only during central SaaS outage or isolated offline nodes.
# ===================================================================

/ip hotspot user add name="5D78-654J" password="5D78-654J" profile="3min-test" comment="USIMAMIZI_FALLBACK Batch: VB-20260904-8BQDQC"
/ip hotspot user add name="8TW2-Q36V" password="8TW2-Q36V" profile="3min-test" comment="USIMAMIZI_FALLBACK Batch: VB-20260904-8BQDQC"
/ip hotspot user add name="BSYY-UTRK" password="BSYY-UTRK" profile="3min-test" comment="USIMAMIZI_FALLBACK Batch: VB-20260904-8BQDQC"
/ip hotspot user add name="CQ9W-EFGR" password="CQ9W-EFGR" profile="3min-test" comment="USIMAMIZI_FALLBACK Batch: VB-20260904-8BQDQC"
/ip hotspot user add name="GQGR-EWV4" password="GQGR-EWV4" profile="3min-test" comment="USIMAMIZI_FALLBACK Batch: VB-20260904-8BQDQC"
```

---

## 4. Operational Runbook: Importing into RouterOS

### Method 1: RouterOS Terminal
1. Connect to the router CLI via SSH or WinBox Terminal (`admin@10.5.50.1`).
2. Paste the contents of the generated `.rsc` file.
3. Users are instantly active in `/ip hotspot user print`.

### Method 2: FTP / SFTP Script Upload
1. Upload `VB-20260904-8BQDQC.rsc` to the router root directory.
2. In RouterOS Terminal, execute:
   ```routeros
   /import file-name=VB-20260904-8BQDQC.rsc
   ```
3. Verify output:
   ```routeros
   /ip hotspot user print where comment~"USIMAMIZI_FALLBACK"
   ```
