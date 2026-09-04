# Captive Portal Security & Hardening Policy

Security controls, anti-abuse measures, and privacy standards in **Usimamizi Wi-Fi** (Phase 6).

---

## 1. Security Safeguards

1. **Cross-Tenant Voucher Isolation:** Strict SQL filtering ensures Company A's portal cannot validate or redeem Company B's vouchers under any circumstance.
2. **Brute-Force & Enumeration Mitigation:** Rate limiting on `/voucher/` endpoint; invalid voucher responses use uniform error timing and normalized messages.
3. **No Arbitrary HTML/JS Injection:** Portal branding tokens only accept controlled strings and sanitized hex color tokens. Raw HTML/JS injection is strictly prohibited.
4. **No Customer Browsing Surveillance:** The SaaS portal and AAA infrastructure only record standard RADIUS accounting session statistics (duration, input bytes, output bytes). Visited URLs, browsing destinations, and packet contents are never monitored or stored.
