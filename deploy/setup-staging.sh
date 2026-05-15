#!/bin/bash
# Запустить один раз на сервере для настройки staging-окружения.
# ssh glava "bash /opt/glava/deploy/setup-staging.sh"

set -e

STAGING_DIR=/opt/glava-staging
PROD_ENV=/opt/glava/.env
REPO=https://github.com/NikitaMorgos/glava-bot.git

echo "=== Setting up GLAVA Admin Staging ==="

# 1. Clone repo
if [ -d "$STAGING_DIR" ]; then
  echo "Directory $STAGING_DIR already exists, skipping clone"
else
  git clone "$REPO" "$STAGING_DIR"
fi

cd "$STAGING_DIR"
git fetch origin
git checkout dev
git reset --hard origin/dev

# 2. Virtualenv
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
venv/bin/pip install -r requirements.txt --quiet

# 3. Systemd service
cp "$STAGING_DIR/deploy/glava-admin-staging.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable glava-admin-staging
systemctl restart glava-admin-staging

# 4. Open firewall port (ufw)
if command -v ufw &>/dev/null; then
  ufw allow 5002/tcp
  echo "Port 5002 opened in ufw"
fi

echo ""
echo "=== Done ==="
echo "Staging panel: http://72.56.121.94:5002"
echo "Status: systemctl status glava-admin-staging"
