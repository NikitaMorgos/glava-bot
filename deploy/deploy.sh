#!/bin/bash
# Установка GLAVA-бота на Ubuntu/Debian VPS для работы 24/7

set -e

APP_DIR=/opt/glava
REPO_URL="${REPO_URL:-https://github.com/YOUR_USER/GLAVA.git}"

echo "=== GLAVA: установка на VPS ==="

# 1. Системные зависимости
echo "[1/6] Установка системных пакетов..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git ffmpeg

# 2. Папка приложения
echo "[2/6] Создание папки..."
sudo mkdir -p "$APP_DIR"

# 3. Клонирование/копирование кода
echo "[3/6] Развёртывание кода..."
if [ -d "$APP_DIR/.git" ]; then
    (cd "$APP_DIR" && git pull)
elif [ -n "$REPO_URL" ] && [[ "$REPO_URL" == http* ]]; then
    sudo git clone "$REPO_URL" "$APP_DIR"
else
    echo "Скопируй проект в $APP_DIR вручную:"
    echo "  scp -r ./GLAVA root@SERVER_IP:/opt/glava"
    echo "  или git clone <REPO> $APP_DIR"
    read -p "Нажми Enter после копирования..."
fi

# 4. Виртуальное окружение и зависимости
echo "[4/6] Установка Python-зависимостей..."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 5. .env
echo "[5/6] Настройка .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "ВАЖНО: отредактируй $APP_DIR/.env и заполни BOT_TOKEN, DATABASE_URL, S3-ключи"
    echo "  nano $APP_DIR/.env"
else
    echo ".env уже существует"
fi

# 6. systemd
echo "[6/6] Установка systemd-сервиса..."
sudo cp "$APP_DIR/deploy/glava.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable glava
sudo systemctl start glava

echo ""
echo "=== Готово ==="
echo "Бот запущен: systemctl status glava"
echo "Логи: journalctl -u glava -f"
