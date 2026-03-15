#!/bin/bash
# Деплой лендинга glava.family
# Запуск: bash deploy/deploy-landing.sh
set -e

echo "=== Деплой лендинга glava.family ==="

# Создаём папку, если нет
mkdir -p /var/www/glava.family/assets

# Копируем файлы из репо
cp /opt/glava/landing/index.html   /var/www/glava.family/
cp /opt/glava/landing/base.css     /var/www/glava.family/
cp /opt/glava/landing/style.css    /var/www/glava.family/
cp /opt/glava/landing/assets/*     /var/www/glava.family/assets/

# Права
chown -R www-data:www-data /var/www/glava.family

# Nginx конфиг
cp /opt/glava/deploy/nginx-glava.conf /etc/nginx/sites-available/glava.conf
ln -sf /etc/nginx/sites-available/glava.conf /etc/nginx/sites-enabled/glava.conf

nginx -t && systemctl reload nginx

echo "=== Лендинг задеплоен: https://glava.family ==="
