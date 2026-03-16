# Reliability Audit — План работ

## Цель

Устранить single points of failure, обеспечить мониторинг, бэкапы, graceful degradation и recoverability для всех компонентов GLAVA.

---

## Фаза 1: Quick Wins (1–3 дня)

Минимальные изменения, максимальный эффект на reliability.

| # | Задача | Файл(ы) | Effort | Risk ID |
|---|--------|---------|--------|---------|
| 1 | Мониторинг: UptimeRobot ping /api/health + Telegram-алерт | — | 2ч | RL-02 |
| 2 | pg_dump cron: ежедневный бэкап → S3 | cron + скрипт | 3ч | RL-03 |
| 3 | Systemd: WatchdogSec=60, MemoryMax=512M, StartLimitBurst=5 | deploy/*.service | 1ч | RL-11 |
| 4 | n8n webhook: retry 3x с backoff | pipeline_n8n.py | 1ч | RL-04 |
| 5 | check_payment: различать api_error vs pending; retry 2x | payment_adapter.py | 1ч | RL-05 |
| 6 | DB connect_timeout=5s, statement_timeout=30s | config.py | 30мин | RL-16 |
| 7 | S3 client singleton + Config(retries=3, timeout) | storage.py | 30мин | RL-13 |
| 8 | Pipeline failure → Telegram-сообщение пользователю | pipeline_*.py | 2ч | RL-12 |
| 9 | Systemd User=glava вместо root | deploy/*.service | 1ч | RL-11 |
| 10 | Nginx: proxy_read_timeout 60s для всех vhosts | deploy/nginx-*.conf | 30мин | RL-19 |

---

## Фаза 2: Medium Fixes (1–2 недели)

| # | Задача | Файл(ы) | Effort | Risk ID |
|---|--------|---------|--------|---------|
| 11 | Connection pooling: ThreadedConnectionPool | db.py, db_draft.py | 4ч | RL-08 |
| 12 | Race condition fixes: ON CONFLICT, SELECT FOR UPDATE | db.py, db_draft.py | 4ч | RL-09 |
| 13 | Graceful shutdown: thread tracking, SIGTERM drain | main.py | 4ч | RL-07 |
| 14 | n8n workflow: error branches + failure notification | phase-a.json | 4ч | RL-04 |
| 15 | Retry для Recall.ai и MyMeet | recall_client.py, mymeet_client.py | 3ч | RL-10 |
| 16 | Deploy: git tag + health check post-restart | deploy/deploy.sh | 2ч | RL-06 |
| 17 | run_in_executor для sync HTTP в async handlers | main.py | 2ч | RL-21 |
| 18 | Nginx: rate limiting, error pages, upstream health | nginx configs | 3ч | RL-19 |
| 19 | Log rotation для Docker и journald | docker-compose + logrotate | 1ч | RL-17 |
| 20 | DB migration integration в deploy flow | deploy.sh + migrate_admin.py | 2ч | RL-15 |

---

## Фаза 3: Strategic (месяц+)

| # | Задача | Описание | Risk ID |
|---|--------|----------|---------|
| 21 | Managed PostgreSQL (Yandex MDB) | Репликация, автоматический failover, point-in-time recovery | RL-01 |
| 22 | Разделение контуров: бот в РФ, LLM proxy в EU | Устраняет зависимость от одного региона | RL-14 |
| 23 | Celery/Redis вместо daemon threads | Персистентные задачи, retry, DLQ, мониторинг | RL-07, RL-04 |
| 24 | CI/CD: GitHub Actions | lint → test → deploy → healthcheck | RL-06 |
| 25 | DR runbook + quarterly restore test | Документированное восстановление, проверенное RTO/RPO | RL-03 |
| 26 | SLO: 99.5% uptime, <5мин MTTR | Измеримые цели надёжности | RL-02 |
| 27 | Observability: Prometheus + Grafana + Loki | Метрики, дашборды, алерты | RL-02 |

---

## Зависимости

- Фаза 1 не зависит от других фаз — старт немедленно.
- Задачи 1-3 (мониторинг, бэкапы, systemd) дают максимальный ROI и должны быть первыми.
- Фаза 2 зависит от Фазы 1 частично (сначала systemd user, потом hardening).
- Фаза 3 требует бюджета (Yandex MDB, CI/CD runners).
