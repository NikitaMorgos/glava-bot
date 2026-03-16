# Reliability Audit — Чеклист исправлений

## Фаза 1: Quick Wins

- [ ] RL-02: Мониторинг UptimeRobot + Telegram-алерт
- [ ] RL-03: pg_dump cron → S3
- [ ] RL-11: Systemd WatchdogSec, MemoryMax, StartLimitBurst
- [ ] RL-04: n8n webhook retry 3x
- [ ] RL-05: check_payment: api_error vs pending + retry
- [ ] RL-16: DB connect_timeout + statement_timeout
- [ ] RL-13: S3 client singleton + retry config
- [ ] RL-12: Pipeline failure → Telegram-уведомление
- [ ] RL-11: Systemd User=glava
- [ ] RL-19: Nginx proxy timeouts

## Фаза 2: Medium Fixes

- [ ] RL-08: Connection pooling (ThreadedConnectionPool)
- [ ] RL-09: Race conditions (ON CONFLICT, SELECT FOR UPDATE)
- [ ] RL-07: Graceful shutdown + thread tracking
- [ ] RL-04: n8n error branches + user notification
- [ ] RL-10: Retry для Recall.ai / MyMeet
- [ ] RL-06: Deploy: git tag + post-deploy health check
- [ ] RL-21: run_in_executor для sync HTTP
- [ ] RL-19: Nginx rate limiting + error pages
- [ ] RL-17: Log rotation (Docker + journald)
- [ ] RL-15: DB migration in deploy flow

## Фаза 3: Strategic

- [ ] RL-01: Managed PostgreSQL (Yandex MDB)
- [ ] RL-14: Разделение контуров RU/EU
- [ ] RL-07/04: Celery/Redis для задач
- [ ] RL-06: CI/CD (GitHub Actions)
- [ ] RL-03: DR runbook + restore test
- [ ] RL-02: SLO/SLA определение
- [ ] RL-02: Observability stack
