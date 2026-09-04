# FRONTEND_GUIDE.md
## Wi-Fi Hotspot Management SaaS
### Frontend Design & UX Constitution

**Version:** 1.0  
**Status:** Mandatory  
**Applies to:** Tenant Web App, Platform Admin, Captive Portal, future mobile surfaces

---

## 1. Purpose

This document is the top-level frontend constitution for the Wi-Fi Hotspot Management SaaS.

Every frontend implementation agent must read this file before creating or modifying user-facing UI.

The product must feel:

- professional
- deliberate
- premium
- calm
- technically credible
- commercially trustworthy
- visually consistent
- easy to operate

The application must not look AI-generated, template-generated, or vibe-coded.

The product is infrastructure and business software. It manages money, routers, customers, internet access, vouchers, sessions and subscriptions. The UI must reflect that seriousness.

---

## 2. Product Character

The design language should communicate:

- reliable infrastructure software
- excellent operational clarity
- mature SaaS quality
- high information confidence
- restrained visual polish

Quality references include mature products such as Stripe, Linear, Vercel, Cloudflare, Notion and strong modern banking dashboards.

These are quality references only. Do not clone any product.

---

## 3. Core Design Principles

### 3.1 Clarity before decoration

Every screen must make it immediately clear:

1. where the user is
2. what the screen represents
3. what requires attention
4. what action can be taken
5. what the current state is

### 3.2 Information hierarchy matters

The application must visually distinguish:

- page title
- supporting context
- primary action
- important metrics
- operational warnings
- secondary detail

Do not make every card equally loud.

### 3.3 Calm interfaces feel more premium

Prefer:

- strong typography
- balanced spacing
- subtle borders
- restrained surfaces
- deliberate accent color
- compact but readable information density

Avoid:

- giant gradients
- glassmorphism
- decorative blobs
- neon colors
- oversized cards
- heavy shadows
- random illustrations
- excessive animation
- rainbow dashboards

### 3.4 Real data before visual theatre

Never invent metrics, trends or chart values for production UI.

If data does not exist, show an empty state or loading state.

### 3.5 Operational truth over visual optimism

If router data is stale, say it is stale.

If payment is pending, say pending.

If the router is unreachable, do not display a cheerful green icon because the last successful status was yesterday.

---

## 4. Product Surfaces

The frontend has three primary surfaces.

### Tenant SaaS

Used by:

- business owners
- administrators
- managers
- operators
- technicians

### Platform Administration

Used by the SaaS operator for:

- companies
- subscriptions
- router fleet
- system health
- support
- audits
- platform billing

### Captive Portal

Used by people connecting to Wi-Fi.

This surface has a fundamentally different UX objective and is specified separately in `CAPTIVE_PORTAL_SPECIFICATIONS.md`.

---

## 5. Visual Direction

The interface should feel:

- clean
- confident
- neutral
- technical
- precise
- modern
- human

It should not feel:

- futuristic for no reason
- toy-like
- crypto-themed
- gaming-inspired
- generic admin-template
- over-designed

A professional interface is not achieved by adding more visual effects. It is achieved by getting typography, spacing, hierarchy, state and interaction right.

---

## 6. Layout Principles

Desktop application shell:

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar │ Header                                             │
│         ├────────────────────────────────────────────────────│
│         │                                                    │
│         │ Main Content                                       │
│         │                                                    │
└──────────────────────────────────────────────────────────────┘
```

Recommended:

- expanded sidebar: 240–264px
- collapsed sidebar: 64–72px
- main content max width: roughly 1440px for standard pages
- data-heavy monitoring screens may exceed this where necessary

Do not stretch small forms or simple detail pages across enormous monitors.

---

## 7. Navigation

Tenant navigation should follow domain structure:

- Overview
- Network
  - Locations
  - Routers
  - Hotspots
  - Active Sessions
- Customers
  - Customers
  - Devices
- Sales
  - Payments
  - Plans
  - Vouchers
- Reports
- Team
- Settings

Platform Admin navigation:

- Overview
- Companies
- Subscriptions
- Router Fleet
- Payments
- System Health
- Support
- Audit Logs
- Platform Settings

Do not expose platform-level controls inside tenant interfaces.

---

## 8. Typography

Use one modern professional sans-serif family.

Preferred:

- Inter
- Geist
- IBM Plex Sans
- Manrope

One family should be selected for the project and used consistently.

Suggested hierarchy:

- Page title: 28–32px, 600–700
- Section heading: 18–20px, 600
- Card title: 14–16px, 500–600
- Body: 14–16px, 400
- Table: 13–14px
- Metadata: 12–13px

Do not use oversized numbers purely to make dashboards feel dramatic.

---

## 9. Color Philosophy

The application must support **both Light Mode and Dark Mode** as first-class product experiences.

Neither mode may be treated as an inversion or secondary skin. Both must preserve:

- hierarchy
- accessibility
- contrast
- semantic status meaning
- table readability
- chart readability
- form clarity
- focus states
- elevation
- disabled states

The application should be mostly neutral.

Use semantic color intentionally:

- brand/accent: primary actions, active navigation, focus, selected states
- green: success, healthy, online
- amber: warning, degraded, needs attention
- red: failure, offline, destructive
- blue: informational, in progress
- gray: neutral, inactive, expired

Status color meaning must remain consistent across the entire product.

---

## 10. Spacing

Use a fixed spacing scale.

Preferred:

- 4
- 8
- 12
- 16
- 20
- 24
- 32
- 40
- 48
- 64

Typical page padding:

- desktop: 24–32px
- large desktop: 32–40px
- mobile: 16px

Avoid arbitrary spacing values unless technically necessary.

---

## 11. Radius and Elevation

Recommended radius:

- buttons: 6–8px
- inputs: 6–8px
- cards: 8–12px
- modals: 12px

Avoid 20–30px rounded corners everywhere.

Use borders more often than shadows.

Shadows are appropriate for:

- dialogs
- dropdowns
- menus
- floating panels

Not every card needs to float.

---

## 12. Cards

Cards must group related information.

Do not make every section a card.

Avoid nested card-on-card layouts unless the information hierarchy genuinely requires them.

Prefer flatter layouts for:

- settings
- detail pages
- monitoring screens
- forms

---

## 13. Buttons

Required variants:

- Primary
- Secondary
- Ghost
- Destructive
- Link

Use direct verbs:

Good:

- Add Router
- Create Plan
- Generate Vouchers
- Save Changes
- Disconnect User

Avoid vague labels:

- Submit
- Proceed
- Click Here

Only one visually dominant primary action should normally exist within a section.

---

## 14. Forms

Forms must use visible labels.

Do not use placeholders as substitutes for labels.

Break long forms into logical sections.

Validation errors should appear next to relevant fields.

Technical configuration should be hidden under Advanced Settings where appropriate.

Normal business users should not be forced to understand internal networking terms.

---

## 15. Tables

Tables are a major product surface and must be excellent.

Where relevant support:

- search
- filters
- sorting
- pagination
- column visibility
- export
- row actions
- bulk actions

Numeric columns should align consistently.

Do not place many persistent icon buttons in every row.

Prefer row click plus an overflow menu.

---

## 16. Statuses

Use explicit business states.

Examples:

- ONLINE
- OFFLINE
- DEGRADED
- ACTIVE
- EXPIRED
- PENDING
- PAID
- FAILED
- SUSPENDED

Do not use ambiguous language such as “Done” where a precise domain status exists.

---

## 17. Dashboards

Dashboards must answer:

- How is the business performing?
- Is the network healthy?
- Is anything requiring attention?

Recommended first viewport:

- page header and filters
- 4 important metrics
- one meaningful trend
- network status or alerts

Secondary:

- recent payments
- active sessions
- popular plans
- router health

Do not put twelve KPI cards and seven charts on a page simply because chart components exist.

---

## 18. Charts

Preferred:

- line
- area
- bar
- stacked bar where meaningful

Avoid:

- 3D charts
- gauges
- speedometers
- decorative radar charts
- pie charts with many categories

Use one brand/accent series where possible and muted secondary series.

Charts must communicate a decision-relevant trend.

---

## 19. Loading, Empty and Error States

Every major screen must define:

- loading state
- empty state
- error state

Good empty state:

> No routers yet  
> Connect your first MikroTik router to begin managing hotspot access.  
> [Add Router]

Bad empty state:

> No data.

Errors must explain what failed and what the user can do.

---

## 20. Destructive Actions

Require deliberate confirmation for actions such as:

- disconnect active session
- revoke voucher
- block device
- refund payment
- suspend company
- reset router configuration
- delete draft data

Explain consequences.

Dangerous actions must be visually separated from normal actions.

---

## 21. Theme Modes

The authenticated SaaS and Platform Admin must support:

```text
Light
Dark
System
```

`System` follows the operating-system/browser preference.

Theme preference should persist per user where practical, with a local fallback before authentication.

Requirements:

- no visible flash of the wrong theme during initial load where technically avoidable
- shared components must use semantic design tokens rather than raw light-only colors
- charts must provide readable palettes in both themes
- code/log/diagnostic surfaces must remain readable in both themes
- status colors must preserve meaning in both themes
- logos/assets should provide light/dark-safe variants where required
- borders and surface hierarchy must remain visible in dark mode
- disabled controls must remain distinguishable from active controls

Do not implement dark mode by applying a global CSS inversion/filter.

---

## 22. Mobile

Mobile must be intentionally designed, not merely compressed desktop.

Do not shrink large tables until they are technically responsive but practically unusable.

For complex rows, use mobile list/card representations.

Primary mobile workflows include:

- dashboard check
- payment lookup
- voucher creation
- active session lookup
- router status
- basic reporting

---

## 23. Icons

Use one icon family consistently, preferably Lucide.

Icons support text. They do not replace text for unfamiliar actions.

Do not mix icon libraries or use emojis for product navigation.

---

## 24. Animation

Use animation for state communication only.

Typical duration:

- 150–250ms

Good:

- dialog transition
- dropdown transition
- save confirmation
- payment status change
- live router status update

Avoid:

- bouncing buttons
- animated gradients
- dramatic page transitions
- decorative motion

---

## 25. Accessibility

Minimum requirements:

- keyboard navigation
- visible focus states
- semantic HTML
- accessible form labels
- adequate contrast
- screen-reader-friendly errors
- status not communicated by color alone

---

## 26. Data Formatting

Currency:

`TZS 428,500`

Phone display:

`0712 345 678`

Phone storage/API normalization:

`+255712345678`

Dates:

`19 Aug 2026`

Date/time:

`19 Aug 2026, 21:42`

Data:

`824 MB`, `3.4 GB`, `1.2 TB`

Time remaining:

`2h 14m remaining`

Avoid ambiguous date formats.

---

## 27. Copywriting

Use plain, professional language.

Good:

> Main Router is offline.

Bad:

> NAS connectivity state transitioned to unavailable.

Technical details belong in diagnostics, not normal operational copy.

Avoid childish celebration language.

---

## 28. Frontend Architecture

Recommended:

```text
src/
├── app/
├── components/
│   ├── ui/
│   ├── layout/
│   └── domain/
├── features/
│   ├── dashboard/
│   ├── routers/
│   ├── hotspots/
│   ├── customers/
│   ├── payments/
│   ├── plans/
│   ├── vouchers/
│   └── reports/
├── hooks/
├── lib/
├── services/
├── types/
└── styles/
```

Feature modules should own feature-specific:

- components
- hooks
- API functions
- schemas
- types
- utilities

---

## 29. API Access

Centralize HTTP/API behavior.

Do not scatter `fetch()` calls across components.

Central handling should cover:

- auth
- token refresh
- errors
- tenant context
- request IDs
- retry policy where safe

---

## 30. State Management

Use server-state tools for backend data.

Do not duplicate large backend datasets into global client state.

Global client state should normally be limited to:

- authenticated user
- active company
- selected location context
- theme
- UI preferences

---

## 31. TypeScript

Use strict TypeScript.

Avoid `any` unless unavoidable and documented.

Frontend types must clearly match backend API contracts.

---

## 32. Mutations

Every mutation must support:

- idle
- loading
- success
- error

Prevent accidental duplicate submission.

Do not optimistically update:

- payments
- refunds
- router provisioning
- subscription changes
- financial state transitions

Wait for backend confirmation.

---

## 33. Role-Aware UI

Hide or disable unavailable actions where appropriate.

Backend permissions remain authoritative.

Frontend role checks are UX, not security.

---

## 34. Agent Prohibitions

Agents must not:

- invent random gradients
- add glassmorphism without explicit approval
- add decorative blobs
- use giant rounded cards everywhere
- give each KPI a random bright color
- invent charts or fake metrics
- use emojis as navigation icons
- turn every screen into a dashboard
- add unnecessary tabs
- add animations for decoration
- use lorem ipsum
- add mock data to production paths
- introduce unapproved fonts
- introduce arbitrary colors outside tokens
- put business logic inside React components

---

## 35. Screen Implementation Checklist

Before implementing any screen, the agent must identify:

- screen purpose
- primary user
- primary action
- secondary actions
- data required
- filters
- permissions
- loading state
- empty state
- error state
- mobile behavior
- destructive actions

---

## 36. UI Quality Gate

A frontend task is not complete because the project compiles.

It must pass:

- visual hierarchy review
- responsive review
- empty state review
- loading review
- error review
- permission review
- accessibility review
- real-data review

Major screens must be inspected at:

- 1440px desktop
- 1024px tablet
- 390px mobile

---

## 37. Mandatory Reading Order for Agents

Before frontend implementation:

1. `PROJECT_ARCHITECTURE.md`
2. `FRONTEND_GUIDE.md`
3. `UI_DESIGN_SYSTEM.md`
4. `WEB_SCREEN_SPECIFICATIONS.md` or `CAPTIVE_PORTAL_SPECIFICATIONS.md`
5. relevant API contract/documentation

If a later approved screen specification explicitly overrides this document for a specific screen, the explicit screen specification wins for that screen only.

Otherwise, this document is the frontend constitution.
