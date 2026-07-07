#!/bin/bash
# VPS install script — isolated from getclover (port 80/3000)
set -euo pipefail

APP_DIR="/opt/map-scraper"
REPO="https://github.com/smarthashmi/Google-Map-Scrapper-Web-Based-with-Python.git"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "  Map Scraper VPS Install"
echo "  Isolated: port 8080 (nginx) -> 5050 (app)"
echo "  getclover untouched: port 80 -> 3000"
echo "=========================================="

# System packages
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip nginx curl

# Clone or update app
if [ -d "$APP_DIR/.git" ]; then
    echo "[install] Updating existing repo..."
    cd "$APP_DIR"
    git pull origin main
else
    echo "[install] Cloning repository..."
    rm -rf "$APP_DIR"
    git clone "$REPO" "$APP_DIR"
    cd "$APP_DIR"
fi

# Python virtual environment
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
source "$APP_DIR/venv/bin/activate"
pip install -q --upgrade pip
pip install -q -r requirements.txt
# Pin for older VPS CPUs (QEMU without x86-v2)
pip install -q "numpy==1.26.4" "pandas==2.2.3"

# Playwright Chromium (lighter than Chrome on Linux)
python -m playwright install chromium
python -m playwright install-deps chromium

# Data directory
mkdir -p "$APP_DIR/data"

# Systemd service
cp "$SCRIPT_DIR/map-scraper.service" /etc/systemd/system/map-scraper.service
systemctl daemon-reload
systemctl enable map-scraper

# Nginx site (port 8080 — does NOT touch getclover on port 80)
cp "$SCRIPT_DIR/nginx-map-scraper.conf" /etc/nginx/sites-available/map-scraper
ln -sf /etc/nginx/sites-available/map-scraper /etc/nginx/sites-enabled/map-scraper
nginx -t
systemctl reload nginx

# Firewall (if ufw active)
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    ufw allow 8080/tcp comment 'Map Scraper' || true
fi

# Start app
systemctl restart map-scraper
sleep 3

echo ""
echo "=========================================="
echo "  Deployment complete!"
echo "  URL: http://198.177.123.152:8080"
echo "  getclover: http://198.177.123.152 (unchanged)"
echo "=========================================="
systemctl status map-scraper --no-pager -l | head -15
echo ""
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:5050/ || true
curl -s -o /dev/null -w "HTTP %{http_code} (via nginx :8080)\n" http://127.0.0.1:8080/ || true
