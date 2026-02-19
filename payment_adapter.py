"""
Платежный адаптер — интерфейс для провайдеров.
ТЗ Pre-pay: create_payment, check_payment.
Реализация — заглушка (возвращает тестовую ссылку).
"""

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


def create_payment(draft_order: dict) -> dict[str, str | None]:
    """
    Создаёт платёж. Возвращает {payment_id, payment_url}.
    draft_order: id, total_price, currency, email, characters
    """
    # Заглушка: возвращаем тестовые данные
    payment_id = f"test_{uuid.uuid4().hex[:12]}"
    payment_url = "https://example.com/pay/" + payment_id
    logger.info("create_payment (stub): draft_id=%s, payment_id=%s", draft_order.get("id"), payment_id)
    return {"payment_id": payment_id, "payment_url": payment_url}


def check_payment(payment_id: str) -> str:
    """
    Проверяет статус платежа.
    Возвращает: 'paid' | 'pending' | 'failed' | 'cancelled'
    """
    # Заглушка: всегда pending
    logger.info("check_payment (stub): %s -> pending", payment_id)
    return "pending"
