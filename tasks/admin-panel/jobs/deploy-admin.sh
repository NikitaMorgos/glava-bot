#!/bin/bash
# Деплой Admin Panel + n8n на сервер.
# Запускать на СЕРВЕРЕ в папке /opt/glava после git pull.
set -e

echo "=== GLAVA Admin: деплой ==="

# 1. Зависимости Python для admin-панели
echo "[1] Установка Python-зависимостей..."
/opt/glava/venv/bin/pip install --quiet psycopg2-binary boto3 requests gunicorn

# 2. Docker (если не установлен)
if ! command -v docker &> /dev/null; then
    echo "[2] Установка Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[2] Docker уже установлен: $(docker --version)"
fi

# 3. n8n через Docker Compose
echo "[3] Запуск n8n..."
mkdir -p /opt/glava/n8n-data
cd /opt/glava
docker compose -f docker/docker-compose.yml up -d
echo "  n8n запущен на http://localhost:5678"

# 4. systemd: Admin Panel
echo "[4] Регистрация admin-сервиса..."
cp /opt/glava/deploy/glava-admin.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable glava-admin
systemctl restart glava-admin
echo "  admin-panel запущен на http://127.0.0.1:5001"

# 5. Nginx
echo "[5] Настройка Nginx..."
cp /opt/glava/deploy/nginx-admin.conf /etc/nginx/sites-available/glava-admin
ln -sf /etc/nginx/sites-available/glava-admin /etc/nginx/sites-enabled/glava-admin 2>/dev/null || true
nginx -t && systemctl reload nginx

# 6. SSL
echo "[6] Получение SSL для admin.glava.family..."
echo "  ВАЖНО: убедись что A-запись admin.glava.family → 72.56.121.94 уже добавлена в DNS"
echo "  Запусти вручную: certbot --nginx -d admin.glava.family"

# 7. Миграция БД
echo "[7] Миграция БД..."
/opt/glava/venv/bin/python /opt/glava/scripts/migrate_admin.py

echo ""
echo "=== Готово ==="
echo "Admin Panel: https://admin.glava.family (после SSL)"
echo "n8n:         http://localhost:5678 (только SSH-туннель)"
echo ""
echo "Логи admin:  journalctl -u glava-admin -f"
echo "Логи n8n:    docker logs -f glava-n8n"
