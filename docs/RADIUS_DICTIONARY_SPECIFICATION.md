# RADIUS Dictionary & Vendor Attribute Specification

**System Name:** Usimamizi Wi-Fi  
**Vendor:** MikroTik (Vendor ID: `14988`)  

---

## 1. Standard RADIUS Attributes

The SaaS backend sends standard RFC RADIUS attributes in `Access-Accept` responses:

| Attribute Name | ID | Type | Purpose | Example Value |
| :--- | :--- | :--- | :--- | :--- |
| `Session-Timeout` | 27 | integer | Maximum allowed continuous connection time in seconds. Router automatically terminates session upon expiry. | `3600` (1 hour) |
| `Idle-Timeout` | 28 | integer | Disconnects client if zero traffic observed for specified seconds. | `300` (5 minutes) |
| `Acct-Interim-Interval` | 85 | integer | Interval in seconds between periodic RADIUS Interim-Update accounting packets sent by router. | `60` (1 minute) |

---

## 2. MikroTik Vendor-Specific Attributes (VSA)

MikroTik-specific attributes returned in `Access-Accept` responses:

| Attribute Name | Vendor ID | Type | Format / Purpose | Example Value |
| :--- | :--- | :--- | :--- | :--- |
| `Mikrotik-Rate-Limit` | 14988 / 8 | string | Bandwidth rate limit: `rx-rate[/tx-rate]` (Upload/Download). Configures RouterOS dynamic simple queue. | `"3M/10M"` (3Mbps Rx, 10Mbps Tx) |
| `Mikrotik-Group` | 14988 / 3 | string | Assigns user to local RouterOS user group if needed. | `"default"` |
| `Mikrotik-Wireless-PSK` | 14988 / 9 | string | Dynamic WPA/WPA2 passphrase assignment. | `"SecretKey123"` |

---

## 3. Accounting Packet Fields

MikroTik sends the following accounting attributes in `Accounting-Request` packets:

- `Acct-Status-Type`: `Start`, `Interim-Update`, `Stop`
- `Acct-Session-Id`: Unique session correlation ID
- `Calling-Station-Id`: Device MAC address (`AA:BB:CC:DD:EE:FF`)
- `Framed-IP-Address`: Client IP address (`10.5.50.X`)
- `Acct-Input-Octets` / `Acct-Input-Gigawords`: Data uploaded by client (bytes)
- `Acct-Output-Octets` / `Acct-Output-Gigawords`: Data downloaded by client (bytes)
- `Acct-Session-Time`: Session elapsed time (seconds)
- `Acct-Terminate-Cause`: `User-Request`, `Session-Timeout`, `Lost-Carrier`, `Admin-Reset`
