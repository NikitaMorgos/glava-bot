#!/bin/bash
# deploy.sh — деплой лендинга glava.family на VPS
# Запускать с локального ПК из корня проекта GLAVA/
# Согласовать переменные с Агентом А перед использованием

set -e

SERVER="root@glava.family"        # или IP VPS
REMOTE_DIR="/opt/glava/landing"   # уточнить у Агента А
LOCAL_DIR="./landing/"

echo "==> Синхронизация лендинга на сервер..."
rsync -avz --delete \
  --exclude=".DS_Store" \
  --exclude="*.md" \
  "$LOCAL_DIR" "$SERVER:$REMOTE_DIR"

echo "==> Перезагрузка Nginx..."
ssh "$SERVER" "systemctl reload nginx"

echo "==> Проверка..."
ssh "$SERVER" "systemctl status nginx --no-pager -l | head -5"

echo ""
echo "✅ Деплой завершён. Проверь: https://glava.family/"
echo "   curl -I https://glava.family/"
