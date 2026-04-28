"""
Клиент SMSimple (https://smsimple.ru/) — триггерные и сервисные SMS по HTTP API.

Документация: https://smsimple.ru/api-http
Переменные: SMSIMPLE_USER, SMSIMPLE_PASSWORD, SMSIMPLE_ORIGIN_ID (из кабинета SMSimple).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests

import config

logger = logging.getLogger(__name__)

SMSIMPLE_DEFAULT_BASE = "https://smsimple.ru"

# Успех: «Сообщение #12345 отослано.» — номер выдаётся до фактической доставки оператору.
_RE_MESSAGE_ID = re.compile(r"Сообщение\s*#(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class SMSendResult:
    ok: bool
    message_id: int | None
    raw: str
    error: str | None = None


@dataclass(frozen=True)
class SMBalanceResult:
    ok: bool
    raw: str
    error: str | None = None


def smsimple_credentials_ok() -> bool:
    """Логин и пароль заданы (без проверки сети)."""
    u = getattr(config, "SMSIMPLE_USER", "") or ""
    p = getattr(config, "SMSIMPLE_PASSWORD", "") or ""
    return bool(str(u).strip() and str(p).strip())


def smsimple_configured() -> bool:
    """Готова отправка с подписью по умолчанию из SMSIMPLE_ORIGIN_ID."""
    oid = getattr(config, "SMSIMPLE_ORIGIN_ID", "") or ""
    return smsimple_credentials_ok() and bool(str(oid).strip())


def normalize_ru_phone(phone: str) -> str:
    """
    Приводит номер к виду 79XXXXXXXXX (цифры, без +).
    Пустая/некорректная строка — как есть по цифрам, может не пройти валидацию на стороне SMSimple.
    """
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "7" + digits
    return digits


def _base_url() -> str:
    return (getattr(config, "SMSIMPLE_BASE_URL", "") or SMSIMPLE_DEFAULT_BASE).rstrip("/")


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "GLAVA-bot/1.0 (+smsimple)"})
    return s


def get_balance(timeout: float = 15.0) -> SMBalanceResult:
    """
    Баланс в личном кабинете (ответ — текст от SMSimple).
    """
    if not smsimple_credentials_ok():
        return SMBalanceResult(ok=False, raw="", error="SMSimple не настроен (SMSIMPLE_USER/PASSWORD)")
    params = {
        "user": config.SMSIMPLE_USER,
        "pass": config.SMSIMPLE_PASSWORD,
    }
    url = urljoin(_base_url() + "/", "http_balance.php")
    try:
        r = _session().get(url, params=params, timeout=timeout)
        r.raise_for_status()
        text = (r.text or "").strip()
        return SMBalanceResult(ok=True, raw=text, error=None)
    except requests.RequestException as e:
        logger.warning("SMSimple get_balance: %s", e)
        return SMBalanceResult(ok=False, raw="", error=str(e))


def send_sms(
    phone: str,
    message: str,
    *,
    origin_id: int | None = None,
    timeout: float = 30.0,
) -> SMSendResult:
    """
    Отправка одной SMS. phone — в любом удобном виде; нормализуется под 79XXXXXXXXX.
    origin_id — подпись отправителя; по умолчанию из SMSIMPLE_ORIGIN_ID.
    """
    if not smsimple_credentials_ok():
        return SMSendResult(
            ok=False,
            message_id=None,
            raw="",
            error="SMSimple не настроен: задайте SMSIMPLE_USER и SMSIMPLE_PASSWORD",
        )
    oid_src = origin_id
    if oid_src is None:
        raw_oid = str(getattr(config, "SMSIMPLE_ORIGIN_ID", "") or "").strip()
        if not raw_oid:
            return SMSendResult(
                ok=False,
                message_id=None,
                raw="",
                error="Не задана подпись отправителя: SMSIMPLE_ORIGIN_ID или аргумент origin_id",
            )
        oid_src = int(raw_oid)
    oid = int(oid_src)
    normalized = normalize_ru_phone(phone)
    params: dict[str, Any] = {
        "user": config.SMSIMPLE_USER,
        "pass": config.SMSIMPLE_PASSWORD,
        "or_id": oid,
        "phone": normalized,
        "message": message,
    }
    url = urljoin(_base_url() + "/", "http_send.php")
    try:
        r = _session().get(url, params=params, timeout=timeout)
        r.raise_for_status()
        text = (r.text or "").strip()
    except requests.RequestException as e:
        logger.warning("SMSimple send_sms: %s", e)
        return SMSendResult(ok=False, message_id=None, raw="", error=str(e))

    if "Ошибка при отправке:" in text or text.startswith("Ошибка"):
        err = text.replace("Ошибка при отправке:", "").strip() or text
        return SMSendResult(ok=False, message_id=None, raw=text, error=err)

    m = _RE_MESSAGE_ID.search(text)
    if m:
        mid = int(m.group(1))
        return SMSendResult(ok=True, message_id=mid, raw=text, error=None)

    # Неожиданный формат ответа
    logger.warning("SMSimple send_sms: неизвестный ответ: %s", text[:500])
    return SMSendResult(
        ok=False,
        message_id=None,
        raw=text,
        error="Не удалось разобрать ответ SMSimple",
    )


def check_delivery(
    message_id: int,
    *,
    detailed: bool = False,
    timeout: float = 15.0,
) -> str:
    """
    Статус доставки (сырой текст от SMSimple).
    detailed=True — параметр version=3 в API (подробнее статусы).
    """
    if not smsimple_credentials_ok():
        return ""
    params: dict[str, Any] = {
        "user": config.SMSIMPLE_USER,
        "pass": config.SMSIMPLE_PASSWORD,
        "message_id": message_id,
    }
    if detailed:
        params["version"] = 3
    url = urljoin(_base_url() + "/", "http_check.php")
    try:
        r = _session().get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return (r.text or "").strip()
    except requests.RequestException as e:
        logger.warning("SMSimple check_delivery: %s", e)
        return ""
