"""
Платежный адаптер — интерфейс для провайдеров.
ТЗ Pre-pay: create_payment, check_payment.
Поддержка: ЮKassa (YooKassa).
"""

import logging
import uuid
from typing import Any

import config

logger = logging.getLogger(__name__)

def _return_url() -> str:
    return getattr(config, "PAYMENT_RETURN_URL", "") or "https://t.me/glava_voice_bot"


def _yookassa_available() -> bool:
    shop_id = getattr(config, "YOOKASSA_SHOP_ID", "") or ""
    secret = getattr(config, "YOOKASSA_SECRET_KEY", "") or ""
    return bool(shop_id and secret)


def create_payment(draft_order: dict) -> dict[str, str | None]:
    """
    Создаёт платёж. Возвращает {payment_id, payment_url}.
    draft_order: id, total_price, currency, email, characters
    """
    if not _yookassa_available():
        logger.warning(
            "create_payment: ЮKassa недоступна (YOOKASSA_SHOP_ID=%s, SECRET=%s)",
            "есть" if getattr(config, "YOOKASSA_SHOP_ID", "") else "нет",
            "есть" if getattr(config, "YOOKASSA_SECRET_KEY", "") else "нет",
        )
    if _yookassa_available():
        try:
            from yookassa import Configuration, Payment

            Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_KEY)

            draft_id = draft_order.get("id", 0)
            total_kopecks = int(draft_order.get("total_price") or 0)
            total_rub = max(1, round(total_kopecks / 100, 2))  # минимум 1 руб
            email = (draft_order.get("email") or "").strip()
            description = f"GLAVA — заказ #{draft_id}"

            payload: dict[str, Any] = {
                "amount": {"value": f"{total_rub:.2f}", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": _return_url(),
                },
                "capture": True,
                "description": description,
                "metadata": {"draft_id": str(draft_id)},
            }

            if email:
                payload["receipt"] = {
                    "customer": {"email": email},
                    "items": [
                        {
                            "description": "Семейная книга GLAVA",
                            "quantity": "1",
                            "amount": {"value": f"{total_rub:.2f}", "currency": "RUB"},
                            "vat_code": 1,
                            "payment_mode": "full_payment",
                            "payment_subject": "service",
                        }
                    ],
                    "tax_system_code": 1,
                }

            payment = Payment.create(payload)
            payment_id = getattr(payment, "id", None) or str(payment.get("id", ""))
            confirmation = getattr(payment, "confirmation", None) or payment.get("confirmation", {})
            payment_url = (
                getattr(confirmation, "confirmation_url", None)
                or confirmation.get("confirmation_url")
                or ""
            )
            if payment_id and payment_url:
                logger.info("create_payment (yookassa): draft_id=%s, payment_id=%s", draft_id, payment_id)
                return {"payment_id": payment_id, "payment_url": payment_url, "provider": "yookassa"}
            logger.warning("create_payment (yookassa): пустой ответ API")
            return {}
        except Exception as e:
            logger.exception("create_payment (yookassa): %s", e)
            # Не подставляем заглушку — пусть пользователь увидит ошибку
            raise

    # Заглушка только если ЮKassa не настроена
    payment_id = f"test_{uuid.uuid4().hex[:12]}"
    payment_url = "https://example.com/pay/" + payment_id
    logger.info("create_payment (stub): draft_id=%s, payment_id=%s", draft_order.get("id"), payment_id)
    return {"payment_id": payment_id, "payment_url": payment_url, "provider": "stub"}


def check_payment(payment_id: str) -> str:
    """
    Проверяет статус платежа.
    Возвращает: 'paid' | 'pending' | 'failed' | 'cancelled'
    """
    if _yookassa_available() and payment_id and not payment_id.startswith("test_"):
        try:
            from yookassa import Configuration, Payment

            Configuration.configure(config.YOOKASSA_SHOP_ID, config.YOOKASSA_SECRET_KEY)
            payment = Payment.find_one(payment_id)
            status = getattr(payment, "status", None) or payment.get("status", "")

            if status == "succeeded":
                return "paid"
            if status in ("pending", "waiting_for_capture"):
                return "pending"
            if status == "canceled":
                return "cancelled"
            return "failed"
        except Exception as e:
            logger.warning("check_payment (yookassa): %s — %s", payment_id, e)

    # Заглушка
    logger.info("check_payment (stub): %s -> pending", payment_id)
    return "pending"
