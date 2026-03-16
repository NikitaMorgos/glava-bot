#!/bin/bash
# Тест meeting_bot — запись онлайн-созвона
# Использование: ./run_test.sh "https://telemost.yandex.ru/j/xxx" [60]

set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true

URL="${1:?URL встречи обязателен}"
DUR="${2:-60}"

echo "URL: $URL"
echo "Длительность: $DUR сек"
python scripts/run_meeting_bot_test.py "$URL" "$DUR"
