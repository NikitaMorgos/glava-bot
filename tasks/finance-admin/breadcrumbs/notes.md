# Finance Admin — заметки

## 2026-03-17

- Раздел доступен dev/dasha/lena — нового пользователя не создаём.
- Данные в отдельных таблицах `expense_*`, не смешиваем с `prompts`.
- Категория и инициатор — справочники с защитой от удаления, если есть расходы.
- P&L: выручка пока заглушка (0), будет подтянута из `drafts.status='paid'` в этапе 2.
- Initiator по умолчанию в форме = текущий username сессии.
- Суммы хранятся как NUMERIC(12,2), выводятся в рублях с пробелами-разделителями тысяч.

## 2026-03-17 — Деплой

- `git push` → `git reset --hard FETCH_HEAD` на сервере (из-за untracked файлов `git pull` падал с Aborting).
- `python scripts/migrate_finance.py` — таблицы созданы, категории и инициаторы добавлены.
- **Проблема:** после `systemctl restart glava-admin` gunicorn стартовал, но воркер не поднимался (нет строки `Booting worker with pid`). Curl на 127.0.0.1:5001 висел без ответа.
- Диагностика: запуск gunicorn вручную на порту 5003 → `[Errno 98] Address already in use` — порт удерживал старый фоновый gunicorn-процесс от тестов.
- **Решение:** `pkill -f gunicorn` → `systemctl restart glava-admin` → curl вернул `302` → браузер открылся.
- Итог: https://admin.glava.family → все роли видят раздел «Финансы» ✅

## 2026-03-17 — Доработки после запуска

- Добавлены столбцы `periodicity` (разовая/подписка) и `behavior` (постоянная/переменная) — ALTER TABLE через migrate_finance.py.
- Добавлен столбец `title` (название, свободный ввод).
- Форма добавления расхода переверстана в одну строку (flex-wrap), справочники категорий и инициаторов перенесены вниз страницы (grid 2 колонки).
- Gunicorn service: `--worker-tmp-dir /dev/shm` убран — вызывал незапуск воркера. Добавлены `--timeout 30 --log-level debug --capture-output`, `KillMode=mixed`, `TimeoutStopSec=10`, `RestartSec=3`.
- Все роли (dev/dasha/lena) получили доступ ко всем разделам: blueprints dev/dasha/lena обновлены, сайдбар стал единым без ролевых условий.
