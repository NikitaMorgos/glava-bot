#!/bin/bash
# Запуск миграции БД для промо-кодов
# Запуск: bash task-promo-codes/jobs/migrate.sh

SERVER=root@72.56.121.94
GLAVA=/opt/glava

echo "==> Запуск миграции..."
ssh $SERVER "cd $GLAVA && source .venv/bin/activate && python scripts/migrate_promo.py"
echo "==> Готово"
