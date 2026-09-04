# MikroTik Lab Hardware & RouterOS Baseline

**Target Router:** MikroTik hAP ac lite  
**Architecture:** `mipsbe`  
**RouterOS Version:** `6.49.19 long-term`  
**Default Management IP:** `192.168.88.1`  
**Document Purpose:** Baseline capture instructions prior to Phase 1 HotSpot lab configuration.

---

## 1. Baseline Capture Instructions

> [!IMPORTANT]
> **HUMAN EXECUTION REQUIRED**  
> Open WinBox or SSH (`ssh admin@192.168.88.1`) and execute the following commands to record the baseline state of the router.

### System & Resource Baseline
```routeros
/system resource print
/system package print
/system identity print
```

### Network Interfaces & Bridges Baseline
```routeros
/interface print detail
/interface bridge print detail
/interface bridge port print detail
/interface wireless print detail
```

### IP & Routing Baseline
```routeros
/ip address print detail
/ip dhcp-client print detail
/ip dhcp-server print detail
/ip pool print detail
/ip dns print
/ip route print detail
```

### Firewall & Services Baseline
```routeros
/ip firewall nat print detail
/ip firewall filter print detail
/ip service print
```

### Hotspot Baseline (Clean Check)
```routeros
/ip hotspot print detail
/ip hotspot profile print detail
/ip hotspot user print detail
/ip hotspot user profile print detail
```

---

## 2. Safe Baseline Backup & Export Commands

Execute the following commands to create safe backup files before making configuration changes:

```routeros
# Export clean configuration excluding sensitive keys
/export hide-sensitive file=phase1-baseline

# Save complete binary system backup
/system backup save name=phase1-baseline
```

> [!WARNING]
> Never commit exports containing live Wi-Fi passwords, ISP credentials, or administrative secrets to public source control.

---

## 3. Rollback Instructions

If it becomes necessary to revert the router back to its original baseline state during testing:

```routeros
# Restore binary backup
/system backup load name=phase1-baseline.backup

# Reboot router to apply restored baseline
/system reboot
```
