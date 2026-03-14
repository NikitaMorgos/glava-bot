#!/bin/bash
# Установка и обновление GLAVA-бота на Ubuntu/Debian VPS.
# Первый запуск: задай REPO_URL=https://github.com/ВАШ_РЕПОЗИТОРИЙ.git
# Обновление (если git уже есть): ./deploy.sh

set -e

APP_DIR=/opt/glava
# REPO_URL должен быть задан при первой установке через git clone.
# Пример: REPO_URL=https://github.com/owner/GLAVA.git bash deploy.sh
REPO_URL="${REPO_URL:-}"

echo "=== GLAVA: установка/обновление на VPS ==="

# 1. Системные зависимости
echo "[1/7] Установка системных пакетов..."
sudo apt-get update -q
sudo apt-get install -y python3 python3-venv python3-pip git ffmpeg

# 2. Папка приложения
echo "[2/7] Создание папки..."
sudo mkdir -p "$APP_DIR"

# 3. Клонирование/копирование кода
echo "[3/7] Развёртывание кода..."
if [ -d "$APP_DIR/.git" ]; then
    echo "  git pull (репозиторий уже есть)..."
    (cd "$APP_DIR" && git pull)
elif [ -n "$REPO_URL" ]; then
    echo "  git clone $REPO_URL → $APP_DIR ..."
    sudo git clone "$REPO_URL" "$APP_DIR"
else
    echo ""
    echo "ОШИБКА: $APP_DIR не является git-репозиторием и REPO_URL не задан."
    echo "Варианты:"
    echo "  а) REPO_URL=https://github.com/owner/GLAVA.git bash deploy.sh"
    echo "  б) Скопируй проект вручную, затем повтори:"
    echo "     rsync -avz --exclude=venv --exclude='__pycache__' --exclude='.git' \\"
    echo "       ./GLAVA/ root@SERVER_IP:/opt/glava/"
    echo "     После чего снова запусти deploy.sh"
    exit 1
fi

# 4. Виртуальное окружение и зависимости
echo "[4/7] Установка Python-зависимостей..."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# 5. .env
echo "[5/7] Настройка .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "ВАЖНО: отредактируй $APP_DIR/.env и заполни BOT_TOKEN, DATABASE_URL, S3-ключи"
    echo "  nano $APP_DIR/.env"
else
    echo "  .env уже существует — пропускаю"
fi

# 6. systemd (бот)
# Всегда копируем эталонный .service из репозитория, чтобы не было расхождений.
echo "[6/7] Установка/обновление systemd-сервиса бота..."
sudo cp "$APP_DIR/deploy/glava.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable glava
# restart (а не start) — перезапускает даже уже работающий сервис с новым кодом.
sudo systemctl restart glava

# 7. Личный кабинет
echo "[7/7] Установка/обновление кабинета..."
sudo cp "$APP_DIR/deploy/glava-cabinet.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable glava-cabinet
sudo systemctl restart glava-cabinet 2>/dev/null || true

echo ""
echo "=== Готово ==="
echo "Бот:     systemctl status glava"
echo "Кабинет: systemctl status glava-cabinet"
echo "Логи:    journalctl -u glava -f"
echo ""
echo "Если только что установлено — не забудь заполнить $APP_DIR/.env"
echo "Кабинет: добавь CABINET_SECRET_KEY и TRUST_PROXY=1 в .env, затем:"
echo "  systemctl restart glava-cabinet"
echo "Nginx + SSL: см. DEPLOY_24_7.md"
