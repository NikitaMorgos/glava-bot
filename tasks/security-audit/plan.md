# Security Audit — План работ

## Цель

Устранить выявленные риски безопасности, приватности и compliance проекта GLAVA. Привести инфраструктуру в соответствие с требованиями ФЗ-152 и базовыми стандартами AppSec.

---

## Фаза 1: Quick Wins (1–3 дня)

Минимальные изменения с максимальным эффектом. Не требуют архитектурных решений.

| # | Задача | Файл(ы) | Effort | Risk ID |
|---|--------|---------|--------|---------|
| 1 | Убрать BOT_TOKEN из payload n8n; n8n читает из $env.BOT_TOKEN | `pipeline_n8n.py`, `phase-a.json` | 2ч | R-01 |
| 2 | Настроить файрвол: `ufw allow 22,80,443/tcp && ufw enable` | `deploy/deploy.sh` | 30мин | R-03 |
| 3 | Cabinet bind `127.0.0.1:5000` вместо `0.0.0.0` | `deploy/glava-cabinet.service` | 5мин | R-08 |
| 4 | Убрать fallback secret keys, crash если не задан | `admin/app.py`, `cabinet/app.py`, `cabinet/tma_api.py` | 30мин | R-07 |
| 5 | `set_draft_paid` + `user_id` + `payment_id IS NOT NULL` в WHERE | `db_draft.py` | 30мин | R-12 |
| 6 | Заменить `f"Ошибка: {e}"` на generic сообщение | `main.py` | 30мин | R-17 |
| 7 | IDOR fix — проверка ownership в `cfg_del` | `main.py` | 30мин | R-19 |
| 8 | `hmac.compare_digest` для API key | `admin/blueprints/api.py` | 5мин | R-20 |
| 9 | Guard `ALLOW_ONLINE_WITHOUT_PAYMENT` в prod | `config.py` | 15мин | R-21 |
| 10 | Cookie security flags: Secure, SameSite, HttpOnly | `admin/app.py`, `cabinet/app.py` | 15мин | R-23 |
| 11 | Session expiration: `PERMANENT_SESSION_LIFETIME = 8h` | `admin/app.py`, `cabinet/app.py` | 15мин | R-23 |
| 12 | Stub payment → raise error в prod | `payment_adapter.py` | 15мин | R-27 |
| 13 | XSS fix: escHtml для caption и download_url в TMA | `tma/index.html` | 30мин | R-24 |
| 14 | Nginx security headers (HSTS, CSP, X-Frame-Options) | Все nginx конфиги | 1ч | R-13 |
| 15 | n8n: убрать changeme, пиннить версию образа | `docker/docker-compose.yml` | 15мин | R-09, R-32 |

---

## Фаза 2: Medium Fixes (1–2 недели)

Требуют больше кода и тестирования, но остаются в рамках текущей архитектуры.

| # | Задача | Файл(ы) | Effort | Risk ID |
|---|--------|---------|--------|---------|
| 16 | bcrypt для админ-паролей + убрать plaintext-дефолты | `admin/app.py` | 3ч | R-04 |
| 17 | CSRF-защита: `flask-wtf` CSRFProtect + токены | Все Flask-приложения | 4ч | R-06 |
| 18 | Rate limiting: `flask-limiter` + Nginx `limit_req_zone` | Flask + Nginx | 3ч | R-11 |
| 19 | Systemd: создать user `glava`, hardening директивы | Все `.service` файлы | 4ч | R-02 |
| 20 | Бэкапы: cron pg_dump + S3 upload + .env copy | Новый cron + скрипт | 4ч | R-10 |
| 21 | n8n: bridge network, убрать host mode | `docker/docker-compose.yml` | 2ч | R-09 |
| 22 | SSL для landing и cabinet nginx | nginx конфиги | 2ч | R-16 |
| 23 | Audit log: middleware для записи действий админов | `admin/` | 4ч | R-25 |
| 24 | Basic Auth на n8n webhook | `pipeline_n8n.py` | 30мин | R-18 |
| 25 | Data retention policy + cleanup cron для `exports/` | Pipeline + cron | 4ч | R-15 |

---

## Фаза 3: Strategic Fixes (месяц+)

Архитектурные изменения, юридические документы, разделение контуров.

| # | Задача | Описание | Risk ID |
|---|--------|----------|---------|
| 31 | Разделение контуров RU/EU | PostgreSQL с ПД в РФ (Yandex MDB). VPS EU только для LLM-вызовов. Sync минимального набора данных. | R-05 |
| 32 | Privacy Policy и согласие | Юрист → документ ПД, уведомление РКН, кнопка согласия в боте, право на удаление. | R-05 |
| 33 | DPA с внешними сервисами | Data Processing Agreements: OpenAI, AssemblyAI, Anthropic, Recall.ai, MyMeet. | R-05, R-14 |
| 34 | Data minimization | Псевдонимизация имён и дат перед отправкой в LLM. | R-05 |
| 35 | Self-hosted LLM | vLLM/ollama для промежуточных шагов (Fact Checker, Proofreader). | R-05 |
| 36 | CI/CD | GitHub Actions: lint, pytest, deploy pipeline. | R-33 |
| 37 | Consent для записи встреч | Уведомление всех участников (Recall.ai) + explicit opt-in. | R-05 |

---

## Целевая архитектура

```
РОССИЯ                              ЕВРОПА (EU VPS)
┌──────────────────────────┐       ┌──────────────────────┐
│ PostgreSQL (Yandex MDB)  │       │ n8n (LLM orchestr.)  │
│ S3 (Yandex Object Stor.) │  ───▶ │ OpenAI/Anthropic API │
│ Telegram Bot (main.py)   │       │ Нет первичного       │
│ Cabinet, Admin Panel     │       │ хранения ПД          │
│ SpeechKit, ЮKassa        │       └──────────────────────┘
└──────────────────────────┘
```

Принцип: первичные ПД граждан РФ хранятся и обрабатываются в РФ. Европейский VPS получает только обезличенные транскрипты по согласию субъекта для LLM-обработки.

---

## Зависимости

- Фаза 1 не зависит от других фаз — можно начинать немедленно.
- Фаза 2 частично зависит от Фазы 1 (сначала файрвол, потом hardening).
- Фаза 3 требует бизнес-решений (бюджет на Yandex MDB, юрист для ПД).
