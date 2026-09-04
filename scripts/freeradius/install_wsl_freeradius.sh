#!/usr/bin/env bash
# ==============================================================================
# FreeRADIUS 3.2.8 WSL Lab Deployment Script — Usimamizi Wi-Fi
# ==============================================================================
# Automates installation of dependencies, backup of stock configs, deployment of
# project AAA REST modules and virtual servers, validation, and service reload.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RADIUS_CONFIG_DIR="/etc/freeradius/3.0"

echo "==> [1/6] Checking root privileges..."
if [[ $EUID -ne 0 ]]; then
   echo "Error: This script must be run as root (e.g. sudo bash install_wsl_freeradius.sh)" >&2
   exit 1
fi

echo "==> [2/6] Verifying FreeRADIUS & REST module packages..."
apt-get update -qq
apt-get install -y -qq freeradius freeradius-rest freeradius-utils

echo "==> [3/6] Backing up original FreeRADIUS configurations..."
for file in clients.conf sites-available/default mods-available/rest; do
    if [[ -f "${RADIUS_CONFIG_DIR}/${file}" && ! -f "${RADIUS_CONFIG_DIR}/${file}.orig" ]]; then
        cp "${RADIUS_CONFIG_DIR}/${file}" "${RADIUS_CONFIG_DIR}/${file}.orig"
        echo "    Backed up ${file} -> ${file}.orig"
    fi
done

echo "==> [4/6] Deploying project FreeRADIUS configuration files..."
cp "${PROJECT_ROOT}/infrastructure/freeradius/mods-available/rest" "${RADIUS_CONFIG_DIR}/mods-available/rest"
ln -sf ../mods-available/rest "${RADIUS_CONFIG_DIR}/mods-enabled/rest"

cp "${PROJECT_ROOT}/infrastructure/freeradius/sites-available/default" "${RADIUS_CONFIG_DIR}/sites-available/default"
ln -sf ../sites-available/default "${RADIUS_CONFIG_DIR}/sites-enabled/default"

cp "${PROJECT_ROOT}/infrastructure/freeradius/clients.conf" "${RADIUS_CONFIG_DIR}/clients.conf"

# Ensure proper permissions
chown -R freerad:freerad "${RADIUS_CONFIG_DIR}"

echo "==> [5/6] Validating FreeRADIUS configuration syntax..."
freeradius -XC

echo "==> [6/6] Restarting FreeRADIUS service..."
# Stop and kill any orphan foreground/debug freeradius processes
systemctl stop freeradius 2>/dev/null || true
pkill -9 -x freeradius 2>/dev/null || true
sleep 1
systemctl restart freeradius

echo "==> [SUCCESS] FreeRADIUS 3.2.8 Central AAA is active and listening on UDP 1812/1813!"
systemctl status freeradius --no-pager | head -n 12
