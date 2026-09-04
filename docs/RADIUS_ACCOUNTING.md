# RADIUS Accounting & Usage Tracking Specification

Detailed explanation of cumulative delta calculations, gigawords 64-bit math, idempotency, and session lifecycle in **Usimamizi Wi-Fi** (Phase 4).

---

## 1. Cumulative Delta Accounting Model

In RADIUS accounting, `Acct-Input-Octets` and `Acct-Output-Octets` represent **cumulative** counters for the entire duration of the session:

$$\text{total\_input\_bytes} = (\text{input\_gigawords} \times 2^{32}) + \text{input\_octets}$$
$$\text{total\_output\_bytes} = (\text{output\_gigawords} \times 2^{32}) + \text{output\_octets}$$
$$\text{total\_bytes} = \text{total\_input\_bytes} + \text{total\_output\_bytes}$$

### Delta Calculation Rule
When an `Interim-Update` or `Stop` packet arrives:
$$\Delta_{\text{bytes}} = \max(0, \text{total\_bytes} - (\text{session.input\_bytes} + \text{session.output\_bytes}))$$
$$\Delta_{\text{seconds}} = \max(0, \text{session\_time} - \text{session.session\_seconds})$$

Only strictly positive deltas are added to the entitlement:
- `entitlement.data_used_bytes += delta_bytes`
- `entitlement.usage_time_used_seconds += delta_seconds`

---

## 2. Robustness Invariants

1. **Duplicate Packet Idempotency:** Duplicate `Start`, `Interim`, or `Stop` packets produce $\Delta = 0$, preventing double-billing or metric inflation.
2. **Out-of-Order Packet Protection:** Late-arriving packets with smaller counters produce $\Delta = 0$ and do not decrement existing high-water marks.
3. **Missing Start Resilience:** If an `Interim` or `Stop` packet arrives without a prior `Start`, a `HotspotSession` record is automatically initialized and updated.
4. **Gigawords Support:** $2^{32}$ roll-overs (4 GB threshold) are handled smoothly without 32-bit integer overflow.
