from typing import List, Optional

from django.db import models, transaction

from apps.companies.models import Company, HotspotConfiguration
from apps.payments.models import (
    HotspotWalledGardenEntry,
    WalledGardenEntryType,
    WalledGardenPurpose,
)

PRESET_SNIPPE_PAYMENTS = [
    {"host": "api.snippe.sh", "description": "Snippe API gateway", "purpose": WalledGardenPurpose.PAYMENT},
    {"host": "snippe.sh", "description": "Snippe root domain", "purpose": WalledGardenPurpose.PAYMENT},
    {"host": "snippe.me", "description": "Snippe shortlink and checkout domain", "purpose": WalledGardenPurpose.PAYMENT},
]

PRESET_USIMAMIZI_PORTAL = [
    {"address": "10.5.50.1", "description": "HotSpot Gateway Router", "purpose": WalledGardenPurpose.PORTAL, "entry_type": WalledGardenEntryType.IP},
    {"address": "10.5.50.254", "description": "Usimamizi Server Lab Host", "purpose": WalledGardenPurpose.PORTAL, "entry_type": WalledGardenEntryType.IP},
]


@transaction.atomic
def apply_walled_garden_preset(
    *,
    company: Company,
    hotspot: Optional[HotspotConfiguration],
    preset_name: str
) -> List[HotspotWalledGardenEntry]:
    """
    Apply standard 1-click allowlist presets to prevent human typos in RouterOS hostnames.
    """
    created_entries: List[HotspotWalledGardenEntry] = []
    preset_lower = preset_name.lower()

    if 'snippe' in preset_lower or 'payment' in preset_lower:
        for item in PRESET_SNIPPE_PAYMENTS:
            entry, _ = HotspotWalledGardenEntry.objects.get_or_create(
                company=company,
                hotspot=hotspot,
                host=item["host"],
                entry_type=WalledGardenEntryType.DOMAIN,
                defaults={
                    "purpose": item["purpose"],
                    "description": item["description"],
                    "is_active": True
                }
            )
            created_entries.append(entry)

    if 'portal' in preset_lower or 'usimamizi' in preset_lower:
        for item in PRESET_USIMAMIZI_PORTAL:
            entry, _ = HotspotWalledGardenEntry.objects.get_or_create(
                company=company,
                hotspot=hotspot,
                address=item["address"],
                entry_type=item["entry_type"],
                defaults={
                    "purpose": item["purpose"],
                    "description": item["description"],
                    "is_active": True
                }
            )
            created_entries.append(entry)

    return created_entries


def generate_routeros_walled_garden_script(
    company: Company,
    hotspot: Optional[HotspotConfiguration] = None
) -> str:
    """
    Generate clean RouterOS 6 & 7 compatible commands to synchronize walled garden rules.
    """
    qs = HotspotWalledGardenEntry.objects.filter(company=company, is_active=True)
    if hotspot:
        qs = qs.filter(models.Q(hotspot=hotspot) | models.Q(hotspot__isnull=True))

    lines = [
        "# ========================================================",
        "# Usimamizi Wi-Fi - MikroTik HotSpot Walled Garden Sync",
        f"# Company: {company.name}",
        "# Generated automatically by Usimamizi SaaS",
        "# ========================================================",
        "",
        "# --- Domain Walled Garden (HTTP/HTTPS Host Redirection Bypass) ---"
    ]

    domain_entries = qs.filter(entry_type=WalledGardenEntryType.DOMAIN)
    for entry in domain_entries:
        comment = f"Usimamizi: {entry.description or entry.purpose}"
        lines.append(f'/ip hotspot walled-garden add dst-host="{entry.host}" comment="{comment}"')

    lines.extend([
        "",
        "# --- IP/CIDR Walled Garden (L3 Bypass for Portal / DNS / Auth Servers) ---"
    ])

    ip_entries = qs.filter(entry_type__in=[WalledGardenEntryType.IP, WalledGardenEntryType.CIDR])
    for entry in ip_entries:
        comment = f"Usimamizi: {entry.description or entry.purpose}"
        lines.append(f'/ip hotspot walled-garden ip add dst-address="{entry.address}" action=accept comment="{comment}"')

    lines.append("")
    return "\n".join(lines)
