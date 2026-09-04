# UI_DESIGN_SYSTEM.md
## Wi-Fi Hotspot Management SaaS
### Exact Visual Tokens, Components & Interaction Standards

**Version:** 1.0  
**Status:** Mandatory Design System  
**Depends on:** `FRONTEND_GUIDE.md`

---

## 1. Purpose

This document translates the frontend constitution into implementation-level design rules.

Agents must use these tokens and component patterns consistently.

Do not create a second local design system inside a feature.

---

## 2. Design System Philosophy

The system should use:

- neutral surfaces
- one primary brand accent
- restrained semantic colors
- tight visual consistency
- professional typography
- moderate density
- subtle elevation
- predictable interaction

Do not introduce visual novelty at feature level.

---

## 3. Recommended Technical Foundation

Preferred stack:

- React
- TypeScript
- Tailwind CSS
- Radix primitives or equivalent accessible primitives
- Lucide icons
- React Hook Form
- Zod
- TanStack Query
- TanStack Table
- Recharts or another restrained chart library

A component library may be used as a primitive foundation, but default styling must be customized to this design system.

Do not ship obvious stock-template styling.

---

## 4. Typography Tokens

Recommended primary font:

`Inter`

Fallback:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
```

Scale:

| Token | Size | Line height | Weight |
|---|---:|---:|---:|
| display-sm | 30px | 36px | 650–700 |
| heading-lg | 24px | 32px | 650 |
| heading-md | 20px | 28px | 600 |
| heading-sm | 16px | 24px | 600 |
| body-lg | 16px | 24px | 400 |
| body | 14px | 21px | 400 |
| body-medium | 14px | 21px | 500 |
| small | 13px | 18px | 400 |
| caption | 12px | 16px | 400 |

Use tabular numerals for:

- money
- data usage
- durations
- KPI values
- router metrics

where supported.

---

## 5. Color Tokens

Exact brand colors should be finalized when product branding is approved.

Until then use semantic token names, never feature-level raw colors.

Required tokens:

```text
--bg-app
--bg-surface
--bg-subtle
--bg-elevated

--border-default
--border-strong
--border-focus

--text-primary
--text-secondary
--text-muted
--text-inverse

--brand
--brand-hover
--brand-subtle

--success
--success-subtle
--warning
--warning-subtle
--danger
--danger-subtle
--info
--info-subtle
```

Every component consumes tokens, not arbitrary color literals.

---

## 6. Theme Architecture

The design system must support three user-facing theme preferences:

```text
light
dark
system
```

Implementation requirements:

- theme choice must live at application-shell level
- `system` must react to `prefers-color-scheme`
- user preference should persist
- theme must be applied before main UI paint where practical to avoid flashing
- components consume semantic CSS variables/tokens
- no feature should branch into a separate unrelated dark-mode design system

The same semantic token names are used in both modes. Only token values change.

### Required theme token groups

```text
background
surface
surface-subtle
surface-elevated
border
border-strong
text-primary
text-secondary
text-muted
brand
success
warning
danger
info
focus-ring
overlay
shadow
```

### Asset behavior

Logos, charts, illustrations and router/network diagrams must remain legible in both modes. When one asset cannot work on both backgrounds, provide controlled light/dark variants rather than CSS hacks.

---

## 8. Suggested Neutral Baseline

Light mode concept:

```text
App background: very light neutral
Surface: white
Subtle surface: soft gray
Primary text: near-black neutral
Secondary text: dark gray
Muted text: medium gray
Borders: light neutral gray
```

Dark mode concept:

```text
App background: near-black neutral
Surface: slightly lighter neutral
Subtle surface: medium-dark neutral
Primary text: soft white
Secondary text: light gray
Muted text: medium gray
Borders: subtle dark gray
```

Avoid pure black and pure white as the only large-area colors.

---

## 8. Semantic Color Rules

Green:

- payment successful
- router online
- entitlement active
- healthy state

Amber:

- degraded router
- pending attention
- expiring
- warning state

Red:

- router offline
- failed payment
- destructive action
- blocked state
- critical alert

Blue:

- informational
- synchronization
- in-progress workflow

Gray:

- expired
- inactive
- neutral state

---

## 9. Spacing Tokens

Use:

```text
space-1 = 4px
space-2 = 8px
space-3 = 12px
space-4 = 16px
space-5 = 20px
space-6 = 24px
space-8 = 32px
space-10 = 40px
space-12 = 48px
space-16 = 64px
```

Do not create arbitrary feature spacing unless layout constraints require it.

---

## 10. Radius Tokens

```text
radius-sm = 6px
radius-md = 8px
radius-lg = 12px
radius-xl = 16px
```

Usage:

- button/input: sm or md
- cards: md or lg
- dialog: lg
- mobile bottom sheet: lg/xl where visually appropriate

Do not default everything to `radius-xl`.

---

## 11. Shadows

Define at most:

- shadow-xs
- shadow-sm
- shadow-md

Most cards use no shadow.

Use elevation mainly for:

- dropdown
- popover
- dialog
- floating action surface

---

## 12. App Shell

### Sidebar

Expanded: 256px preferred.

Collapsed: 68px preferred.

Contains:

- product mark
- tenant context
- primary nav
- lower utility nav
- user/account area

### Header

Height target: 56–64px.

Contains only relevant context:

- breadcrumb
- page-level context
- global search
- notifications
- company/location selector
- user menu

### Content

Typical:

- desktop padding: 32px
- tablet: 24px
- mobile: 16px

---

## 13. Page Header Component

Required structure:

```text
Breadcrumb optional
Title
Description optional

Secondary controls         Primary action
```

Example:

```text
Routers
Manage hotspot gateways and network health.

[All Locations] [Add Router]
```

On mobile:

- stack title/context
- actions move below
- primary action remains visible

---

## 14. Button Component

Sizes:

- sm: 32px
- md: 36–40px
- lg: 44px

Variants:

### Primary

Use for main action.

### Secondary

Neutral bordered or subtle-filled action.

### Ghost

Low emphasis.

### Destructive

Red semantic styling.

### Link

Inline action.

Required states:

- default
- hover
- focus
- disabled
- loading

Buttons must not change width dramatically when loading.

---

## 15. Input Components

Required:

- Input
- Textarea
- Select
- Combobox
- Checkbox
- Radio
- Switch
- DateRangePicker
- PhoneInput
- MoneyInput

Every field supports:

- label
- optional description
- optional/error text
- disabled
- required marker if used consistently

---

## 16. Search Input

Use compact search where page scope is obvious.

Examples:

- Search customers
- Search payments
- Search routers

Global search may use a command palette pattern.

---

## 17. Status Badge

Shape:

- compact pill or softly rounded rectangle
- small text
- semantic subtle background
- semantic text/icon

Optional dot indicator.

Do not use highly saturated full-fill badges.

---

## 18. Card Component

Base card:

- surface background
- 1px subtle border
- radius-md/lg
- no shadow by default

Variants:

- standard
- interactive
- alert
- KPI

Cards should not become universal layout wrappers.

---

## 19. KPI Card

Structure:

```text
Label
Value
Context / comparison
Optional mini indicator
```

Example:

```text
Revenue Today
TZS 428,500
+12.8% vs yesterday
```

Never put meaningless icons into every KPI.

---

## 20. Metric Formatting

Use:

```text
TZS 428,500
47 users
3.4 GB
18%
8 / 8 online
```

Numbers should be immediately scannable.

---

## 21. Table System

Header:

- subtle background or no fill
- 12–13px medium/semibold labels
- consistent alignment

Rows:

- 44–52px target height
- subtle divider
- hover state
- selected state where applicable

Actions:

- overflow menu
- row link
- occasional explicit primary row action

Numeric values align right where appropriate.

---

## 22. Data Table Toolbar

Typical:

```text
[Search] [Date] [Location] [Status] [More Filters]     [Export]
```

On narrow screens use:

- search
- Filters button
- key contextual action

---

## 23. Filter Drawer/Popover

Advanced filtering should not permanently occupy large vertical space.

Filters may include:

- date range
- location
- router
- status
- plan
- payment provider
- customer type

Display active filters visibly.

---

## 24. Tabs

Use tabs only when views are peers.

Good:

- Router: Overview / Sessions / Configuration / Logs
- Customer: Overview / Payments / Sessions / Devices

Do not use tabs merely to hide poor information architecture.

---

## 25. Dialog

Use for:

- focused small/medium forms
- confirmation
- single-step operations

Avoid enormous forms in modals.

Large workflows should use:

- dedicated page
- side panel
- multi-step wizard

---

## 26. Drawer / Side Panel

Appropriate for:

- filters
- quick detail
- editing small records
- diagnostics detail
- responsive mobile interactions

Do not use a drawer where a full-page workflow is clearer.

---

## 27. Toasts

Use for transient confirmation:

- Plan saved
- Voucher batch generated
- Router sync started

Do not use toast as the only place for critical error details.

---

## 28. Alerts

Use inline alert components for:

- degraded service
- missing payment configuration
- router offline
- onboarding incomplete
- subscription issue

Severity:

- info
- warning
- danger
- success

---

## 29. Skeletons

Skeletons should mirror real content shape.

Use for:

- KPI row
- table rows
- detail header
- chart region

Avoid spinner-only full-page loading when layout is known.

---

## 30. Empty State Component

Structure:

```text
Optional simple icon
Title
Description
Primary action
Optional secondary action
```

Keep illustrations restrained or absent.

---

## 31. Charts

Chart surface:

- minimal gridlines
- clean axis labels
- compact tooltip
- no decorative gradients by default
- no 3D

Chart legends should remain small and readable.

Use accessible labels and accompanying textual metric summaries where needed.

---

## 32. Router Health Indicator

Standard domain component:

```text
ONLINE
DEGRADED
OFFLINE
PROVISIONING
FAILED
```

Must support:

- label
- status dot
- optional last seen context

Never infer ONLINE from stale data.

---

## 33. Payment Status Badge

Supported:

- CREATED
- PENDING
- PAID
- FAILED
- EXPIRED
- CANCELLED
- REFUNDED

`PAID` must be visually distinct from `PENDING`.

---

## 34. Entitlement Status Badge

Supported:

- PENDING
- ACTIVE
- EXHAUSTED
- EXPIRED
- REVOKED
- SUSPENDED

---

## 35. Voucher Status Badge

Supported:

- AVAILABLE
- REDEEMED
- EXPIRED
- REVOKED

---

## 36. Router Resource Card

Use compact resource display:

```text
CPU       18%
Memory    42%
Uptime    18d 4h
Sessions  47
```

Avoid speedometer/gauge components.

---

## 37. Timeline Component

Use for:

- payment lifecycle
- router provisioning
- audit events
- entitlement activity

Example:

```text
21:42 Payment requested
21:43 Payment confirmed
21:43 Entitlement activated
```

---

## 38. Confirmation Pattern

Title + consequence + actions.

Example:

```text
Disconnect user?

This immediately terminates the current internet session.

[Cancel] [Disconnect]
```

Destructive button comes last.

---

## 39. Form Section Pattern

Use:

```text
Section title
Short description

Field
Field

Divider/space

Next section
```

Do not create a card for every field group unless layout benefits.

---

## 40. Responsive Breakpoints

Follow framework defaults where reasonable, but target intentional behavior at:

- mobile: ~390px
- tablet: ~768–1024px
- desktop: 1280–1440px+

Every major screen must be manually inspected at:

- 390px
- 1024px
- 1440px

---

## 41. Mobile Data Row Pattern

Convert complex desktop rows into readable mobile cards/list rows.

Example:

```text
0712 345 678                   ONLINE
Day Pass · Mlimani Cafe
1h 42m connected · 3.2 GB
```

---

## 42. Accessibility Tokens

Focus ring must be visible.

Minimum touch target:

- 40–44px for mobile interactive controls where practical

Color contrast must meet accepted accessibility standards.

---

## 43. Iconography

Use Lucide unless explicitly changed project-wide.

Recommended size:

- 16px inline
- 18–20px buttons/nav
- 20–24px empty state/supporting icon

Do not use large decorative icons without purpose.

---

## 44. Z-Index System

Define fixed layers:

```text
base
sticky
dropdown
popover
overlay
modal
toast
```

Do not create random `z-[9999]` feature fixes.

---

## 46. Light & Dark Mode Requirements

Light and dark mode are both mandatory product modes.

### Light Mode

Must preserve:

- clean neutral background separation
- restrained borders
- readable muted text
- subtle elevation
- professional data density

Avoid excessive pure-white layering that makes all surfaces visually indistinguishable.

### Dark Mode

Must preserve:

- distinct application and surface layers
- readable borders
- restrained contrast
- readable tables
- legible charts
- visible focus states
- semantic status colors without neon saturation

Avoid using pure black for every background and pure white for every text element.

### System Mode

When selected, follow the operating system's theme preference and respond to preference changes.

### Mandatory Testing

Every shared primitive and every major screen must be checked in:

```text
Light desktop
Dark desktop
Light mobile
Dark mobile
```

At minimum, major screens must be reviewed at:

```text
1440px desktop
390px mobile
```

in both modes.

Screens with dense tables should additionally be checked around tablet width.

Do not mark a frontend feature complete if it only looks correct in one theme.

---

## 46. Component Ownership

`components/ui/`

Contains general primitives.

`components/domain/`

Contains reusable business concepts.

Examples:

- RouterStatusBadge
- PaymentStatusBadge
- PlanSummary
- SessionIdentity
- MoneyValue
- DataUsageValue

`features/*/components`

Contains feature-specific compositions.

---

## 47. No Duplicate Components

Before creating a new component, agents must search for an existing primitive/domain component.

Do not create:

- PrimaryButton
- MainButton
- SubmitButton
- BlueButton

as separate styling inventions.

Use the shared `Button`.

---

## 48. Design Token Enforcement

Feature code must not introduce arbitrary raw design values unless the design system cannot represent the need.

If a new token is required:

1. justify it
2. add it centrally
3. document it
4. reuse it

---

## 49. UI Review Checklist

Before merge:

- typography matches system
- spacing matches system
- colors use tokens
- component variants are reused
- loading exists
- empty state exists
- error state exists
- mobile behavior checked
- keyboard/focus checked
- no fake data
- no arbitrary visual flourishes
- domain statuses are exact

---

## 50. Anti-Vibe-Code Rule

If a screen's primary visual interest comes from:

- gradient backgrounds
- giant metric text
- glass cards
- glowing outlines
- decorative illustrations
- excessive motion

rather than hierarchy, data and usability, redesign it.

The system should look expensive because it is coherent, not because the CSS is loud.
