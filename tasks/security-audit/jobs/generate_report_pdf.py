"""
Генерация PDF-отчёта по аудиту безопасности GLAVA.
Запуск: python tasks/security-audit/jobs/generate_report_pdf.py
Результат: tasks/security-audit/docs/SECURITY_AUDIT_2026-03-15.pdf
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
    PageBreak, HRFlowable, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT_DIR = Path(__file__).resolve().parent.parent / "docs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = OUT_DIR / "SECURITY_AUDIT_2026-03-15.pdf"

# ── colours ──────────────────────────────────────────────────────────
C_BG        = HexColor("#FFFFFF")
C_TITLE     = HexColor("#1a1a2e")
C_ACCENT    = HexColor("#e94560")
C_H2        = HexColor("#16213e")
C_TEXT      = HexColor("#222222")
C_MUTED     = HexColor("#666666")
C_CELL_BG   = HexColor("#f8f9fa")
C_HDR_BG    = HexColor("#1a1a2e")
C_HDR_FG    = HexColor("#FFFFFF")
C_CRIT      = HexColor("#dc2626")
C_HIGH      = HexColor("#ea580c")
C_MED       = HexColor("#ca8a04")
C_LOW       = HexColor("#2563eb")

SEVERITY_COLORS = {
    "Critical": C_CRIT, "High": C_HIGH, "Medium": C_MED, "Low": C_LOW,
}


def register_fonts():
    candidates = [
        ("DejaVuSans", "DejaVuSans.ttf"),
        ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
    ]
    dirs = [
        r"C:\Windows\Fonts",
        r"C:\Users\user\AppData\Local\Microsoft\Windows\Fonts",
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
    ]
    found = {}
    for name, fname in candidates:
        for d in dirs:
            p = os.path.join(d, fname)
            if os.path.isfile(p):
                pdfmetrics.registerFont(TTFont(name, p))
                found[name] = True
                break
    return "DejaVuSans" in found


def build_styles(has_font: bool):
    base = "DejaVuSans" if has_font else "Helvetica"
    bold = "DejaVuSans-Bold" if has_font else "Helvetica-Bold"
    ss = getSampleStyleSheet()

    ss.add(ParagraphStyle("DocTitle", fontName=bold, fontSize=18, leading=22,
                          textColor=C_TITLE, alignment=TA_CENTER, spaceAfter=4*mm))
    ss.add(ParagraphStyle("DocSubtitle", fontName=base, fontSize=10, leading=13,
                          textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=8*mm))
    ss.add(ParagraphStyle("H1", fontName=bold, fontSize=14, leading=18,
                          textColor=C_ACCENT, spaceBefore=10*mm, spaceAfter=4*mm))
    ss.add(ParagraphStyle("H2", fontName=bold, fontSize=11, leading=14,
                          textColor=C_H2, spaceBefore=6*mm, spaceAfter=3*mm))
    ss.add(ParagraphStyle("Body", fontName=base, fontSize=9, leading=12,
                          textColor=C_TEXT, alignment=TA_JUSTIFY, spaceAfter=2*mm))
    ss.add(ParagraphStyle("BodySmall", fontName=base, fontSize=8, leading=10,
                          textColor=C_TEXT, spaceAfter=1*mm))
    ss.add(ParagraphStyle("BulletCustom", fontName=base, fontSize=9, leading=12,
                          textColor=C_TEXT, leftIndent=10*mm, bulletIndent=4*mm,
                          spaceAfter=1.5*mm))
    ss.add(ParagraphStyle("CodeBlock", fontName="Courier", fontSize=7.5, leading=9.5,
                          textColor=C_MUTED, leftIndent=6*mm, spaceAfter=2*mm,
                          backColor=HexColor("#f4f4f5")))
    ss.add(ParagraphStyle("CellText", fontName=base, fontSize=7.5, leading=9.5,
                          textColor=C_TEXT))
    ss.add(ParagraphStyle("CellBold", fontName=bold, fontSize=7.5, leading=9.5,
                          textColor=C_TEXT))
    ss.add(ParagraphStyle("CellHdr", fontName=bold, fontSize=7.5, leading=9.5,
                          textColor=C_HDR_FG))
    ss.add(ParagraphStyle("Footer", fontName=base, fontSize=7, leading=9,
                          textColor=C_MUTED, alignment=TA_CENTER))
    return ss


def sev_para(sev: str, ss):
    color = SEVERITY_COLORS.get(sev, C_TEXT)
    return Paragraph(f'<font color="{color.hexval()}">{sev}</font>', ss["CellBold"])


def make_risk_table(risks, ss):
    col_widths = [12*mm, 18*mm, 22*mm, 30*mm, 55*mm, 30*mm]
    header = [Paragraph(h, ss["CellHdr"]) for h in
              ["ID", "Severity", "Category", "Where", "Risk / Evidence", "Fix"]]
    data = [header]
    for r in risks:
        data.append([
            Paragraph(r[0], ss["CellText"]),
            sev_para(r[1], ss),
            Paragraph(r[2], ss["CellText"]),
            Paragraph(r[3], ss["CellText"]),
            Paragraph(r[4], ss["CellText"]),
            Paragraph(r[5], ss["CellText"]),
        ])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), C_HDR_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_HDR_FG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_CELL_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


def make_simple_table(headers, rows, col_widths, ss):
    hdr = [Paragraph(h, ss["CellHdr"]) for h in headers]
    data = [hdr]
    for row in rows:
        data.append([Paragraph(c, ss["CellText"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
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
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_CELL_BG))
    t.setStyle(TableStyle(style_cmds))
    return t


def hr():
    return HRFlowable(width="100%", thickness=0.5, color=HexColor("#dee2e6"),
                      spaceBefore=4*mm, spaceAfter=4*mm)


# ── content ──────────────────────────────────────────────────────────

EXEC_SUMMARY = [
    "BOT_TOKEN передаётся в payload n8n-вебхука и хранится в истории исполнения n8n — полный контроль над ботом при утечке.",
    "Все 3 systemd-сервиса работают от root — любая RCE-уязвимость = полный доступ к серверу.",
    "Нет файрвола — задокументированных правил ufw/iptables нет, все порты открыты наружу.",
    "Пароли админ-панели хранятся и сравниваются в plaintext с дефолтами dev123, dasha123, lena123.",
    "Биографические данные (здоровье, политика, конфликты) передаются в 4 SaaS-сервиса в США (OpenAI, AssemblyAI, Recall.ai, Anthropic) без DPA.",
    "Нет CSRF-защиты ни на одной форме во всех Flask-приложениях.",
    "Захардкоженные fallback-ключи Flask-сессий позволяют подделку cookies.",
    "Cabinet биндится на 0.0.0.0:5000 — доступен напрямую в обход Nginx, без SSL.",
    "n8n использует network_mode: host, дефолт-пароль changeme, порт 5678 наружу.",
    "Нет бэкапов БД, секретов, данных n8n.",
    "Нет rate limiting ни на одном endpoint-е.",
    "set_draft_paid не проверяет payment_id и user_id — любой черновик можно отметить оплаченным.",
    "Нет security headers (HSTS, CSP, X-Frame-Options) ни в одном nginx-конфиге.",
    "Данные граждан РФ первично записываются и обрабатываются за пределами РФ — нарушение ФЗ-152 ст. 18 ч. 5.",
    "Нет audit log — действия админов не логируются.",
]

RISKS = [
    ("R-01","Critical","Security","pipeline_n8n.py, phase-a.json","BOT_TOKEN в payload вебхука и URL Telegram API внутри n8n. Утечка = полный контроль над ботом.","Убрать BOT_TOKEN из payload; n8n читает из $env.BOT_TOKEN."),
    ("R-02","Critical","Infra","glava.service, glava-cabinet.service, glava-admin.service","User=root — любая уязвимость в Python = root на сервере.","Создать user glava, запустить от него, systemd hardening."),
    ("R-03","Critical","Infra","Весь проект","Нет файрвола. Порты 5000, 5001, 5678 открыты.","ufw allow 22,80,443/tcp &amp;&amp; ufw enable."),
    ("R-04","Critical","Security","admin/app.py:25-28,64","Пароли в plaintext, ==, дефолты dev123/dasha123/lena123.","bcrypt, убрать дефолты, timing-safe compare."),
    ("R-05","Critical","Privacy","llm_bio.py, typesetter.py, assemblyai_client.py, recall_client.py","ПД (биографии, голос, фото) → 4 SaaS США без DPA. Нарушение ФЗ-152.","DPA с сервисами; self-hosted LLM; согласие субъекта."),
    ("R-06","Critical","Security","Все Flask-приложения","Нет CSRF-защиты. Атакующий может запустить рассылку/рестарт.","flask-wtf CSRFProtect + токены."),
    ("R-07","Critical","Security","admin/app.py:17, cabinet/app.py:22, tma_api.py:92","Hardcoded fallback secret keys → сессии подделываемы.","Убрать fallback, crash если не задан."),
    ("R-08","High","Infra","glava-cabinet.service:10","Cabinet на 0.0.0.0:5000 — без Nginx, без SSL.","Изменить на 127.0.0.1:5000."),
    ("R-09","High","Infra","docker-compose.yml:8,22","n8n: host network, changeme, порт 5678 наружу.","Bridge network, strong password, Nginx proxy."),
    ("R-10","High","Ops","Отсутствие файлов","Нет бэкапов PostgreSQL, .env, n8n-data.","Cron pg_dump + S3; бэкап .env и n8n-data."),
    ("R-11","High","Security","Все endpoints","Нет rate limiting. Brute-force, DDoS.","flask-limiter + Nginx limit_req_zone."),
    ("R-12","High","Security","db_draft.py:177-183","set_draft_paid без проверки payment_id/user_id.","Добавить user_id + payment_id в WHERE."),
    ("R-13","High","Security","Все nginx-конфиги","Нет HSTS, CSP, X-Frame-Options.","Стандартный блок security headers."),
    ("R-14","High","Privacy","recall_client.py:66","AssemblyAI API key передаётся Recall.ai.","Не передавать ключ; built-in транскрипция."),
    ("R-15","High","Privacy","pipeline_*.py, exports/","Нет retention policy. Данные копятся бесконечно.","Срок хранения + cron cleanup."),
    ("R-16","High","Infra","nginx-glava.conf, nginx-cabinet.conf","Нет SSL-блоков. Если certbot не запущен — HTTP.","Добавить SSL-блоки, certbot auto-renewal."),
    ("R-17","Medium","Security","main.py:537,595,635","Сырые exceptions → в Telegram пользователю.","Generic сообщение; детали в лог."),
    ("R-18","Medium","Security","pipeline_n8n.py:51","n8n webhook без аутентификации.","Basic Auth в заголовках."),
    ("R-19","Medium","Security","main.py:287-293","IDOR: cfg_del без проверки ownership.","Проверка draft.user_id == telegram_id."),
    ("R-20","Medium","Security","admin/blueprints/api.py:26","API key через == (timing attack).","hmac.compare_digest."),
    ("R-21","Medium","Security","config.py:69","ALLOW_ONLINE_WITHOUT_PAYMENT bypass.","Удалить flag или guard в prod."),
    ("R-22","Medium","Privacy","mymeet_client.py:190","API key в query params GET.","Перенести в Authorization header."),
    ("R-23","Medium","Security","admin/app.py, cabinet/app.py","Нет session expiration, cookie flags.","Flask app.config: Secure, SameSite, Lifetime."),
    ("R-24","Medium","Security","tma/index.html:426,437","XSS: download_url и caption без escaping.","escHtml() для всех user-controlled значений."),
    ("R-25","Medium","Ops","admin/","Нет audit log для действий админов.","Middleware логирования в таблицу audit_log."),
    ("R-26","Medium","Security","admin/templates/base.html:7","Tailwind CDN JIT в production.","Собрать Tailwind локально."),
    ("R-27","Medium","Security","payment_adapter.py:93-97","Stub-платёж молча активен без YooKassa.","Raise error в prod."),
    ("R-28","Medium","Security","payment_adapter.py:75","Нет idempotency key для YooKassa.","Добавить idempotence_key=draft_id."),
    ("R-29","Medium","Privacy","main.py:621-636","Пароль plaintext в Telegram-чате.","Задание пароля через веб; удаление сообщения."),
    ("R-30","Low","Privacy","cabinet/app.py:92-96","User enumeration через разные ошибки.","Унифицировать сообщение."),
    ("R-31","Low","Privacy","landing/index.html:8-10","Google Fonts → IP в Google.","Self-host шрифты."),
    ("R-32","Low","Infra","docker-compose.yml:5","n8n:latest — supply chain risk.","Пиннить версию."),
    ("R-33","Low","Ops","Весь проект","Нет CI/CD. Деплой ручной.","GitHub Actions: lint, test, deploy."),
]

PD_FLOW = [
    ("telegram_id", "Telegram", "PostgreSQL, n8n, logs", "n8n workflow"),
    ("username", "Telegram", "PostgreSQL, exports/", "n8n"),
    ("email", "Ввод пользователя", "PostgreSQL (draft_orders)", "ЮKassa (receipt)"),
    ("Пароль кабинета", "Telegram-сообщение", "PostgreSQL (bcrypt)", "Нет (plaintext в истории Telegram)"),
    ("Голосовые записи", "Telegram", "S3, temp-файлы", "AssemblyAI, SpeechKit, MyMeet, Recall.ai"),
    ("Фотографии", "Telegram", "S3", "Anthropic Claude (base64)"),
    ("Транскрипт", "SpeechKit/AssemblyAI", "PostgreSQL, exports/, n8n", "OpenAI (×7+), Anthropic"),
    ("Биография", "OpenAI", "exports/, n8n", "OpenAI (editor), Anthropic, Telegram"),
    ("Имена, родство", "Ввод пользователя", "PostgreSQL (JSONB)", "OpenAI (часть транскрипта)"),
    ("IP-адрес", "HTTP в кабинет/админку", "Nginx access logs", "Нет"),
    ("Данные платежа", "ЮKassa callback", "PostgreSQL", "ЮKassa"),
    ("Записи встреч", "Zoom/Meet/Teams", "Recall.ai/MyMeet серверы", "Recall.ai (US), MyMeet (?)"),
]

RU_RISKS = [
    ("Первичное хранение ПД вне РФ","Critical","ФЗ-152 ст.18 ч.5: PostgreSQL на сервере в Германии."),
    ("Трансграничная передача без DPA","High","Данные → 4+ SaaS в США без уведомления РКН."),
    ("Нет уведомления субъекта","High","Пользователь не информируется о передаче за рубеж."),
    ("Нет согласия на обработку","High","Нет privacy policy, формы согласия."),
    ("Голосовые = биометрия","High","Могут квалифицироваться по ФЗ-152 как биометрические ПД."),
    ("Блокировка IP РКН","Medium","Hetzner IP периодически блокируются."),
    ("Юрисдикционные запросы","Low","Немецкие власти могут запросить данные по GDPR."),
]

QUICK_WINS = [
    ("1","Убрать BOT_TOKEN из payload n8n","pipeline_n8n.py, phase-a.json","2ч"),
    ("2","Файрвол: ufw allow 22,80,443","deploy/deploy.sh","30мин"),
    ("3","Cabinet bind 127.0.0.1:5000","glava-cabinet.service","5мин"),
    ("4","Убрать fallback secret keys","admin/app.py, cabinet/app.py, tma_api.py","30мин"),
    ("5","set_draft_paid + user_id + payment_id","db_draft.py","30мин"),
    ("6","Generic error messages","main.py","30мин"),
    ("7","IDOR fix cfg_del","main.py","30мин"),
    ("8","hmac.compare_digest для API key","admin/blueprints/api.py","5мин"),
    ("9","Guard ALLOW_ONLINE_WITHOUT_PAYMENT","config.py","15мин"),
    ("10","Cookie security flags","admin/app.py, cabinet/app.py","15мин"),
    ("11","Session expiration 8h","admin/app.py, cabinet/app.py","15мин"),
    ("12","Stub payment → error в prod","payment_adapter.py","15мин"),
    ("13","XSS fix escHtml в TMA","tma/index.html","30мин"),
    ("14","Nginx security headers","Все nginx конфиги","1ч"),
    ("15","n8n: убрать changeme, пиннить версию","docker-compose.yml","15мин"),
]

MEDIUM_FIXES = [
    ("16","bcrypt для админ-паролей","admin/app.py","3ч"),
    ("17","CSRF-защита flask-wtf","Все Flask-приложения","4ч"),
    ("18","Rate limiting","Flask + Nginx","3ч"),
    ("19","Systemd: user glava + hardening","Все .service файлы","4ч"),
    ("20","Бэкапы: pg_dump + S3","cron + скрипт","4ч"),
    ("21","n8n bridge network","docker-compose.yml","2ч"),
    ("22","SSL для landing/cabinet","nginx конфиги","2ч"),
    ("23","Audit log для админов","admin/","4ч"),
    ("24","Basic Auth на n8n webhook","pipeline_n8n.py","30мин"),
    ("25","Data retention + cleanup","exports/","4ч"),
]

STRATEGIC = [
    ("31","Разделение контуров RU/EU","PostgreSQL с ПД в РФ (Yandex MDB). VPS EU только для LLM-вызовов."),
    ("32","Privacy Policy и согласие","Юрист → документ ПД, уведомление РКН, кнопка согласия в боте."),
    ("33","DPA с внешними сервисами","Data Processing Agreements: OpenAI, AssemblyAI, Anthropic, Recall.ai."),
    ("34","Data minimization","Псевдонимизация перед отправкой в LLM."),
    ("35","Self-hosted LLM","vLLM/ollama для промежуточных шагов (Fact Checker, Proofreader)."),
    ("36","CI/CD","GitHub Actions: lint, pytest, deploy."),
    ("37","Consent для записи встреч","Уведомление всех участников (Recall.ai) + opt-in."),
]

CHECKED_FILES = [
    "main.py, config.py, db.py, db_draft.py, payment_adapter.py, storage.py, .env.example",
    "admin/app.py, admin/auth.py, admin/db_admin.py, admin/blueprints/{dev,dasha,lena,api}.py",
    "admin/templates/base.html, login.html, dev/dashboard.html, dasha/prompts.html, prompt_edit.html, order_detail.html",
    "cabinet/app.py, cabinet/tma_api.py, cabinet/templates/login.html, tma/index.html",
    "pipeline_transcribe_bio.py, pipeline_assemblyai_bio.py, pipeline_plaud_bio.py",
    "pipeline_mymeet_bio.py, pipeline_recall_bio.py, pipeline_n8n.py",
    "transcribe.py, assemblyai_client.py, recall_client.py, mymeet_client.py",
    "llm_bio.py, biographical_prompt.py, clarifying_questions_prompt.py, typesetter.py",
    "n8n-workflows/phase-a.json, docker/docker-compose.yml",
    "deploy/deploy.sh, deploy/glava.service, glava-cabinet.service, glava-admin.service",
    "deploy/nginx-glava.conf, nginx-cabinet.conf, nginx-glava-cabinet.conf, nginx-tma.conf, nginx-admin.conf",
    "DEPLOY_24_7.md, DEPLOY_TIMEWEB.md, deploy/DEPLOY_GLAVA_FAMILY.md",
    "docs/OPENAI_ACCESS.md, docs/DIARIZATION.md, landing/index.html",
    "scripts/migrate_admin.py, requirements.txt, requirements-dev.txt, requirements-server.txt",
]

TO_VERIFY = [
    ("S3_ENDPOINT_URL в prod .env","Определить страну хранения аудио/фото."),
    ("IP/хостинг VPS 72.56.121.94","Подтвердить страну размещения."),
    ("S3 bucket policy","Публичный ли bucket."),
    ("ADMIN_PASSWORD_* в prod","Не используются ли дефолты."),
    ("certbot + auto-renewal на VPS","certbot certificates + cron."),
    (".env permissions на сервере","ls -la → 600."),
    ("n8n execution history retention","Сколько дней хранятся логи с транскриптами."),
    ("Yandex Cloud IAM policy","Права S3 access key."),
    ("DPA с OpenAI, AssemblyAI, Anthropic, Recall.ai","Есть ли соглашения."),
    ("Уведомление Роскомнадзора","Подано ли уведомление об обработке ПД."),
    ("Согласие пользователя в /start","Есть ли текст согласия."),
    ("SSH-конфигурация VPS","PermitRootLogin, PasswordAuthentication."),
    ("Nginx access/error logs","IP, query strings, logrotate."),
]


def build_pdf():
    has_font = register_fonts()
    ss = build_styles(has_font)
    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title="GLAVA Security Audit Report",
        author="AI Security Reviewer",
    )
    story = []

    # ── title ────────────────────────────────────────────────────────
    story.append(Spacer(1, 12*mm))
    story.append(Paragraph("GLAVA — Аудит безопасности", ss["DocTitle"]))
    story.append(Paragraph("Security · Privacy · Compliance · Infrastructure", ss["DocSubtitle"]))
    story.append(Paragraph("Дата: 15 марта 2026 &nbsp;|&nbsp; Версия: 1.0 &nbsp;|&nbsp; Статус: Draft", ss["DocSubtitle"]))
    story.append(hr())

    # ── 1. Executive Summary ─────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary (ТОП-15 рисков)", ss["H1"]))
    for i, item in enumerate(EXEC_SUMMARY, 1):
        story.append(Paragraph(f"<b>{i}.</b> {item}", ss["BulletCustom"]))

    story.append(PageBreak())

    # ── 2. Таблица рисков ────────────────────────────────────────────
    story.append(Paragraph("2. Таблица рисков", ss["H1"]))
    story.append(Paragraph(
        "33 риска идентифицированы. Critical: 7, High: 9, Medium: 13, Low: 4.",
        ss["Body"]))
    story.append(Spacer(1, 3*mm))
    story.append(make_risk_table(RISKS, ss))

    story.append(PageBreak())

    # ── 3. Data Flow Map ─────────────────────────────────────────────
    story.append(Paragraph("3. Data Flow Map", ss["H1"]))
    story.append(Paragraph(
        "Карта движения персональных данных по системе: откуда приходят, где хранятся, куда передаются.",
        ss["Body"]))
    story.append(Spacer(1, 3*mm))
    story.append(make_simple_table(
        ["Тип данных", "Источник", "Хранение", "Передача во внешние сервисы"],
        PD_FLOW,
        [30*mm, 30*mm, 45*mm, 62*mm],
        ss,
    ))

    story.append(Spacer(1, 8*mm))

    # ── 4. Риски Германия / за пределами РФ ──────────────────────────
    story.append(Paragraph("4. Риски из-за инфраструктуры в Германии / за пределами РФ", ss["H1"]))
    story.append(Paragraph(
        "Документация проекта явно требует размещения VPS в Европе/США (для доступа к OpenAI). "
        "PostgreSQL с персональными данными граждан РФ, транскрипты на диске и n8n SQLite "
        "находятся на том же сервере — за пределами РФ.",
        ss["Body"]))
    story.append(Spacer(1, 3*mm))
    story.append(make_simple_table(
        ["Риск", "Severity", "Описание"],
        RU_RISKS,
        [40*mm, 18*mm, 109*mm],
        ss,
    ))

    story.append(PageBreak())

    # ── 5. План исправления ──────────────────────────────────────────
    story.append(Paragraph("5. План исправления", ss["H1"]))

    story.append(Paragraph("5.1. Quick Wins (1–3 дня)", ss["H2"]))
    story.append(make_simple_table(
        ["#", "Действие", "Файл(ы)", "Effort"],
        QUICK_WINS,
        [8*mm, 65*mm, 60*mm, 20*mm],
        ss,
    ))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("5.2. Medium Fixes (1–2 недели)", ss["H2"]))
    story.append(make_simple_table(
        ["#", "Действие", "Файл(ы)", "Effort"],
        MEDIUM_FIXES,
        [8*mm, 65*mm, 60*mm, 20*mm],
        ss,
    ))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("5.3. Strategic Fixes (месяц+)", ss["H2"]))
    story.append(make_simple_table(
        ["#", "Действие", "Описание"],
        STRATEGIC,
        [8*mm, 50*mm, 109*mm],
        ss,
    ))

    story.append(PageBreak())

    # ── 6. Просмотренные файлы ───────────────────────────────────────
    story.append(Paragraph("6. Просмотренные файлы", ss["H1"]))
    for line in CHECKED_FILES:
        story.append(Paragraph(f"• {line}", ss["BulletCustom"]))

    story.append(Spacer(1, 6*mm))

    # ── 7. Требует дополнительной проверки ───────────────────────────
    story.append(Paragraph("7. Требует дополнительной проверки", ss["H1"]))
    story.append(make_simple_table(
        ["Что проверить", "Зачем"],
        TO_VERIFY,
        [60*mm, 107*mm],
        ss,
    ))

    story.append(Spacer(1, 10*mm))
    story.append(hr())
    story.append(Paragraph(
        "Конец отчёта. Документ сгенерирован автоматически. Не является юридическим заключением.",
        ss["Footer"]))

    doc.build(story)
    print(f"PDF saved: {PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
