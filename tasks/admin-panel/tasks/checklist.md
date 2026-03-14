# Admin Panel + n8n — чеклист

## Этап 1: Инфраструктура

- [ ] Установить Docker + Docker Compose на VPS
- [ ] Создать `docker-compose.yml` для n8n (с volume для данных)
- [ ] Запустить n8n, проверить доступность на :5678
- [ ] Создать `admin/app.py` — Flask-приложение на порту 5001
- [ ] Создать `deploy/glava-admin.service` — systemd для admin Flask
- [ ] Добавить в Nginx: admin.glava.family → 127.0.0.1:5001
- [ ] Получить SSL: `certbot --nginx -d admin.glava.family`
- [ ] Авторизация: 3 учётки (dev/dasha/lena), bcrypt, role-based

## Этап 2: БД

- [ ] Таблица `prompts` (role, version, prompt_text, updated_at, updated_by)
- [ ] Таблица `pipeline_jobs` (id, telegram_id, phase, step, status, started_at, finished_at, error)
- [ ] Таблица `mailings` (id, name, template_text, segment, scheduled_at, sent_at, sent_count, created_by)
- [ ] Таблица `mailing_recipients` (mailing_id, telegram_id, status, sent_at)
- [ ] Наполнить `prompts` промптами 12 агентов

## Этап 3: Дашборд разработчика (/dev/)

- [ ] Виджет: статус сервисов (glava, glava-cabinet, n8n)
- [ ] Виджет: метрики БД (users, drafts, voices, photos)
- [ ] Виджет: метрики S3 (объекты, размер)
- [ ] Виджет: статистика бота (сообщений/день, активных)
- [ ] Виджет: n8n — запуски пайплайна сегодня / успех / ошибки
- [ ] Виджет: последние ошибки (journalctl ERROR, последние 20 строк)
- [ ] Виджет: git — текущий коммит + дата деплоя
- [ ] Виджет: конфиг-чеклист (какие ключи заданы)
- [ ] Кнопки управления: Restart Bot / Cabinet / n8n

## Этап 4: Панель Даши (/dasha/)

- [ ] Страница: список промптов агентов (12 ролей)
- [ ] Страница: редактор промпта с историей версий
- [ ] Страница: список заказов (клиент / этап / дата)
- [ ] Страница: детали заказа + управление пайплайном
- [ ] API: POST /dasha/pipeline/start (→ n8n webhook)
- [ ] API: POST /dasha/pipeline/restart-step
- [ ] Страница: уточняющие вопросы по клиенту
- [ ] Страница: отчёт (книг в работе / готово / среднее время)

## Этап 5: n8n Phase A

- [ ] Workflow: Phase A (все 12 нод)
- [ ] Нода 01: Transcriber (HTTP → AssemblyAI/SpeechKit)
- [ ] Нода 02: Fact Extractor (OpenAI, JSON output)
- [ ] Нода 03: Ghostwriter (OpenAI, читает промпт из БД)
- [ ] Нода 04: Fact Checker (OpenAI, loop ≤3)
- [ ] Нода 05: Literary Editor (OpenAI, loop ≤2)
- [ ] Нода 06: Proofreader (OpenAI)
- [ ] Нода 07: Photo Editor (параллельная ветка)
- [ ] Нода 08: Layout Designer (→ typesetter.py → PDF)
- [ ] Нода 09: Layout QA (OpenAI, loop ≤3)
- [ ] Нода 10: Producer (финальный gate, → webhook бота)
- [ ] Нода 11: Interview Architect (параллельная ветка)
- [ ] Webhook: trigger из бота после оплаты
- [ ] Webhook: callback в бот когда книга готова

## Этап 6: n8n Phase B

- [ ] Workflow: Triage Agent (классификация вводной → 6 маршрутов)
- [ ] Маршрут ①: Фактическая поправка
- [ ] Маршрут ②: Стилевой комментарий
- [ ] Маршрут ③: Дополнение текстом
- [ ] Маршрут ④: Новое аудио
- [ ] Маршрут ⑤: Новые фото
- [ ] Маршрут ⑥: Структурная правка

## Этап 7: Панель Лены (/lena/)

- [ ] Страница: список пользователей с сегментами
- [ ] Страница: создание рассылки (текст + сегмент + расписание)
- [ ] API: POST /lena/mailings/send (broadcast через Bot API)
- [ ] Страница: история рассылок
- [ ] Страница: триггеры (просмотр + вкл/выкл)
- [ ] Триггер: книга готова → автоуведомление
- [ ] Триггер: 7 дней без активности → напоминание
