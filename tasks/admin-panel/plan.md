# Admin Panel + n8n Pipeline — план задачи

## Цель

Создать операционную инфраструктуру GLAVA:
1. **n8n** — оркестратор AI-пайплайна (12 агентов, 2 фазы)
2. **admin.glava.family** — панели управления для 3 ролей:
   - Дашa (Product Manager) — скрипты, заказы, пайплайн
   - Лена (Marketer) — рассылки, сегменты, триггеры
   - Разработчик — технический дашборд сервиса

---

## Архитектура

```
admin.glava.family (Nginx → Flask :5001)
    ├── /login          — авторизация (role-based)
    ├── /dev/           — дашборд разработчика
    ├── /dasha/         — панель продакта
    └── /lena/          — панель маркетолога

n8n (Docker → :5678)  [внутренний, без публичного домена]
    ├── Phase A workflow
    ├── Phase B workflow + Triage
    └── Webhooks → принимает задачи от бота и admin-панели

PostgreSQL (уже есть)
    └── + таблица prompts (12 ролей × prompt_text + history)
    └── + таблица mailings (шаблоны + статусы)
    └── + таблица pipeline_jobs (заказы × этапы)
```

---

## Панель разработчика (/dev/)

| Раздел | Что выводим |
|--------|------------|
| **Сервисы** | Статус + uptime: glava.service, glava-cabinet.service, n8n (ping) |
| **Боевые метрики** | Сообщений за сутки/неделю, активных пользователей, новых |
| **Пайплайн** | Запусков n8n сегодня, успешных/упавших, средняя длительность |
| **БД** | Кол-во users, drafts, voices, photos; размер БД |
| **S3** | Кол-во объектов, суммарный размер хранилища |
| **Ошибки** | Последние 20 строк journalctl ERROR из glava + glava-cabinet |
| **Git** | Текущий коммит на сервере, дата деплоя |
| **Конфиг** | Какие ключи заданы (BOT_TOKEN ✓, OPENAI_API_KEY ✓...) без значений |
| **Управление** | Кнопки: Restart Bot, Restart Cabinet, Restart n8n |

---

## Панель Даши (/dasha/)

| Раздел | Что делает |
|--------|-----------|
| **Скрипты агентов** | CRUD промптов 12 ролей. История версий. Preview-запуск на тестовом тексте |
| **Заказы** | Список клиентов: имя / telegram_id / текущий этап пайплайна / дата |
| **Управление пайплайном** | Для конкретного клиента: запустить этап, перезапустить, пауза |
| **Вопросы** | Просмотр уточняющих вопросов по каждому клиенту (от агента Интервьюер) |
| **Отчёты** | Книг в работе / завершено / среднее время производства |

---

## Панель Лены (/lena/)

| Раздел | Что делает |
|--------|-----------|
| **Пользователи** | Таблица с сегментами: новый / оплатил / книга готова / неактивен (>7 дней) |
| **Рассылки** | Создать рассылку: выбрать сегмент + написать текст + кнопка (опц.) + запустить/отложить |
| **История** | Что отправлено, кому (N чел.), когда, статус (в очереди / отправлено / ошибка) |
| **Триггеры** | Автоматические события: книга готова → уведомление, 7 дн. без актив. → напоминание |

---

## Пайплайн n8n (12 агентов)

### Phase A — первичная сборка

```
Webhook (POST /webhook/start-pipeline)
  ↓
[01] Transcriber      → AssemblyAI/SpeechKit → transcript.txt
  ↓
[02] Fact Extractor   → OpenAI → facts.json (даты, люди, события, gaps)
  ↓                   (параллельно)
[03] Ghostwriter      → OpenAI → book_draft.txt         [07] Photo Editor → обработка фото
  ↓
[04] Fact Checker     → OpenAI → verify (loop ≤3)
  ↓
[05] Literary Editor  → OpenAI → style (loop ≤2)
  ↓                   (параллельно)
[06] Proofreader      → OpenAI → final_text.txt         [11] Interview Architect → questions.txt
  ↓
[08] Layout Designer  → WeasyPrint/typesetter → book_v1.pdf
  ↓
[09] Layout QA        → OpenAI → check PDF (loop ≤3)
  ↓
[10] Producer         → gate: все проверки пройдены?
  ↓
Webhook → Bot → отправляет клиенту book_v1.pdf + questions.txt
```

### Phase B — Triage + 6 маршрутов

```
Webhook (POST /webhook/phase-b)
  ↓
[T] Triage Agent → OpenAI → классифицирует входящее
  ↓
Switch:
  ① Фактическая поправка    → [03]→[06]→[08]→[09]→bot
  ② Стилевой комментарий    → [05]→[06]→[08]→[09]→bot
  ③ Дополнение текстом      → [02]→[03]→[04]→[05]→[06]→[08]→[09]→bot
  ④ Новое аудио             → [01]→[02]→[03]→[04]→[05]→[06]→[08]→[09]→bot
  ⑤ Новые фото              → [07]→[08]→[09]→bot
  ⑥ Структурная правка      → [03]→[04]→[05]→[06]→[08]→[09]→bot
```

---

## Стек

| Компонент | Технология |
|-----------|-----------|
| Admin Flask app | Flask + Jinja2, порт 5001 |
| n8n | Docker (image: n8nio/n8n), порт 5678 |
| Nginx | новый server block: admin.glava.family → :5001 |
| SSL | certbot (уже настроен) |
| Промпты | PostgreSQL таблица `prompts` |
| Рассылки | PostgreSQL таблица `mailings` + `mailing_recipients` |
| Пайплайн-статусы | PostgreSQL таблица `pipeline_jobs` |
| PDF-вёрстка | typesetter.py (уже есть) или WeasyPrint |
| Авторизация | Flask sessions + bcrypt, 3 учётки (dev/dasha/lena) |

---

## Этапы реализации

### Этап 1 — Инфраструктура (n8n + admin домен)
- [ ] Установить Docker на VPS
- [ ] Запустить n8n в Docker
- [ ] Настроить Nginx: admin.glava.family → Flask :5001
- [ ] Получить SSL для admin.glava.family
- [ ] Создать `admin/app.py` — базовый Flask с авторизацией 3 ролей

### Этап 2 — БД: новые таблицы
- [ ] `prompts` (role, version, prompt_text, created_at, created_by)
- [ ] `pipeline_jobs` (telegram_id, phase, current_step, status, started_at)
- [ ] `mailings` (id, template, segment, scheduled_at, sent_at, sent_count)
- [ ] `mailing_recipients` (mailing_id, telegram_id, status)

### Этап 3 — Дашборд разработчика
- [ ] API-эндпоинты: статус сервисов, метрики, журнал ошибок
- [ ] Страница /dev/ с виджетами
- [ ] Кнопки управления сервисами (через subprocess/systemctl API)

### Этап 4 — Панель Даши
- [ ] CRUD для промптов агентов
- [ ] Список заказов с этапами пайплайна
- [ ] Управление пайплайном (запуск/пауза через n8n webhook)

### Этап 5 — n8n Phase A workflow
- [ ] Создать workflow Phase A в n8n (все 12 агентов)
- [ ] Подключить к БД, S3, OpenAI
- [ ] Webhook-интеграция с ботом

### Этап 6 — n8n Phase B workflow
- [ ] Triage Agent + Switch
- [ ] 6 маршрутов обработки

### Этап 7 — Панель Лены
- [ ] Сегменты пользователей
- [ ] Создание и отправка рассылок
- [ ] История рассылок
- [ ] Базовые триггеры (книга готова, неактивность)
