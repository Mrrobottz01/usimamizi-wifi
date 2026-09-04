# CAPTIVE_PORTAL_SPECIFICATIONS.md
## Wi-Fi Hotspot Management SaaS
### Customer-Facing Captive Portal UX & Visual Specification

**Version:** 1.0  
**Status:** Mandatory  
**Depends on:** `PROJECT_ARCHITECTURE.md`, `FRONTEND_GUIDE.md`, `UI_DESIGN_SYSTEM.md`

---

# 1. Purpose

The Captive Portal is the public customer experience shown when a person connects to a managed Wi-Fi hotspot.

Its goal is not to demonstrate the sophistication of the SaaS.

Its goal is:

> Get the customer online quickly, safely and confidently.

The entire flow must be mobile-first, low-bandwidth and understandable to non-technical users.

---

# 2. Primary Success Metric

A normal paying customer should be able to go from:

```text
Connect to Wi-Fi
→ choose plan
→ enter phone
→ pay
→ connect
```

with minimal friction.

Target UX:

- understandable within seconds
- few fields
- no technical terminology
- clear price
- clear package terms
- trustworthy payment state
- clear internet activation result

---

# 3. Portal Character

The portal should feel:

- fast
- clean
- trustworthy
- locally appropriate
- branded
- simple
- premium but restrained

Avoid:

- marketing-page complexity
- giant hero sections
- multiple carousels
- glassmorphism
- animated backgrounds
- oversized illustrations
- heavy JavaScript
- decorative charts
- long forms

The customer is trying to get internet, not admire a web-design portfolio.

---

# 4. Performance Requirements

The portal must be lightweight because the user does not yet have ordinary internet access.

Prioritize:

- minimal JavaScript
- optimized assets
- locally served critical assets where possible
- minimal font payload
- no unnecessary third-party dependencies
- small images
- resilient loading

Avoid external dependencies that are not included in the hotspot walled garden.

---

# 5. Mobile-First Layout

Primary target:

- 360–430px phone viewport

Secondary:

- tablet
- laptop

Content width should remain compact on large screens.

Typical desktop portal should look like a centered mobile-oriented experience, not a full SaaS dashboard.

---

# 6. Theme & Tenant Branding

The captive portal must be visually safe in both light and dark environments.

For MVP, the portal may use either:

- tenant-selected Light or Dark presentation, or
- automatic `System` mode where approved by product configuration.

If a portal offers user-selectable themes, it must use the same semantic token approach as the main product.

Payment, voucher and connection-status screens must remain equally readable in both themes.

Supported customization:

- logo
- business name
- approved accent color
- welcome heading
- short message
- background image or subtle visual if approved
- support phone
- WhatsApp number
- terms link

Tenant branding must remain inside safe design constraints.

Do not allow arbitrary tenant CSS.

Do not allow brand choices to break:

- contrast
- button readability
- spacing
- layout
- status semantics

---

# 7. Shared Portal Shell

Typical:

```text
Logo / Business Name

Primary content

Help / Support
Terms
Powered by [Platform] optional/configurable
```

Navigation should be minimal.

---

# 8. Welcome Screen

## Purpose

Identify network and immediately present access options.

Recommended:

```text
[Logo]

Welcome to Mlimani Wi-Fi

Fast, reliable internet access.

Choose a package

[Plan cards]

Already have a voucher?
[Use Voucher]

Need help?
```

Do not require account creation before package selection.

---

# 9. Plan Card

Show only decision-relevant attributes.

Example:

```text
DAY PASS

24 Hours
Up to 5 Mbps

TZS 2,000

[Choose Plan]
```

Optional:

- data limit
- device count

Only show these if materially relevant.

Avoid technical properties such as:

- idle timeout
- RADIUS attributes
- NAS profile names

---

# 10. Plan Ordering

Recommended:

- most common/recommended first
- shorter duration
- longer duration
- weekly/monthly

A tenant may control ordering.

A “Popular” label may be supported but should not be fabricated from fake analytics unless explicitly configured.

---

# 11. Phone Entry

After choosing a plan:

```text
Day Pass
TZS 2,000

Mobile number
[07XXXXXXXX]

We will use this number for payment and access.

[Continue]
```

Normalize phone number in backend/API.

Provide useful validation.

Do not ask for:

- full name
- email
- address
- birthday

unless a specific business workflow requires it.

---

# 12. Payment Method Selection

Display configured methods only.

Example:

```text
Choose payment method

[ M-Pesa ]
[ Airtel Money ]
[ Mixx by Yas ]

Pay TZS 2,000
```

Show:

- selected plan
- total amount
- phone number
- provider

before initiating payment.

---

# 13. Payment Initiation

When user submits:

- disable duplicate submission
- show immediate progress
- create backend order first
- obtain payment request status
- transition to pending state

Do not claim success based on frontend request acceptance.

---

# 14. Payment Pending

Recommended:

```text
Check your phone

We sent a payment request to:
0712 345 678

Approve the TZS 2,000 payment to activate your internet.

Waiting for confirmation…
```

Actions:

- I have paid / Check status, if backend flow requires manual refresh fallback
- Change number
- Cancel where safe

Use automatic polling or real-time update where supported.

Do not use anxiety-inducing countdown animation.

---

# 15. Payment Success

Recommended:

```text
You're connected

Day Pass

Valid until
20 Aug 2026, 21:43

Speed
Up to 5 Mbps

[Start Browsing]
```

Optional:

- data limit
- device count
- phone number

Do not add unnecessary celebration animation.

---

# 16. Payment Failed

Recommended:

```text
Payment was not completed

No charge was confirmed for this request.

[Try Again]
[Choose Another Method]
```

If provider gives a safe actionable reason, show it.

Do not reveal internal provider errors or stack traces.

---

# 17. Payment Expired

Recommended:

```text
Payment request expired

Start a new payment request to continue.

[Try Again]
```

Never reuse an expired payment attempt as if it were current.

---

# 18. Voucher Entry

Screen:

```text
Use Voucher

Voucher code
[XXXX-XXXX]

[Connect]
```

Validation:

- available
- expired
- already redeemed
- revoked
- invalid

Use clear user language.

---

# 19. Voucher Success

```text
Voucher accepted

24 Hour Access

Valid until:
20 Aug 2026, 21:43

[Connect]
```

Redemption must be idempotent and backend-controlled.

---

# 20. Returning User

If recognized safely:

```text
Welcome back

You have active internet access.

Day Pass
2h 14m remaining

[Continue]
```

Do not force another payment when a valid entitlement exists.

---

# 21. Existing Active Entitlement

Show:

- package
- expiry or usage remaining
- device allowance if relevant
- connection status

Actions:

- Continue
- Buy Another Package only when business logic permits
- View Access Status

---

# 22. Access Status Screen

Show:

```text
Internet Access

ACTIVE

Day Pass

Started
19 Aug 2026, 21:43

Expires
20 Aug 2026, 21:43

Data Used
3.4 GB
```

If usage data is not reliable/live, do not pretend it is.

---

# 23. Expired Access

```text
Your package has expired

Choose a new package to continue using the internet.

[View Packages]
```

Keep copy direct.

---

# 24. Device Limit Reached

Example:

```text
Device limit reached

This package allows 1 active device.

Disconnect another device or purchase a package that supports more devices.
```

Only show actions supported by backend business rules.

---

# 25. Blocked Device

```text
Internet access unavailable

This device has been blocked by the hotspot operator.

Contact support for assistance.
```

Do not expose internal security/audit details.

---

# 26. Free Access

Where configured:

```text
Free Wi-Fi

30 minutes free today

[Start Free Access]
```

Clearly communicate:

- duration
- data if limited
- eligibility
- expiry

Do not create hidden recurring commitments.

---

# 27. Support

Support screen may show:

- business name
- phone
- WhatsApp
- front desk/in-person note
- troubleshooting basics

Example:

```text
Need help?

Call:
0712 345 678

WhatsApp:
0712 345 678
```

Do not expose SaaS platform support unless business model requires it.

---

# 28. Terms & Privacy

Accessible before payment.

Keep short summaries available with link to full legal text where appropriate.

Customer should understand:

- pricing
- package validity
- refunds/cancellation policy where applicable
- acceptable use
- basic privacy information

---

# 29. Captive Network Detection

The portal must support realistic captive portal behavior.

Expected sequence:

```text
Device joins Wi-Fi
→ operating system captive check
→ MikroTik intercepts
→ portal opens
→ customer authenticates/pays
→ MikroTik permits internet
```

Test on:

- Android
- iOS
- Windows
- macOS

Do not assume browser behavior is identical across devices.

---

# 30. Walled Garden Dependencies

Before authentication, the user must be able to reach required portal/payment endpoints.

Provisioning must account for:

- portal domain
- API endpoints required by portal
- payment dependencies
- static assets
- DNS behavior
- provider redirects if used

Avoid pulling arbitrary assets from domains not allowed pre-authentication.

---

# 31. Payment Polling

If webhook confirmation occurs asynchronously:

- portal polls a safe order-status endpoint
- polling has reasonable interval/backoff
- stops at final state
- handles expiry
- does not create new payments

Never poll the payment provider directly from the browser using secret credentials.

---

# 32. Security

Portal APIs must:

- validate hotspot context
- validate plan availability
- validate amount server-side
- prevent price tampering
- rate limit abuse
- validate phone input
- prevent voucher brute forcing
- use secure order references
- never expose secrets

The browser is not trusted.

---

# 33. Price Integrity

Never trust:

```text
plan_price from frontend
```

Backend determines:

- plan
- tenant
- hotspot availability
- price
- currency
- payment amount

Frontend displays backend-provided price.

---

# 34. Voucher Security

Voucher entry must be protected against automated guessing.

Consider:

- rate limiting
- attempt throttling
- sufficiently random codes
- server-side redemption transaction
- secure logging

Do not expose entire voucher batches publicly.

---

# 35. Error Handling

Portal errors must be written for ordinary customers.

Good:

> We couldn't start the payment request. Please try again.

Bad:

> HTTP 500: ProviderAdapterException.

Technical details belong in backend logs.

---

# 36. Network Error

If portal loses cloud connectivity:

```text
We're having trouble connecting to the service.

Please try again in a moment.
```

Where offline/local access modes are later implemented, behavior must follow architecture, not frontend guesses.

---

# 37. Accessibility

The portal must support:

- readable text size
- adequate contrast
- labeled form fields
- keyboard use on desktop
- large touch targets
- clear focus
- status text beyond color

---

# 38. Localization

Architecture should allow:

- English
- Swahili

Do not concatenate translated strings in ways that make localization difficult.

Currency and date formatting must respect configured locale.

---

# 39. Language Selector

If multiple languages enabled:

use a simple selector:

```text
English | Kiswahili
```

Keep it visible but secondary.

---

# 40. Portal Screen Inventory

Required MVP:

1. Welcome / Plans
2. Phone Entry
3. Payment Method
4. Payment Pending
5. Payment Success
6. Payment Failed
7. Voucher Entry
8. Voucher Result
9. Access Status
10. Help
11. Terms

Optional later:

- account/history
- device management
- promotions
- sponsored access

---

# 41. Portal Component Set

Reusable:

- PortalShell
- BusinessLogo
- PlanCard
- MoneyValue
- PhoneInput
- PaymentMethodCard
- PaymentStatusPanel
- VoucherInput
- AccessStatusCard
- SupportPanel
- LanguageSelector
- InlineAlert
- LoadingState

Do not import the entire complex admin UI system into the captive portal if it increases payload substantially.

---

# 42. Portal Visual Constraints

Portal components must be checked in both Light and Dark theme variants whenever both are enabled for that tenant/product configuration.

Preferred:

- one brand accent
- white/neutral surface
- clear contrast
- 8–12px radii
- moderate spacing
- minimal shadows

Avoid:

- enormous hero image
- video
- animated backgrounds
- translucent cards
- complex illustration systems
- multiple fonts

---

# 43. Portal Header

Keep compact.

Use:

- logo
- business name
- language selector if needed

No dashboard navigation.

---

# 44. Portal Footer

May include:

- support
- terms
- privacy
- powered-by platform branding if commercial model requires it

Keep subtle.

---

# 45. Analytics

Portal may collect operationally necessary events:

- portal opened
- plan viewed/selected
- payment initiated
- payment succeeded/failed
- voucher attempted/redeemed
- access activated

Do not collect invasive analytics without clear reason.

---

# 46. Testing Matrix

Test each major flow on:

### Android
- Chrome
- captive portal window

### iPhone
- captive portal assistant
- Safari handoff where applicable

### Windows
- captive network prompt
- browser

### macOS
- captive network assistant
- browser

Also test:

- slow network
- payment delayed
- payment callback duplicate
- user closes portal mid-payment
- phone reconnects after payment
- voucher already redeemed
- entitlement already active
- session expired

---

# 47. Acceptance Flow: Payment

```text
Connect Wi-Fi
→ portal opens
→ choose valid plan
→ enter phone
→ choose provider
→ initiate payment
→ provider confirms
→ backend marks PAID
→ entitlement created
→ authentication succeeds
→ internet available
→ success/status screen reflects active access
```

No manual staff intervention.

---

# 48. Acceptance Flow: Voucher

```text
Connect Wi-Fi
→ portal opens
→ Use Voucher
→ enter valid code
→ backend atomically redeems voucher
→ entitlement created
→ internet available
```

Second redemption attempt must fail safely.

---

# 49. Agent Rules

Agents implementing portal screens must not:

- expose technical networking terms
- add unnecessary registration
- add marketing sections without requirement
- load huge assets
- trust frontend prices
- simulate payment success
- create fake “connected” state
- use fake timers
- invent provider states
- expose API keys
- bypass backend entitlement logic

---

# 50. Definition of Done

A portal feature is done only when:

- mobile layout is polished
- loading exists
- failure exists
- retry behavior exists
- payment/access truth comes from backend
- slow network is handled
- accessibility checked
- captive browser tested
- walled garden dependencies documented
- no fake production data exists

The portal should feel almost boring in its simplicity.

That is desirable.

People are there to buy internet and continue with their lives.
