# Plan Snapshot Strategy

This document outlines how plan changes affect existing active vouchers and historical sessions.

## Principles

1. **Immature/Active Entitlement Immutability:** When a commercial plan's price, bandwidth, or duration is updated, existing generated vouchers and active sessions retain their original plan snapshot parameters.
2. **Historical Integrity:** Modifying a plan's price does not alter revenue reports for previously redeemed vouchers.
3. **Deactivation Policy:** Deactivating a plan prevents creation of new voucher batches using that plan code, while existing un-redeemed vouchers remain valid until their expiration date.
