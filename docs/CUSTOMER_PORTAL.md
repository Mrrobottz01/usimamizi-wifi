# Usimamizi Wi-Fi: Customer Self-Service Portal

## 1. Overview & Accessibility

The **Customer Self-Service Portal** gives Wi-Fi users complete transparency into their active plan, remaining time, and connected devices without needing staff assistance.

- **URL Routes**:
  - `https://wifi.domain/p/:slug/account`
  - `https://wifi.domain/portal/:slug/account`
- **Device Support**: Mobile-first responsive web application.
- **Languages**: Bilingual English (`EN`) and Kiswahili (`SW`).

---

## 2. Passwordless Authentication Flow

Customers authenticate securely via SMS OTP without memorizing passwords:

```text
Customer enters phone number (e.g. 0712345678)
                  │
                  ▼
System normalizes to canonical E.164 (+255712345678)
                  │
                  ▼
Generates 6-digit random code (e.g. 582910)
                  │
                  ├──────────────────────────────┐
                  ▼                              ▼
Calculates SHA-256 hash           Dispatches plaintext SMS via
Stores hash in CustomerOTP        RafikiSMS to phone
(Plaintext is NEVER saved)
                  │
                  ▼
Customer submits 6-digit code in portal
                  │
                  ▼
System compares SHA-256(input) == stored hash
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
Match verified        Incorrect code
Generates signed      Increments attempts counter
session token         (Locks after 3 failed attempts)
```

### Security Properties
1. **Hash at Rest**: SHA-256 cryptographic hashing prevents exposure of OTPs in database dumps or query logs.
2. **Short Expiry**: Code expires strictly after 5 minutes (configurable per tenant).
3. **Resend Cooldown**: 60-second minimum interval between OTP generation requests prevents SMS spamming.
4. **Tamper-Proof Session Token**: Uses Django cryptographic signing (`signing.dumps`) with salt isolation.

---

## 3. Customer Dashboard Features

Once authenticated, the customer sees:

### 1. Real-Time Time Remaining Countdown
- Live ticking display in `HH:MM:SS` (or days + hours).
- Clear expiration date and time.
- Plan name and download/upload speed ratings.

### 2. Lossless Self-Service Plan Renewal
- Choose current plan or switch to a new high-speed tier.
- Select payment method: M-Pesa, Airtel Money, or Mixx by Yas.
- Dispatches instant USSD payment prompt to the customer's phone via Snippe.
- As soon as the customer enters their mobile money PIN, the new period appends strictly after their existing paid time.

### 3. Self-Service Device Disconnect (Device Portability)
- With anti-tethering and `simultaneous_sessions=1` active, a customer who buys a new phone or wants to use their laptop might be blocked by the existing session.
- The "Vifaa Vyangu / Connected Devices" card displays the active MAC addresses and allows the customer to click **"Tenganisha / Disconnect"**.
- This immediately issues an RFC 3576 POD Disconnect-Request to MikroTik, releasing the hotspot IP/MAC binding in real time so the user can immediately connect their new device.
