"""
Отправка email из кабинета.

Два backend'а:
- SMTPSender — реальная отправка через Яндекс 360 (smtp.yandex.ru:465, SSL).
- LogSender   — пишет письмо в лог (для разработки без SMTP-кред).

Выбирается через переменную окружения CABINET_EMAIL_BACKEND={smtp|log}.
По умолчанию: log (безопасный fallback).

Креды (для smtp):
  CABINET_SMTP_HOST     — обычно smtp.yandex.ru
  CABINET_SMTP_PORT     — 465 (SSL) или 587 (STARTTLS)
  CABINET_SMTP_USER     — полный адрес: hello@glava.family
  CABINET_SMTP_PASSWORD — пароль приложения из Яндекс ID
  CABINET_EMAIL_FROM    — обычно hello@glava.family
  CABINET_EMAIL_FROM_NAME — отображаемое имя, напр. "Glava"
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class EmailSender(ABC):
    """Интерфейс отправки писем."""

    @abstractmethod
    def send(self, to: str, subject: str, text: str, html: str | None = None) -> bool:
        """Отправляет письмо. Возвращает True при успехе."""


class LogSender(EmailSender):
    """Пишет письмо в лог. Для разработки и тестов."""

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> bool:
        logger.warning(
            "📧 [LogSender] EMAIL NOT SENT — would deliver to %s\n"
            "Subject: %s\n"
            "Body:\n%s\n"
            "── end of email ──",
            to,
            subject,
            text,
        )
        return True


class SMTPSender(EmailSender):
    """Отправка через SMTP (Яндекс 360 SSL по умолчанию)."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        from_email: str,
        from_name: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email
        self.from_name = from_name

    def send(self, to: str, subject: str, text: str, html: str | None = None) -> bool:
        msg = EmailMessage()
        msg["Subject"] = subject
        if self.from_name:
            msg["From"] = f"{self.from_name} <{self.from_email}>"
        else:
            msg["From"] = self.from_email
        msg["To"] = to
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")

        try:
            if self.port == 465:
                ctx = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=ctx, timeout=20) as s:
                    s.login(self.user, self.password)
                    s.send_message(msg)
            else:
                # STARTTLS path (587)
                with smtplib.SMTP(self.host, self.port, timeout=20) as s:
                    s.ehlo()
                    s.starttls(context=ssl.create_default_context())
                    s.ehlo()
                    s.login(self.user, self.password)
                    s.send_message(msg)
        except Exception as e:
            logger.error("SMTPSender: не удалось отправить письмо на %s: %s", to, e)
            return False
        logger.info("SMTPSender: письмо отправлено на %s (subject=%s)", to, subject)
        return True


def get_sender() -> EmailSender:
    """
    Возвращает настроенный EmailSender согласно env.
    backend=smtp → SMTPSender (если все креды есть), иначе fallback на LogSender.
    backend=log  → LogSender.
    """
    backend = (os.environ.get("CABINET_EMAIL_BACKEND") or "log").strip().lower()
    if backend != "smtp":
        return LogSender()

    host = os.environ.get("CABINET_SMTP_HOST", "smtp.yandex.ru").strip()
    port = int(os.environ.get("CABINET_SMTP_PORT", "465").strip())
    user = os.environ.get("CABINET_SMTP_USER", "").strip()
    password = os.environ.get("CABINET_SMTP_PASSWORD", "").strip()
    from_email = os.environ.get("CABINET_EMAIL_FROM", user).strip()
    from_name = os.environ.get("CABINET_EMAIL_FROM_NAME", "Glava").strip()

    if not (host and port and user and password and from_email):
        logger.warning(
            "CABINET_EMAIL_BACKEND=smtp, но не все креды заданы — fallback на LogSender. "
            "Нужны: CABINET_SMTP_HOST/PORT/USER/PASSWORD, CABINET_EMAIL_FROM."
        )
        return LogSender()

    return SMTPSender(
        host=host,
        port=port,
        user=user,
        password=password,
        from_email=from_email,
        from_name=from_name,
    )


# ── Шаблоны писем ────────────────────────────────────────────────────────────

MAGIC_LINK_SUBJECT = "Вход в личный кабинет Glava"

MAGIC_LINK_TEMPLATE_TEXT = """Здравствуйте!

Чтобы войти в личный кабинет Glava, нажмите на ссылку:

{link}

Ссылка действительна 30 минут. Если вы её не запрашивали — просто проигнорируйте это письмо.

— Команда Glava
hello@glava.family
"""

MAGIC_LINK_TEMPLATE_HTML = """\
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
             background:#faf8f5;color:#2c2419;line-height:1.6;padding:32px;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;
              padding:36px 32px;border:1px solid #ece5d8;">
    <div style="font-size:20px;font-weight:600;margin-bottom:8px;">Глава.</div>
    <h1 style="font-size:20px;font-weight:600;margin:24px 0 12px;">Вход в личный кабинет</h1>
    <p style="color:#6b5d4d;margin-bottom:28px;">
      Нажмите кнопку ниже, чтобы войти в свой кабинет.
    </p>
    <p style="margin-bottom:28px;">
      <a href="{link}"
         style="display:inline-block;padding:14px 28px;background:#2c2419;color:#fff;
                border-radius:10px;text-decoration:none;font-weight:500;">
        Войти в кабинет
      </a>
    </p>
    <p style="color:#8a8480;font-size:13px;margin-bottom:8px;">
      Ссылка действительна 30 минут. Если вы её не запрашивали — просто проигнорируйте это письмо.
    </p>
    <p style="color:#8a8480;font-size:13px;word-break:break-all;">
      Если кнопка не работает, скопируйте ссылку:<br>
      <span style="color:#5b7a9e;">{link}</span>
    </p>
    <hr style="border:none;border-top:1px solid #ece5d8;margin:28px 0;">
    <p style="color:#8a8480;font-size:12px;">
      Glava — биографические книги о ваших близких<br>
      <a href="mailto:hello@glava.family" style="color:#5b7a9e;">hello@glava.family</a>
    </p>
  </div>
</body>
</html>
"""


def send_magic_link(to_email: str, link: str) -> bool:
    """Отправляет письмо с magic-link. Возвращает True при успехе."""
    sender = get_sender()
    text = MAGIC_LINK_TEMPLATE_TEXT.format(link=link)
    html = MAGIC_LINK_TEMPLATE_HTML.format(link=link)
    return sender.send(to_email, MAGIC_LINK_SUBJECT, text, html)


# ── Уведомления о прогрессе сборки книги ─────────────────────────────────────

def _cabinet_base_url() -> str:
    """URL кабинета для формирования ссылок. По умолчанию — локальный dev."""
    return (os.environ.get("CABINET_BASE_URL") or "http://localhost:5000").rstrip("/")


def _render_notification_html(title: str, intro: str, cta_text: str, cta_url: str, note: str = "") -> str:
    return f"""\
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
             background:#faf8f5;color:#2c2419;line-height:1.6;padding:32px;">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;
              padding:36px 32px;border:1px solid #ece5d8;">
    <div style="font-size:20px;font-weight:600;margin-bottom:8px;">Глава.</div>
    <h1 style="font-size:20px;font-weight:600;margin:24px 0 12px;">{title}</h1>
    <p style="color:#6b5d4d;margin-bottom:28px;">{intro}</p>
    <p style="margin-bottom:28px;">
      <a href="{cta_url}"
         style="display:inline-block;padding:14px 28px;background:#2c2419;color:#fff;
                border-radius:10px;text-decoration:none;font-weight:500;">
        {cta_text}
      </a>
    </p>
    {f'<p style="color:#8a8480;font-size:13px;margin-bottom:8px;">{note}</p>' if note else ''}
    <hr style="border:none;border-top:1px solid #ece5d8;margin:28px 0;">
    <p style="color:#8a8480;font-size:12px;">
      Glava — биографические книги о ваших близких<br>
      <a href="mailto:hello@glava.family" style="color:#5b7a9e;">hello@glava.family</a>
    </p>
  </div>
</body>
</html>
"""


def send_questions_ready(to_email: str, project_id: int, hero_name: str | None = None) -> bool:
    """Уведомление клиенту: готовы уточняющие вопросы."""
    subject = "Готовы уточняющие вопросы"
    who = f" о {hero_name}" if hero_name else ""
    url = f"{_cabinet_base_url()}/projects/{project_id}"
    intro = (
        f"Мы обработали первые интервью{who} и подготовили список уточняющих вопросов — "
        f"тем, которые стоит раскрыть подробнее. Загляните в кабинет: посмотрите вопросы, "
        f"при желании догрузите второе интервью с ответами и запустите сборку книги."
    )
    text = (
        f"Здравствуйте!\n\n{intro}\n\n"
        f"Открыть проект в кабинете: {url}\n\n"
        f"— Команда Glava\nhello@glava.family\n"
    )
    html = _render_notification_html(
        title=f"Уточняющие вопросы готовы",
        intro=intro,
        cta_text="Открыть проект",
        cta_url=url,
    )
    return get_sender().send(to_email, subject, text, html)


def send_book_ready(
    to_email: str, project_id: int, hero_name: str | None = None, version: int | None = None
) -> bool:
    """Уведомление клиенту: книга собрана."""
    subject = "Книга готова"
    who = f" о {hero_name}" if hero_name else ""
    ver = f" (версия {version})" if version else ""
    url = f"{_cabinet_base_url()}/projects/{project_id}/book"
    intro = (
        f"Мы собрали книгу{who}{ver}. Откройте кабинет, чтобы посмотреть результат, "
        f"скачать PDF или отредактировать текст перед печатью."
    )
    text = (
        f"Здравствуйте!\n\n{intro}\n\n"
        f"Открыть книгу: {url}\n\n"
        f"— Команда Glava\nhello@glava.family\n"
    )
    html = _render_notification_html(
        title="Книга готова",
        intro=intro,
        cta_text="Открыть книгу",
        cta_url=url,
    )
    return get_sender().send(to_email, subject, text, html)
