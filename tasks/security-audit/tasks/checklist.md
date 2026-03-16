# Security Audit — Чеклист исправлений

## Фаза 1: Quick Wins

- [ ] R-01: Убрать BOT_TOKEN из payload n8n
- [ ] R-03: Настроить ufw на VPS
- [ ] R-08: Cabinet bind 127.0.0.1:5000
- [ ] R-07: Убрать fallback secret keys
- [ ] R-12: set_draft_paid + user_id + payment_id
- [ ] R-17: Generic error messages в main.py
- [ ] R-19: IDOR fix cfg_del
- [ ] R-20: hmac.compare_digest для API key
- [ ] R-21: Guard ALLOW_ONLINE_WITHOUT_PAYMENT
- [ ] R-23: Cookie security flags + session expiration
- [ ] R-27: Stub payment → error в prod
- [ ] R-24: XSS fix escHtml в TMA
- [ ] R-13: Nginx security headers
- [ ] R-09/R-32: n8n changeme + pin version

## Фаза 2: Medium Fixes

- [ ] R-04: bcrypt для админ-паролей
- [ ] R-06: CSRF-защита flask-wtf
- [ ] R-11: Rate limiting
- [ ] R-02: Systemd user glava + hardening
- [ ] R-10: Бэкапы pg_dump + S3
- [ ] R-09: n8n bridge network
- [ ] R-16: SSL для landing/cabinet
- [ ] R-25: Audit log
- [ ] R-18: Basic Auth на n8n webhook
- [ ] R-15: Data retention policy

## Фаза 3: Strategic

- [ ] R-05: Разделение контуров RU/EU
- [ ] R-05: Privacy Policy + уведомление РКН
- [ ] R-05/R-14: DPA с внешними сервисами
- [ ] R-05: Data minimization / псевдонимизация
- [ ] R-05: Self-hosted LLM
- [ ] R-33: CI/CD pipeline
- [ ] R-05: Consent для записи встреч
