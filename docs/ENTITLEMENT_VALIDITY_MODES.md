# Entitlement Validity Modes Specification

Detailed explanation of validity calculation modes and arithmetic rules implemented in **Usimamizi Wi-Fi** (Phase 3).

---

## 1. Validity Modes

### A. CONTINUOUS (Clock Time)
- **Concept:** Continuous wall-clock duration from activation time.
- **Formula:**
  $$\text{expires\_at} = \text{activated\_at} + \Delta(\text{duration\_value}, \text{duration\_unit})$$
- **Example:**
  - Plan: 24 Hours Continuous
  - Activated: `30 Aug 10:00`
  - Expires: `31 Aug 10:00`
- **Suspension Behavior:** The wall-clock timer **continues** running during suspension. Suspension blocks access immediately but does not grant hidden commercial validity extensions.

---

### B. CALENDAR (Fixed Boundary)
- **Concept:** Expiration aligns with physical calendar boundaries (e.g. End of Day, End of Month).
- **Daily Rules:**
  $$\text{expires\_at} = (\text{activated\_at} + N \text{ days})\text{ with hour=23:59:59.999999}$$
- **Monthly Arithmetic:**
  - Safely handles varying month lengths using `calendar.monthrange(year, month)`:
  - Example: `Jan 31 + 1 Month` $\rightarrow$ `Feb 28` (or `Feb 29` on leap years).
- **Timezone Awareness:** Calculations use timezone-aware datetime objects (`UTC` canonical storage).

---

### C. USAGE_TIME (Active Consumption)
- **Concept:** Duration represents the cumulative duration of active network sessions.
- **Field Representation:**
  - `usage_time_limit_seconds = duration_value * unit_in_seconds`
  - `usage_time_used_seconds = 0` (incremented by future RADIUS accounting in Phase 4/5)
- **Example:**
  - Plan: 5 Hours Usage Time
  - Session 1: 1 hour $\rightarrow$ `usage_time_used_seconds = 3600`
  - Session 2: 30 mins $\rightarrow$ `usage_time_used_seconds = 5400`
  - Remaining: `12600 seconds (3h 30m)`.
- **Exhaustion Trigger:**
  $$\text{usage\_time\_used\_seconds} \ge \text{usage\_time\_limit\_seconds} \implies \text{USAGE\_TIME\_EXHAUSTED}$$
