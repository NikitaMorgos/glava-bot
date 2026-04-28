"""
Проверка интеграции SMSimple: баланс и тестовая отправка SMS.

Из корня репозитория:
  python scripts/smsimple_test_send.py --balance
  python scripts/smsimple_test_send.py +79161234567
  python scripts/smsimple_test_send.py 89161234567 --message "Тест GLAVA"

Нужны в .env: SMSIMPLE_USER, SMSIMPLE_PASSWORD, SMSIMPLE_ORIGIN_ID
(или origin_id только в командной строке: --origin-id 50101).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from smsimple_client import (  # noqa: E402
    get_balance,
    normalize_ru_phone,
    send_sms,
    smsimple_credentials_ok,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Тест SMSimple (баланс / отправка SMS)")
    p.add_argument("phone", nargs="?", help="Номер получателя (любой формат)")
    p.add_argument(
        "--balance",
        action="store_true",
        help="Только запросить баланс (без отправки)",
    )
    p.add_argument(
        "--message",
        default="Тест GLAVA: SMSimple подключён.",
        help="Текст SMS (по умолчанию короткий тестовый)",
    )
    p.add_argument(
        "--origin-id",
        type=int,
        default=None,
        help="or_id подписи (если не задан SMSIMPLE_ORIGIN_ID в .env)",
    )
    args = p.parse_args()

    if not smsimple_credentials_ok():
        print(
            "Ошибка: в .env не заданы SMSIMPLE_USER и SMSIMPLE_PASSWORD.\n"
            "Скопируйте из кабинета https://smsimple.ru/ после регистрации.",
            file=sys.stderr,
        )
        return 1

    if args.balance or not args.phone:
        b = get_balance()
        if not b.ok:
            print(f"Баланс: ошибка — {b.error}", file=sys.stderr)
            return 1
        print("Баланс (ответ SMSimple):")
        print(b.raw)
        if not args.phone:
            print(
                "\nЧтобы отправить тестовую SMS, укажите номер:\n"
                "  python scripts/smsimple_test_send.py +79XXXXXXXXX",
            )
        return 0

    oid = args.origin_id
    if oid is None and not (getattr(config, "SMSIMPLE_ORIGIN_ID", "") or "").strip():
        print(
            "Ошибка: задайте SMSIMPLE_ORIGIN_ID в .env или передайте --origin-id",
            file=sys.stderr,
        )
        return 1

    phone_norm = normalize_ru_phone(args.phone)
    print(f"Отправка на {phone_norm} (нормализовано из «{args.phone}»)...")
    r = send_sms(args.phone, args.message, origin_id=oid)
    print(f"Сырой ответ: {r.raw!r}")
    if r.ok:
        print(f"OK: message_id={r.message_id}")
        return 0
    print(f"Ошибка: {r.error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
