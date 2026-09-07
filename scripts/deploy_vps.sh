#!/usr/bin/env bash
# ==============================================================================
# Usimamizi Wi-Fi Automated VPS Production Deployment Script
# Target Host: Ubuntu 24.04 LTS (Nginx + PostgreSQL 16 + Redis + FreeRADIUS)
# Domain: wifi.swahilicode.tech (IP: 23.95.130.161)
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use: sudo bash deploy_vps.sh)"
    exit 1
fi

APP_DIR="/var/www/usimamizi-wifi"
GIT_REPO="https://github.com/Mrrobottz01/usimamizi-wifi.git"
DOMAIN="wifi.swahilicode.tech"
SERVER_IP="23.95.130.161"
GUNICORN_PORT="8090"
DB_NAME="usimamizi_db"
DB_USER="usimamizi_user"
DB_PASS="Usimamizi_StrongPass_2026!"
ADMIN_EMAIL="admin@swahilicode.tech"

echo "====================================================================="
echo "   Usimamizi Wi-Fi — Production Deployment on ${DOMAIN}"
echo "====================================================================="

# ------------------------------------------------------------------------------
# 1. System Packages & Dependencies
# ------------------------------------------------------------------------------
log_info "Step 1/9: Verifying system packages and dependencies..."
apt-get update -qq

# Install essential build tools & Python packages
apt-get install -y -qq \
    git curl wget ca-certificates gnupg \
    python3 python3-pip python3-venv libpq-dev \
    freeradius freeradius-rest freeradius-utils \
    certbot python3-certbot-nginx

# Check Node.js and npm
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    log_info "Installing Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
fi
log_success "Node.js $(node -v) and npm $(npm -v) ready."

# ------------------------------------------------------------------------------
# 2. Dedicated PostgreSQL Database
# ------------------------------------------------------------------------------
log_info "Step 2/9: Setting up dedicated PostgreSQL database (${DB_NAME})..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_user WHERE usename = '${DB_USER}';" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}';" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" >/dev/null 2>&1 || true
log_success "PostgreSQL database '${DB_NAME}' and user '${DB_USER}' configured."

# ------------------------------------------------------------------------------
# 3. Clone or Update Application Repository
# ------------------------------------------------------------------------------
log_info "Step 3/9: Setting up repository in ${APP_DIR}..."
if [ -d "${APP_DIR}/.git" ]; then
    log_info "Updating existing repository..."
    cd "${APP_DIR}"
    git fetch origin main
    git reset --hard origin/main
else
    log_info "Cloning fresh repository..."
    mkdir -p /var/www
    git clone "${GIT_REPO}" "${APP_DIR}"
fi
cd "${APP_DIR}"
log_success "Repository ready on branch main."

# ------------------------------------------------------------------------------
# 4. Python Virtual Environment & Backend Setup
# ------------------------------------------------------------------------------
log_info "Step 4/9: Configuring Python 3 virtual environment..."
cd "${APP_DIR}/backend"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements/production.txt -q

# Generate .env file if not exists
ENV_FILE="${APP_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
    log_info "Generating production .env configuration..."
    DJANGO_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    cat <<EOF > "${ENV_FILE}"
DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=${DJANGO_SECRET}
ALLOWED_HOSTS=${DOMAIN},127.0.0.1,localhost,${SERVER_IP}

# Database Configuration (PostgreSQL 16)
USE_SQLITE=False
DATABASE_URL=postgres://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}

# Redis & Celery
REDIS_URL=redis://127.0.0.1:6379/4
CELERY_BROKER_URL=redis://127.0.0.1:6379/4

# Router Password Cryptographic Key
ENCRYPTION_MASTER_KEY=${FERNET_KEY}

# Security & CORS
CORS_ALLOWED_ORIGINS=https://${DOMAIN}
CSRF_TRUSTED_ORIGINS=https://${DOMAIN}
EOF
    log_success "Generated new production .env with secure encryption keys."
else
    log_info "Preserving existing .env file."
fi

# Run database migrations and collect static
log_info "Running database migrations..."
python manage.py migrate --noinput
log_info "Collecting static assets..."
python manage.py collectstatic --noinput
log_success "Backend prepared successfully."

# ------------------------------------------------------------------------------
# 5. Build Frontend SPA
# ------------------------------------------------------------------------------
log_info "Step 5/9: Building Vite React frontend..."
cd "${APP_DIR}/frontend"
npm install --legacy-peer-deps -q
npm run build
log_success "Frontend compiled successfully to ${APP_DIR}/frontend/dist."

# ------------------------------------------------------------------------------
# 6. Systemd Services (Gunicorn & Watchdog)
# ------------------------------------------------------------------------------
log_info "Step 6/9: Configuring systemd services..."

cat <<EOF > /etc/systemd/system/usimamizi-gunicorn.service
[Unit]
Description=Usimamizi Wi-Fi Gunicorn WSGI Server
After=network.target postgresql.service redis-server.service

[Service]
User=root
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/backend/.venv/bin/gunicorn \\
    --workers 3 \\
    --bind 127.0.0.1:${GUNICORN_PORT} \\
    --timeout 90 \\
    --access-logfile /var/log/usimamizi-gunicorn.access.log \\
    --error-logfile /var/log/usimamizi-gunicorn.error.log \\
    config.wsgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat <<EOF > /etc/systemd/system/usimamizi-watchdog.service
[Unit]
Description=Usimamizi Wi-Fi System Watchdog
After=network.target usimamizi-gunicorn.service

[Service]
User=root
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/backend/.venv/bin/python manage.py run_system_watchdog --interval 30
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable usimamizi-gunicorn.service
systemctl restart usimamizi-gunicorn.service
systemctl enable usimamizi-watchdog.service
systemctl restart usimamizi-watchdog.service
log_success "Gunicorn (127.0.0.1:${GUNICORN_PORT}) and Watchdog services active."

# ------------------------------------------------------------------------------
# 7. Configure FreeRADIUS with rlm_rest
# ------------------------------------------------------------------------------
log_info "Step 7/9: Configuring FreeRADIUS for Central AAA..."
RADIUS_DIR="/etc/freeradius/3.0"

# Stop FreeRADIUS service temporarily during config update
systemctl stop freeradius 2>/dev/null || true
pkill -9 -x freeradius 2>/dev/null || true

# Deploy REST module configured to port 8090
cp "${APP_DIR}/infrastructure/freeradius/mods-available/rest" "${RADIUS_DIR}/mods-available/rest"
sed -i "s|127.0.0.1:8000|127.0.0.1:${GUNICORN_PORT}|g" "${RADIUS_DIR}/mods-available/rest"
ln -sf "${RADIUS_DIR}/mods-available/rest" "${RADIUS_DIR}/mods-enabled/rest"

# Deploy sites-available/default
cp "${APP_DIR}/infrastructure/freeradius/sites-available/default" "${RADIUS_DIR}/sites-available/default"

# Deploy clients.conf (preserves localhost and sets up dynamic/mikrotik client definitions)
cp -n "${RADIUS_DIR}/clients.conf" "${RADIUS_DIR}/clients.conf.backup" 2>/dev/null || true
cp "${APP_DIR}/infrastructure/freeradius/clients.conf" "${RADIUS_DIR}/clients.conf"

# Test configuration syntax
if freeradius -XC >/tmp/freeradius_check.log 2>&1; then
    systemctl restart freeradius
    log_success "FreeRADIUS configured and listening on UDP 1812/1813."
else
    log_warn "FreeRADIUS syntax check reported issues. Log:"
    tail -n 20 /tmp/freeradius_check.log
fi

# ------------------------------------------------------------------------------
# 8. Nginx Virtual Host Configuration
# ------------------------------------------------------------------------------
log_info "Step 8/9: Configuring Nginx virtual host for ${DOMAIN}..."

NGINX_CONF="/etc/nginx/sites-available/${DOMAIN}"

cat <<EOF > "${NGINX_CONF}"
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    # Frontend React SPA
    root ${APP_DIR}/frontend/dist;
    index index.html;

    client_max_body_size 20M;

    # Django Static Files
    location /static/ {
        alias ${APP_DIR}/backend/staticfiles/;
        expires 30d;
        access_log off;
    }

    # Django Media Files
    location /media/ {
        alias ${APP_DIR}/backend/media/;
        expires 30d;
    }

    # Proxy API and Admin to Gunicorn
    location ~ ^/(api|admin)/ {
        proxy_pass http://127.0.0.1:${GUNICORN_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    # SPA Fallback
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

ln -sf "${NGINX_CONF}" "/etc/nginx/sites-enabled/${DOMAIN}"

# Test Nginx configuration before reloading
if nginx -t >/dev/null 2>&1; then
    systemctl reload nginx
    log_success "Nginx virtual host enabled and reloaded."
else
    log_error "Nginx configuration syntax check failed! Check 'nginx -t'."
fi

# ------------------------------------------------------------------------------
# 9. Let's Encrypt SSL Certificate
# ------------------------------------------------------------------------------
log_info "Step 9/9: Requesting Let's Encrypt SSL certificate for ${DOMAIN}..."
if certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "${ADMIN_EMAIL}" --redirect; then
    log_success "SSL certificate successfully installed and HTTPS active!"
else
    log_warn "Certbot automatic issuance skipped or requires DNS check."
    log_warn "Run manually when DNS propagation finishes: certbot --nginx -d ${DOMAIN}"
fi

echo "====================================================================="
echo -e "${GREEN}>>> DEPLOYMENT COMPLETED SUCCESSFULLY! <<<${NC}"
echo "Dashboard & Captive Portal: https://${DOMAIN}"
echo "API Endpoint:               https://${DOMAIN}/api/v1/"
echo "Admin Portal:               https://${DOMAIN}/admin/"
echo "FreeRADIUS UDP Ports:       1812 (Auth), 1813 (Acct)"
echo "Gunicorn Internal Port:     127.0.0.1:${GUNICORN_PORT}"
echo "====================================================================="
