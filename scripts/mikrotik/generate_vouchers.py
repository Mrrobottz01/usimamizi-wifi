#!/usr/bin/env python3
"""
Local Lab Voucher Generator Tool for MikroTik Hotspot.
Generates human-readable voucher codes and produces RouterOS import scripts & CSV files.
"""

import argparse
import csv
import secrets
import string
from datetime import datetime
from pathlib import Path

# Safe character set omitting ambiguous characters (0, O, 1, I, L)
SAFE_CHARS = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


def generate_single_voucher_code(group_length: int = 4, groups: int = 2) -> str:
    """
    Generate a random human-readable voucher code (e.g. K7PM-4XQ9).
    """
    parts = []
    for _ in range(groups):
        part = "".join(secrets.choice(SAFE_CHARS) for _ in range(group_length))
        parts.append(part)
    return "-".join(parts)


def generate_voucher_batch(count: int, profile: str, batch_ref: str = None) -> list:
    """
    Generate a list of unique voucher objects.
    """
    if not batch_ref:
        batch_ref = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M')}"

    vouchers = []
    seen_codes = set()

    while len(vouchers) < count:
        code = generate_single_voucher_code()
        if code not in seen_codes:
            seen_codes.add(code)
            vouchers.append({
                "code": code,
                "username": code,
                "password": code,
                "profile": profile,
                "batch_ref": batch_ref,
                "created_at": datetime.now().isoformat(),
            })

    return vouchers


def save_vouchers_csv(vouchers: list, output_filepath: Path):
    """
    Save voucher data to a CSV file.
    """
    fieldnames = ["code", "username", "password", "profile", "batch_ref", "created_at"]
    with open(output_filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(vouchers)


def save_routeros_script(vouchers: list, output_filepath: Path):
    """
    Save RouterOS import commands (.rsc script).
    """
    lines = [
        "# RouterOS Local Hotspot User Import Script",
        f"# Generated at: {datetime.now().isoformat()}",
        f"# Total Vouchers: {len(vouchers)}",
        "# --------------------------------------------------",
        "",
    ]
    for v in vouchers:
        cmd = (
            f'/ip hotspot user add name="{v["username"]}" password="{v["password"]}" '
            f'profile="{v["profile"]}" comment="Batch: {v["batch_ref"]}"'
        )
        lines.append(cmd)

    lines.append("")
    with open(output_filepath, mode="w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="Generate local RouterOS Hotspot lab vouchers.")
    parser.add_argument(
        "--profile",
        type=str,
        default="LAB-15MIN",
        choices=["LAB-15MIN", "LAB-1H", "LAB-DAY"],
        help="Target Hotspot user profile",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="Number of vouchers to generate",
    )
    parser.add_argument(
        "--batch",
        type=str,
        default=None,
        help="Batch reference string (optional)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="scripts/mikrotik/output",
        help="Output directory for generated CSV and RSC files",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vouchers = generate_voucher_batch(count=args.count, profile=args.profile, batch_ref=args.batch)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = output_dir / f"vouchers_{args.profile}_{timestamp}.csv"
    rsc_file = output_dir / f"vouchers_{args.profile}_{timestamp}.rsc"

    save_vouchers_csv(vouchers, csv_file)
    save_routeros_script(vouchers, rsc_file)

    print(f"Successfully generated {len(vouchers)} vouchers for profile '{args.profile}'.")
    print(f"  CSV file: {csv_file}")
    print(f"  RouterOS Script: {rsc_file}")


if __name__ == "__main__":
    main()
