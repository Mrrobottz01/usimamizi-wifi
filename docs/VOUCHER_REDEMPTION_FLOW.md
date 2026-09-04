# Voucher Redemption Flow & AAA Architecture

## 1. End-to-End Sequence Diagram

```
End-User Device            Captive Portal            Django Backend            FreeRADIUS AAA            MikroTik HotSpot
      │                          │                          │                        │                         │
      │── 1. Connect Wi-Fi ─────▶│                          │                        │                         │
      │◀─ 2. HTTP 302 Redirect ──│                          │                        │                         │
      │                          │                          │                        │                         │
      │── 3. Submit Voucher ────▶│                          │                        │                         │
      │   (e.g. "abcd 7xq9")     │                          │                        │                         │
      │                          │── 4. POST /voucher/ ────▶│                        │                         │
      │                          │   (normalized to ABCD)   │                        │                         │
      │                          │                          │── 5. Redeem & Create ─▶│                         │
      │                          │                          │   AccessEntitlement    │                         │
      │                          │◀─ 6. Login credentials ──│                        │                         │
      │                          │   (username, password)   │                        │                         │
      │                          │                          │                        │                         │
      │◀─ 7. Auto-submit form ───│                          │                        │                         │
      │   to http://10.5.50.1/login                         │                        │                         │
      │                                                     │                        │                         │
      │── 8. POST /login (username=ABCD-7XQ9) ──────────────┼────────────────────────┼────────────────────────▶│
      │                                                     │                        │◀─ 9. Access-Request ────│
      │                                                     │◀─ 10. POST /authorize  │   (User=ABCD-7XQ9)      │
      │                                                     │── 11. 200 Accept ─────▶│                         │
      │                                                     │   (Rate-Limit, Expiry) │                         │
      │                                                     │                        │── 12. Access-Accept ───▶│
      │                                                     │                        │   (Session-Timeout)     │
      │                                                     │                        │                         │
      │◀─ 13. Internet Access Granted (Full Speed) ─────────┼────────────────────────┼─────────────────────────│
```

---

## 2. Dynamic FreeRADIUS Attribute Enforcement

Upon receiving `/api/v1/radius/authorize/`, the backend computes dynamic attributes based on the snapshot of the plan linked to the entitlement:

```json
{
  "accept": true,
  "code": "Access-Accept",
  "reply": {
    "Session-Timeout": 180,
    "Idle-Timeout": 300,
    "Acct-Interim-Interval": 60,
    "Mikrotik-Rate-Limit": "2000k/5000k",
    "WISPr-Bandwidth-Max-Down": 5000000,
    "WISPr-Bandwidth-Max-Up": 2000000
  }
}
```

- **Session-Timeout**: Bounded by the exact remaining continuous or usage seconds. If 152 seconds remain, RouterOS receives `Session-Timeout = 152` and disconnects the user automatically when the timer reaches 0.
- **Mikrotik-Rate-Limit**: Formatted as `UploadRate/DownloadRate` (e.g. `2000k/5000k` for 2 Mbps upload and 5 Mbps download).
- **Acct-Interim-Interval**: Mandates periodic accounting packets every 60 seconds.

---

## 3. Real-Time RADIUS Accounting & Quota Enforcement

1. **Accounting-Start**: Records active session in `HotspotSession` table with IP, MAC, NAS IP, and initial timestamp.
2. **Accounting-Interim-Update**: Computes positive byte and time deltas, updating `AccessEntitlement` cumulative usage.
3. **Accounting-Stop**: Closes `HotspotSession` with termination cause (e.g., `Session-Timeout`, `User-Request`, `Lost-Carrier`).

If cumulative bytes exceed `data_limit_bytes` during an interim update, subsequent re-authorizations are rejected immediately with `DATA_QUOTA_EXHAUSTED`.

---

## 4. Cascading Revocation & RFC 3576 Disconnect (POD)

When an administrator revokes a voucher:
1. Voucher status transitions to `REVOKED`.
2. Linked `AccessEntitlement` transitions to `REVOKED`.
3. An RFC 3576 Packet of Disconnect (POD) is dispatched via UDP port 3799 directly to the NAS gateway (`10.5.50.1`).
4. MikroTik RouterOS unauthenticates the user and tears down firewall bypassing within milliseconds.
