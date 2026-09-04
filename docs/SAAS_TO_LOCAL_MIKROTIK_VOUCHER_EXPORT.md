# SaaS to Local MikroTik RouterOS Voucher Export Bridge

This document describes the transitional batch export mechanism from Usimamizi SaaS to local RouterOS 6 HotSpot routers.

## 1. Export Overview

Until full cloud AAA integration is activated in Phase 3, voucher batches generated in the SaaS platform can be exported directly into local RouterOS script files (`.rsc`).

## 2. Generated RouterOS Commands

Each voucher in the batch is transformed into a RouterOS HotSpot user command:

```routeros
# Usimamizi Wi-Fi — RouterOS Local Hotspot User Export
# Batch: VB-20260827-X8921A | Plan: 1 Hour Pass
# Generated at: 2026-08-27T01:50:00Z
# Total Vouchers: 10
# --------------------------------------------------

/ip hotspot user add name="K7PM-4XQ9" password="K7PM-4XQ9" profile="LAB-1H" comment="Batch: VB-20260827-X8921A"
/ip hotspot user add name="B3RN-992A" password="B3RN-992A" profile="LAB-1H" comment="Batch: VB-20260827-X8921A"
```

## 3. Router Import Command

Operators can import the generated `.rsc` file on the MikroTik terminal:

```routeros
/import file-name=VB-20260827-X8921A.rsc
```
