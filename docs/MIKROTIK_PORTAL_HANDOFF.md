# MikroTik HotSpot SaaS Portal Handoff Protocol

Specification for integrating MikroTik RouterOS 6.49.19 HotSpot with the centralized SaaS captive portal in **Usimamizi Wi-Fi** (Phase 6).

---

## 1. Redirect Mechanism

When an unauthenticated client connects to the HotSpot network (`10.5.50.0/24`), MikroTik intercepts HTTP requests and displays `hotspot/login.html`:

```html
<script>
  var saasPortalBase = "http://192.168.1.163:5173/p/usimamizi-lab";
  var routerParams = "?link-login=" + encodeURIComponent("$(link-login-only)") +
                     "&mac=" + encodeURIComponent("$(mac)") +
                     "&ip=" + encodeURIComponent("$(ip)") +
                     "&link-orig=" + encodeURIComponent("$(link-orig)");
  window.location.href = saasPortalBase + routerParams;
</script>
```

---

## 2. Authentication Handoff

Upon successful voucher validation and atomic redemption on the SaaS portal:
1. The SaaS portal renders a hidden HTML form targeting `$(link-login-only)` (`http://10.5.50.1/login`).
2. The form automatically posts `username` and `password` matching the voucher code.
3. MikroTik HotSpot initiates a standard RADIUS Access-Request to FreeRADIUS / Django AAA.
4. Access-Accept is returned with dynamic bandwidth queues and Session-Timeout.
5. The client device is granted full internet access.
