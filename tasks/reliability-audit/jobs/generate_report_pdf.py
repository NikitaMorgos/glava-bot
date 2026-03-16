"""
Генерация PDF-отчёта по аудиту надёжности GLAVA.
Запуск: python tasks/reliability-audit/jobs/generate_report_pdf.py
Результат: tasks/reliability-audit/docs/RELIABILITY_AUDIT_2026-03-15.pdf
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT_DIR = Path(__file__).resolve().parent.parent / "docs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = OUT_DIR / "RELIABILITY_AUDIT_2026-03-15.pdf"

C_TITLE   = HexColor("#1a1a2e")
C_ACCENT  = HexColor("#0ea5e9")
C_H2      = HexColor("#16213e")
C_TEXT    = HexColor("#222222")
C_MUTED   = HexColor("#666666")
C_CELL_BG = HexColor("#f8f9fa")
C_HDR_BG  = HexColor("#1a1a2e")
C_HDR_FG  = HexColor("#FFFFFF")
C_CRIT    = HexColor("#dc2626")
C_HIGH    = HexColor("#ea580c")
C_MED     = HexColor("#ca8a04")
C_LOW     = HexColor("#2563eb")

SEV_COLORS = {"Critical": C_CRIT, "High": C_HIGH, "Medium": C_MED, "Low": C_LOW}


def register_fonts():
    for name, fname in [("DejaVuSans", "DejaVuSans.ttf"), ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf")]:
        for d in [r"C:\Windows\Fonts", r"C:\Users\user\AppData\Local\Microsoft\Windows\Fonts",
                  "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu"]:
            p = os.path.join(d, fname)
            if os.path.isfile(p):
                pdfmetrics.registerFont(TTFont(name, p))
                break
    try:
        pdfmetrics.getFont("DejaVuSans")
        return True
    except Exception:
        return False


def styles(has_font):
    b = "DejaVuSans" if has_font else "Helvetica"
    bb = "DejaVuSans-Bold" if has_font else "Helvetica-Bold"
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("DocTitle", fontName=bb, fontSize=18, leading=22, textColor=C_TITLE, alignment=TA_CENTER, spaceAfter=4*mm))
    ss.add(ParagraphStyle("DocSub", fontName=b, fontSize=10, leading=13, textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=8*mm))
    ss.add(ParagraphStyle("H1", fontName=bb, fontSize=14, leading=18, textColor=C_ACCENT, spaceBefore=10*mm, spaceAfter=4*mm))
    ss.add(ParagraphStyle("H2x", fontName=bb, fontSize=11, leading=14, textColor=C_H2, spaceBefore=6*mm, spaceAfter=3*mm))
    ss.add(ParagraphStyle("Bd", fontName=b, fontSize=9, leading=12, textColor=C_TEXT, alignment=TA_JUSTIFY, spaceAfter=2*mm))
    ss.add(ParagraphStyle("Bl", fontName=b, fontSize=9, leading=12, textColor=C_TEXT, leftIndent=10*mm, bulletIndent=4*mm, spaceAfter=1.5*mm))
    ss.add(ParagraphStyle("Ct", fontName=b, fontSize=7.5, leading=9.5, textColor=C_TEXT))
    ss.add(ParagraphStyle("Cb", fontName=bb, fontSize=7.5, leading=9.5, textColor=C_TEXT))
    ss.add(ParagraphStyle("Ch", fontName=bb, fontSize=7.5, leading=9.5, textColor=C_HDR_FG))
    ss.add(ParagraphStyle("Ft", fontName=b, fontSize=7, leading=9, textColor=C_MUTED, alignment=TA_CENTER))
    return ss


def sev(s, ss):
    c = SEV_COLORS.get(s, C_TEXT)
    return Paragraph(f'<font color="{c.hexval()}">{s}</font>', ss["Cb"])


def tbl(headers, rows, widths, ss, sev_col=None):
    hdr = [Paragraph(h, ss["Ch"]) for h in headers]
    data = [hdr]
    for row in rows:
        cells = []
        for i, c in enumerate(row):
            if sev_col is not None and i == sev_col:
                cells.append(sev(c, ss))
            else:
                cells.append(Paragraph(c, ss["Ct"]))
        data.append(cells)
    t = Table(data, colWidths=widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), C_HDR_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), C_CELL_BG))
    t.setStyle(TableStyle(cmds))
    return t


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=HexColor("#dee2e6"), spaceBefore=4*mm, spaceAfter=4*mm)


# ── data ─────────────────────────────────────────────────────────────

EXEC_SUMMARY = [
    "Вся система — single point of failure: 1 VPS, 1 БД, 1 S3, 0 реплик, 0 failover.",
    "Нет мониторинга и алертинга. Если бот упадёт ночью, никто не узнает до жалобы пользователя.",
    "Нет бэкапов. Ни pg_dump, ни снимков, ни restore procedure. Потеря данных невосстановима.",
    "Нет graceful shutdown: daemon-потоки убиваются при рестарте, транскрипции обрываются без cleanup.",
    "Деплой с даунтаймом: systemctl restart убивает бот и запускает новый. Нет rollback.",
    "Нет retry в критических интеграциях: n8n webhook, YooKassa, Recall.ai, MyMeet — один сбой = потеря данных.",
    "n8n pipeline — самая хрупкая часть: 7 LLM-вызовов без error branch, без retry, без уведомления пользователя.",
    "check_payment глотает ошибки API и возвращает pending — пользователь может застрять навсегда.",
    "БД без connection pooling: каждый запрос = новое TCP-соединение. Burst 20 сообщений = 20+ коннектов.",
    "Race conditions: get_or_create_user, add_character, set_draft_paid — нет блокировок и идемпотентности.",
    "Systemd без watchdog, resource limits, start-limit: зависший бот не обнаруживается, crash-loop не останавливается.",
    "Все сервисы работают от root без ограничений ресурсов.",
    "Нет health checks: /api/health существует, но никто его не вызывает автоматически.",
    "S3 client пересоздаётся на каждый вызов, нет timeout, нет явного retry.",
    "Зависимость от одного зарубежного региона: OpenAI, n8n, PostgreSQL на одном VPS в Европе.",
    "Нет CI/CD — деплой ручной через git pull, риск человеческой ошибки.",
    "Нет DR runbook, нет SLO/SLA, нет error budget.",
    "Pipeline failures invisible: пользователь отправляет голосовое, получает 'сохранено', но биография никогда не генерируется.",
]

RISKS = [
    ("RL-01","Critical","SPOF","Весь проект","1 VPS, 1 PostgreSQL, 1 S3 — потеря сервера = полная потеря сервиса и данных.","Multi-AZ PostgreSQL (Yandex MDB), S3 cross-region replication, второй VPS."),
    ("RL-02","Critical","Ops","Весь проект","Нет мониторинга и алертинга. Инциденты обнаруживаются по жалобам пользователей.","UptimeRobot + Telegram-алерт через бот; Sentry для ошибок."),
    ("RL-03","Critical","Data","Весь проект","Нет бэкапов PostgreSQL, .env, n8n-data, exports/. Нет restore procedure.","Cron pg_dump ежедневно → S3; тестировать restore ежемесячно."),
    ("RL-04","Critical","Resilience","pipeline_n8n.py, phase-a.json","n8n webhook без retry; 7 LLM-вызовов без error branch; пользователь не уведомлён о провале.","Retry 3x с backoff; error branch → уведомление; DLQ для failed jobs."),
    ("RL-05","Critical","Payment","payment_adapter.py:100-125","check_payment глотает ошибки и возвращает pending — пользователь застревает навсегда.","Различать api_error vs pending; retry; webhook подтверждение."),
    ("RL-06","High","Deploy","deploy/deploy.sh","Деплой с даунтаймом (restart), нет rollback, нет pre/post checks, нет миграций.","Blue-green через новый systemd unit; git tag перед deploy; health check после."),
    ("RL-07","High","Resilience","main.py, pipeline_*.py","daemon=True потоки убиваются при shutdown. Транскрипции, записи в БД обрываются.","Tracked thread pool; graceful shutdown с drain; SIGTERM handler."),
    ("RL-08","High","DB","db.py, db_draft.py","Нет connection pooling. Каждый запрос = TCP connect. Burst → connection exhaustion.","psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10)."),
    ("RL-09","High","DB","db.py:35-57, db_draft.py:115-123","Race conditions: get_or_create_user (TOCTOU), add_character (lost update), set_draft_paid (no status guard).","ON CONFLICT для upsert; SELECT FOR UPDATE; rowcount check."),
    ("RL-10","High","Resilience","recall_client.py, mymeet_client.py","Нет retry ни в Recall.ai, ни в MyMeet. Один сбой сети = потеря записи встречи.","Retry 3x с exponential backoff; fallback Recall → MyMeet автоматический."),
    ("RL-11","High","Infra","deploy/glava*.service","Systemd: нет WatchdogSec, MemoryMax, StartLimitBurst. Зависание не обнаруживается, crash-loop бесконечный.","WatchdogSec=60, MemoryMax=512M, StartLimitBurst=5/300s."),
    ("RL-12","High","Resilience","Все pipeline_*.py","Pipeline failure invisible: пользователь получает 'Аудио сохранено', биография не генерируется, уведомления нет.","Telegram-сообщение пользователю при ошибке pipeline."),
    ("RL-13","High","S3","storage.py","S3 client без кэширования, без timeout, без retry config. Один S3 provider — SPOF.","Singleton client; Config(retries=3, connect_timeout=5, read_timeout=30)."),
    ("RL-14","Medium","Geo","Весь проект","Один VPS в Европе. Блокировка IP РКН = полная недоступность. Нет резервного контура в РФ.","DNS failover; бот в РФ + LLM proxy в EU."),
    ("RL-15","Medium","Deploy","scripts/migrate_admin.py","Миграции не вызываются из deploy.sh. Per-statement commit — partial migration possible. Нет version tracking.","Alembic/миграционный фреймворк; вызов из deploy.sh."),
    ("RL-16","Medium","DB","db.py, config.py","Нет connect_timeout, statement_timeout в DATABASE_URL. PostgreSQL hang → бот зависает на 60-120с.","?connect_timeout=5&amp;options=-c statement_timeout=30000"),
    ("RL-17","Medium","Infra","docker/docker-compose.yml","n8n: нет healthcheck, нет resource limits, нет log rotation driver. Логи растут бесконечно.","healthcheck, mem_limit: 512m, logging: json-file max-size: 10m."),
    ("RL-18","Medium","Resilience","transcribe.py:154-176","SpeechKit polling: 2с интервал × 600 итераций, нет backoff. Один 5xx на polling → весь transcribe fails.","Exponential backoff; retry на отдельных polling-запросах."),
    ("RL-19","Medium","Nginx","deploy/nginx-*.conf","Нет proxy timeouts (кроме admin), нет rate limiting, нет custom error pages, нет upstream health.","Таймауты, limit_req_zone, error_page 502/503."),
    ("RL-20","Medium","Resilience","typesetter.py","Anthropic/Claude: нет timeout, нет retry. Зависание → поток заблокирован навсегда.","Timeout 120s, retry 2x."),
    ("RL-21","Medium","App","main.py:72-96","_start_online_meeting_recording: sync HTTP в async def → блокировка event loop.","run_in_executor()."),
    ("RL-22","Medium","Sessions","cabinet/app.py, cabinet/tma_api.py","Cookie-based sessions, нет expiration, нет server-side revocation. Ротация ключа = mass logout.","Redis sessions или server-side store; PERMANENT_SESSION_LIFETIME."),
    ("RL-23","Medium","DB","admin/db_admin.py:16","Читает DATABASE_URL напрямую из env, минуя pooler-fix из config.py.","Импортировать из config.py."),
    ("RL-24","Low","DB","db.py:169-179","get_all_clients: 2 correlated subqueries без LIMIT. O(N) connections на N users.","JOIN + COUNT + LIMIT/pagination."),
    ("RL-25","Low","App","main.py:748-749","config.BOT_TOKEN/DATABASE_URL: AttributeError при отсутствии — нет user-friendly сообщения.","try/except с sys.exit и ясным сообщением."),
    ("RL-26","Low","Resilience","llm_bio.py","OpenAI retry 3x/5-15-30s — хорошо. Но нет model fallback (gpt-4o → gpt-4o-mini).","Fallback на cheaper model при 3x failure."),
    ("RL-27","Low","Infra","deploy/*.service","Gunicorn -w 1: один worker для cabinet и admin. Один медленный запрос блокирует всех.","-w 2 минимум."),
]

SPOF_TABLE = [
    ("VPS (Европа)","Critical","Вся система мертва: бот, кабинет, админка, n8n, БД, файлы.","Второй VPS в РФ или managed services."),
    ("PostgreSQL","Critical","Все данные пользователей, заказов, транскриптов — недоступны.","Managed PostgreSQL с replica; pg_dump backup."),
    ("S3 provider","High","Аудио и фото недоступны. Новые загрузки невозможны.","Cross-region replication; backup bucket."),
    ("n8n (Docker)","High","AI-пайплайн (7 агентов) не работает. Биографии не генерируются.","Retry из Python; persist failed jobs; second instance."),
    ("OpenAI API","High","Биография не генерируется. Основная ценность продукта потеряна.","Retry 3x; fallback на Anthropic; self-hosted LLM."),
    ("Telegram API","Critical","Весь UI бота мёртв.","Нет fallback — зависимость от Telegram."),
    ("YooKassa","High","Новые заказы невозможны. Существующие pending застревают.","Retry; webhook confirmation; запасной провайдер."),
    ("DNS (nic.ru)","Medium","Домены glava.family, app/cabinet/admin — недоступны.","Backup DNS provider; низкий TTL."),
    ("Certbot/SSL","Medium","После истечения — браузеры блокируют доступ, Telegram webhook rejected.","certbot auto-renew timer; alerting за 14 дней."),
    (".env файл","Critical","Все секреты потеряны → сервис невосстановим без ручной перенастройки.","Backup .env в зашифрованном виде; secrets manager."),
]

FAILURE_SCENARIOS = [
    ("PostgreSQL down 5 мин","Bot: все хендлеры зависают на 60-120с (TCP timeout), затем крашатся. Cabinet: 500. Admin: 500. Пользователи видят 'нет ответа'. Нет retry, нет circuit breaker.","Critical"),
    ("S3 down","Новые аудио/фото не сохраняются. Dashboard показывает broken links. Пайплайн прерывается. Нет fallback.","High"),
    ("OpenAI down 1 час","Транскрипты сохраняются, но биографии не генерируются. Пользователь не уведомлён. n8n pipeline: все 7 агентов fail, job stuck.","High"),
    ("n8n container OOM/crash","Pipeline jobs пропадают. Retry нет. Пользователь ждёт биографию бесконечно. Docker restart=always перезапустит, но in-flight jobs потеряны.","High"),
    ("VPS reboot","Бот, cabinet, admin перезапускаются через systemd. Daemon threads (транскрипции) убиты. Telegram messages during restart — dropped. n8n volume preserved.","High"),
    ("Disk full","PostgreSQL: refuse writes, потенциально corrupt WAL. n8n: SQLite corrupt. Exports: write fails. Бот крашится на аудио-upload. Нет disk monitoring.","High"),
    ("Certbot renewal fails","Через 90 дней: HTTPS broken. Telegram webhook отвергнут. Cabinet/admin недоступны в браузере. Нет alerting.","Medium"),
    ("Network partition RU↔EU","Telegram delivery OK (Telegram servers route). Но кабинет/админка/лендинг — timeout для RU-пользователей. YooKassa callbacks — timeout.","Medium"),
    ("Recall.ai down","Online meeting recording невозможна. Нет автоматического fallback на MyMeet — только manual при отсутствии RECALL_API_KEY.","Medium"),
    ("Memory leak в боте","Без MemoryMax: процесс растёт до OOM. systemd restart=always перезапустит, но все daemon threads потеряны. Цикл повторяется.","Medium"),
]

READINESS = [
    ("Health checks","Частично","/api/health в admin — shallow (не проверяет DB/S3). Никем не вызывается автоматически."),
    ("Liveness/readiness probes","Нет","Нет для systemd (WatchdogSec), нет для Docker (healthcheck)."),
    ("Retries with backoff","Частично","Только llm_bio.py (3x/5-15-30s) и assemblyai_client.py (3x/10s). Отсутствуют в n8n, payment, recall, mymeet, S3."),
    ("Timeouts","Частично","OpenAI: 180s. AssemblyAI: 600s. Recall: 30-60s. НО: S3, DB connect, typesetter — нет timeout."),
    ("Circuit breakers","Нет","Ни одного. Каждый запрос к упавшему сервису проходит полный цикл ошибки."),
    ("Idempotency","Нет","YooKassa payment без idempotence_key. n8n webhook без dedup. DB upsert без ON CONFLICT."),
    ("Dead-letter queues","Нет","Failed pipeline jobs просто логируются. Нет механизма повторной обработки."),
    ("Rate limits","Нет","Ни на Flask endpoints, ни в Nginx, ни на bot handlers."),
    ("Graceful shutdown","Нет","daemon=True потоки. Нет SIGTERM handler в main.py. Нет thread drain."),
    ("Rollback","Нет","Нет git tag до deploy, нет blue-green, нет DB migration rollback."),
    ("Backup schedules","Нет","Нет cron, нет pg_dump, нет S3 backup, нет .env backup."),
    ("Restore procedures","Нет","Нет runbook, нет тестирования restore, нет RTO/RPO."),
    ("DR runbooks","Нет","Нет документации по disaster recovery."),
    ("Alerting","Нет","Нет email/Telegram/PagerDuty при crash, OOM, cert expiry."),
    ("SLO/SLA/error budget","Нет","Не определены."),
]

EXT_SERVICES = [
    ("Telegram API","Critical","Library-managed","Library-managed","Нет (монополия)","Бот полностью мёртв","Можно пережить: нет"),
    ("OpenAI","Critical","180s, retry 3x","3x backoff 5/15/30s","Нет (нет model fallback)","Биография не генерируется","Можно пережить: частично (транскрипт сохранён)"),
    ("YooKassa","Critical","Нет timeout","Нет retry","Stub (dev only)","Оплата невозможна; pending застревает","Можно пережить: нет"),
    ("S3 Storage","Critical","Нет timeout","boto3 built-in (5x)","Нет","Файлы не сохраняются/не скачиваются","Можно пережить: нет"),
    ("AssemblyAI","High","600s","3x/10s","Нет","Транскрипция fails, пользователь не уведомлён","Можно пережить: да (SpeechKit fallback if configured)"),
    ("Recall.ai","High","30-60s","Нет retry","MyMeet (ручной)","Запись встречи невозможна","Можно пережить: частично"),
    ("SpeechKit","High","30s/120s","OGG auto-retry","Whisper (local)","Лучший fallback в проекте","Можно пережить: да"),
    ("MyMeet","Medium","30-120s","Нет retry","Нет","Файловая транскрипция fails","Можно пережить: да (AssemblyAI)"),
    ("Anthropic","Low","Нет timeout","Нет retry","Упрощённый layout","PDF не генерируется","Можно пережить: да"),
    ("n8n (self-hosted)","High","Косвенно","Нет retry","Нет","7-агентный пайплайн мёртв","Можно пережить: частично (прямой OpenAI fallback)"),
]

QUICK_WINS = [
    ("1","Мониторинг: UptimeRobot ping /api/health + Telegram-алерт","—","2ч"),
    ("2","pg_dump cron: ежедневный бэкап в S3","cron + скрипт","3ч"),
    ("3","Systemd: WatchdogSec=60, MemoryMax=512M, StartLimitBurst=5","deploy/*.service","1ч"),
    ("4","n8n webhook: retry 3x с backoff в pipeline_n8n.py","pipeline_n8n.py","1ч"),
    ("5","check_payment: различать api_error vs pending; retry 2x","payment_adapter.py","1ч"),
    ("6","DB connect_timeout=5s, statement_timeout=30s","config.py","30мин"),
    ("7","S3 client singleton + Config(retries=3, timeout)","storage.py","30мин"),
    ("8","Pipeline failure → Telegram-сообщение пользователю","pipeline_*.py","2ч"),
    ("9","Systemd User=glava вместо root","deploy/*.service + сервер","1ч"),
    ("10","Nginx: proxy_read_timeout 60s для всех vhosts","deploy/nginx-*.conf","30мин"),
]

MEDIUM_FIXES = [
    ("11","Connection pooling: ThreadedConnectionPool","db.py, db_draft.py","4ч"),
    ("12","Race condition fixes: ON CONFLICT, SELECT FOR UPDATE","db.py, db_draft.py","4ч"),
    ("13","Graceful shutdown: thread tracking, SIGTERM drain","main.py","4ч"),
    ("14","n8n workflow: error branches + failure notification","phase-a.json","4ч"),
    ("15","Retry для Recall.ai и MyMeet","recall_client.py, mymeet_client.py","3ч"),
    ("16","Deploy: git tag + health check post-restart","deploy/deploy.sh","2ч"),
    ("17","run_in_executor для sync HTTP в async handlers","main.py","2ч"),
    ("18","Nginx: rate limiting, error pages, upstream health","nginx configs","3ч"),
    ("19","Log rotation для Docker и journald","docker-compose + logrotate","1ч"),
    ("20","DB migration integration в deploy flow","deploy.sh + migrate_admin.py","2ч"),
]

STRATEGIC = [
    ("21","Managed PostgreSQL (Yandex MDB) с репликацией","Устраняет SPOF БД, даёт point-in-time recovery."),
    ("22","Разделение контуров: бот в РФ, LLM proxy в EU","Устраняет зависимость от одного региона."),
    ("23","Celery/Redis вместо daemon threads","Персистентные задачи, retry, DLQ, мониторинг."),
    ("24","CI/CD: GitHub Actions (lint → test → deploy → healthcheck)","Устраняет ручной деплой и человеческий фактор."),
    ("25","DR runbook + quarterly restore test","Документированное восстановление, проверенное RTO/RPO."),
    ("26","SLO: 99.5% uptime, <5мин MTTR для бота","Измеримые цели надёжности."),
    ("27","Observability stack: Prometheus + Grafana + Loki","Метрики, дашборды, алерты по всем компонентам."),
]

CHECKED_FILES = [
    "main.py, config.py, db.py, db_draft.py, payment_adapter.py, storage.py",
    "pipeline_transcribe_bio.py, pipeline_assemblyai_bio.py, pipeline_plaud_bio.py",
    "pipeline_mymeet_bio.py, pipeline_recall_bio.py, pipeline_n8n.py",
    "transcribe.py, assemblyai_client.py, recall_client.py, mymeet_client.py",
    "llm_bio.py, typesetter.py, biographical_prompt.py, clarifying_questions_prompt.py",
    "cabinet/app.py, cabinet/tma_api.py",
    "admin/app.py, admin/auth.py, admin/db_admin.py",
    "admin/blueprints/dev.py, dasha.py, lena.py, api.py",
    "n8n-workflows/phase-a.json, docker/docker-compose.yml",
    "deploy/deploy.sh, deploy/glava.service, glava-cabinet.service, glava-admin.service",
    "deploy/nginx-glava.conf, nginx-cabinet.conf, nginx-admin.conf, nginx-tma.conf, nginx-glava-cabinet.conf",
    "DEPLOY_24_7.md, DEPLOY_TIMEWEB.md, deploy/DEPLOY_GLAVA_FAMILY.md",
    "scripts/migrate_admin.py, requirements.txt, requirements-dev.txt",
]

TO_VERIFY = [
    ("systemctl list-timers на VPS","Есть ли certbot-renew timer, logrotate, cron jobs."),
    ("PostgreSQL max_connections","Сколько соединений допускает инстанс."),
    ("df -h на VPS","Свободное место на диске."),
    ("free -m на VPS","Доступная память."),
    ("docker stats glava-n8n","Потребление памяти n8n."),
    ("ls -la /opt/glava/exports/","Размер накопленных данных."),
    ("pg_dump --list","Что реально в БД, размер таблиц."),
    ("S3 bucket versioning/lifecycle","Включено ли версионирование, есть ли lifecycle policy."),
    ("journalctl --disk-usage","Размер системных логов."),
    ("uptime и last reboot","Время работы, история перезагрузок."),
]


def build():
    has_font = register_fonts()
    ss = styles(has_font)
    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=18*mm, bottomMargin=18*mm,
                            title="GLAVA Reliability Audit", author="AI SRE Reviewer")
    s = []

    s.append(Spacer(1, 12*mm))
    s.append(Paragraph("GLAVA — Аудит надёжности и отказоустойчивости", ss["DocTitle"]))
    s.append(Paragraph("SRE · Platform Architecture · Backend Resilience", ss["DocSub"]))
    s.append(Paragraph("Дата: 15 марта 2026 &nbsp;|&nbsp; Версия: 1.0 &nbsp;|&nbsp; Статус: Draft", ss["DocSub"]))
    s.append(hr())

    # 1
    s.append(Paragraph("1. Executive Summary", ss["H1"]))
    for i, item in enumerate(EXEC_SUMMARY, 1):
        s.append(Paragraph(f"<b>{i}.</b> {item}", ss["Bl"]))

    s.append(PageBreak())

    # 2
    s.append(Paragraph("2. Таблица Reliability Risks", ss["H1"]))
    s.append(Paragraph("27 рисков: 5 Critical, 8 High, 10 Medium, 4 Low.", ss["Bd"]))
    s.append(Spacer(1, 3*mm))
    s.append(tbl(
        ["ID","Severity","Category","Where","Risk","Fix"],
        RISKS,
        [12*mm, 16*mm, 18*mm, 28*mm, 52*mm, 40*mm],
        ss, sev_col=1,
    ))

    s.append(PageBreak())

    # 3
    s.append(Paragraph("3. Single Points of Failure", ss["H1"]))
    s.append(tbl(
        ["Компонент","Критичность","Последствия отказа","Рекомендация"],
        SPOF_TABLE,
        [28*mm, 18*mm, 65*mm, 56*mm],
        ss, sev_col=1,
    ))

    s.append(Spacer(1, 6*mm))

    # 4
    s.append(Paragraph("4. Сценарии отказа", ss["H1"]))
    s.append(tbl(
        ["Сценарий","Последствия","Severity"],
        FAILURE_SCENARIOS,
        [35*mm, 95*mm, 18*mm],
        ss, sev_col=2,
    ))

    s.append(PageBreak())

    # 5
    s.append(Paragraph("5. Readiness к Recovery", ss["H1"]))
    s.append(Paragraph("Проверка наличия стандартных механизмов надёжности.", ss["Bd"]))
    s.append(Spacer(1, 3*mm))
    s.append(tbl(
        ["Механизм","Статус","Детали"],
        READINESS,
        [35*mm, 18*mm, 114*mm],
        ss,
    ))

    s.append(Spacer(1, 6*mm))

    # 6
    s.append(Paragraph("6. Внешние зависимости", ss["H1"]))
    s.append(tbl(
        ["Сервис","Критичность","Timeout","Retry","Fallback","Impact","Выживаемость"],
        EXT_SERVICES,
        [22*mm, 16*mm, 18*mm, 22*mm, 22*mm, 35*mm, 32*mm],
        ss, sev_col=1,
    ))

    s.append(PageBreak())

    # 7
    s.append(Paragraph("7. План исправления", ss["H1"]))

    s.append(Paragraph("7.1. Quick Wins (1–3 дня)", ss["H2x"]))
    s.append(tbl(["#","Действие","Файл(ы)","Effort"], QUICK_WINS, [8*mm, 75*mm, 55*mm, 16*mm], ss))

    s.append(Spacer(1, 5*mm))
    s.append(Paragraph("7.2. Medium Fixes (1–2 недели)", ss["H2x"]))
    s.append(tbl(["#","Действие","Файл(ы)","Effort"], MEDIUM_FIXES, [8*mm, 75*mm, 55*mm, 16*mm], ss))

    s.append(Spacer(1, 5*mm))
    s.append(Paragraph("7.3. Strategic (месяц+)", ss["H2x"]))
    s.append(tbl(["#","Действие","Описание"], STRATEGIC, [8*mm, 55*mm, 104*mm], ss))

    s.append(PageBreak())

    # 8
    s.append(Paragraph("8. Просмотренные файлы", ss["H1"]))
    for line in CHECKED_FILES:
        s.append(Paragraph(f"• {line}", ss["Bl"]))

    s.append(Spacer(1, 6*mm))

    # 9
    s.append(Paragraph("9. Требует проверки на сервере", ss["H1"]))
    s.append(tbl(["Что проверить","Зачем"], TO_VERIFY, [55*mm, 112*mm], ss))

    s.append(Spacer(1, 10*mm))
    s.append(hr())
    s.append(Paragraph("Конец отчёта. Документ сгенерирован автоматически. Не является SLA-обязательством.", ss["Ft"]))

    doc.build(s)
    print(f"PDF saved: {PDF_PATH}")


if __name__ == "__main__":
    build()
