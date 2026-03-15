# Admin Panel + n8n — чеклист

## Этап 1: Инфраструктура ✅
- [x] Установить Docker + Docker Compose на VPS
- [x] Создать `docker-compose.yml` для n8n (с volume для данных)
- [x] Запустить n8n, проверить доступность на :5678
- [x] Создать `admin/app.py` — Flask-приложение на порту 5001
- [x] Создать `deploy/glava-admin.service` — systemd для admin Flask
- [x] Добавить в Nginx: admin.glava.family → 127.0.0.1:5001
- [x] Получить SSL: `certbot --nginx -d admin.glava.family`
- [x] Авторизация: 3 учётки (dev/dasha/lena), role-based

## Этап 2: БД ✅
- [x] Таблица `prompts` (role, version, prompt_text, updated_at, updated_by)
- [x] Таблица `pipeline_jobs` (id, telegram_id, phase, step, status, started_at, finished_at, error)
- [x] Таблица `mailings` (id, name, template_text, segment, scheduled_at, sent_at, sent_count, created_by)
- [x] Таблица `mailing_recipients` (mailing_id, telegram_id, status, sent_at)
- [x] Таблица `mailing_triggers`
- [ ] Наполнить `prompts` промптами 12 агентов (через панель Даши)

## Этап 3: Дашборд разработчика (/dev/) ✅
- [x] Виджет: статус сервисов (glava, glava-cabinet, glava-admin, n8n)
- [x] Виджет: метрики БД (users, drafts, voices, photos)
- [x] Виджет: метрики S3 (объекты, размер)
- [x] Виджет: n8n — статус контейнера
- [x] Виджет: последние ошибки (journalctl ERROR)
- [x] Виджет: git — текущий коммит + дата деплоя
- [x] Виджет: конфиг-чеклист (какие ключи заданы)
- [x] Кнопки управления: Restart Bot / Cabinet / Admin

## Этап 4: Панель Даши (/dasha/) ✅
- [x] Страница: список промптов агентов (12 ролей)
- [x] Страница: редактор промпта с историей версий
- [x] Страница: список заказов (клиент / этап / дата)
- [x] Страница: детали заказа + управление пайплайном
- [x] API: POST /dasha/pipeline/start (→ n8n webhook)
- [x] Страница: отчёт (книг в работе / готово / среднее время)
- [x] Баг: сохранение промпта (KeyError: 0) — исправлен 2026-03-15

## Этап 5: Панель Лены (/lena/) ✅
- [x] Страница: список пользователей с сегментами
- [x] Страница: создание рассылки (текст + сегмент)
- [x] API: POST /lena/mailings/send (broadcast через Bot API)
- [x] Страница: история рассылок
- [x] Страница: триггеры (просмотр + вкл/выкл)

## Этап 6: n8n Phase A ⏳
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

## Этап 7: n8n Phase B ⏳
- [ ] Workflow: Triage Agent (классификация вводной → 6 маршрутов)
- [ ] Маршрут ①: Фактическая поправка
- [ ] Маршрут ②: Стилевой комментарий
- [ ] Маршрут ③: Дополнение текстом
- [ ] Маршрут ④: Новое аудио
- [ ] Маршрут ⑤: Новые фото
- [ ] Маршрут ⑥: Структурная правка
