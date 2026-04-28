# -*- coding: utf-8 -*-
"""Аналитические запросы для CCO-агента. Читает из общей БД GLAVA."""
import logging
from datetime import datetime

import db

logger = logging.getLogger(__name__)


def get_funnel_summary() -> dict:
    """Воронка: количество клиентов на каждом этапе bot_state."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT bot_state, COUNT(*) AS cnt
                FROM draft_orders
                WHERE status != 'cancelled'
                GROUP BY bot_state
                ORDER BY cnt DESC
            """)
            return {r[0] or "unknown": r[1] for r in cur.fetchall()}


def get_weekly_revenue(days: int = 7) -> dict:
    """Выручка за последние N дней."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) AS paid_count,
                    COALESCE(SUM(total_price - COALESCE(discount_amount, 0)), 0) AS revenue,
                    COALESCE(AVG(total_price - COALESCE(discount_amount, 0)), 0) AS avg_check
                FROM draft_orders
                WHERE status = 'paid'
                  AND updated_at > NOW() - INTERVAL '%s days'
            """, (days,))
            r = cur.fetchone()
            return {
                "paid_count": r[0],
                "revenue_kopecks": r[1],
                "revenue_rub": round(r[1] / 100, 2) if r[1] else 0,
                "avg_check_rub": round(r[2] / 100, 2) if r[2] else 0,
            }


def get_registrations(days: int = 7) -> int:
    """Новые регистрации за N дней."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '%s days'",
                (days,),
            )
            return cur.fetchone()[0]


def get_books_delivered(days: int = 7) -> dict:
    """Книги доставленные за N дней."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*), COUNT(DISTINCT telegram_id)
                FROM book_versions
                WHERE created_at > NOW() - INTERVAL '%s days'
            """, (days,))
            r = cur.fetchone()
            return {"versions": r[0], "unique_clients": r[1]}


def get_pipeline_performance(days: int = 7) -> dict:
    """Статистика пайплайна за N дней."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'done') AS done,
                    COUNT(*) FILTER (WHERE status = 'error') AS errors,
                    COUNT(*) FILTER (WHERE status IN ('pending', 'running')) AS in_progress,
                    AVG(EXTRACT(EPOCH FROM (finished_at - started_at)) / 3600)
                        FILTER (WHERE status = 'done' AND finished_at IS NOT NULL) AS avg_hours
                FROM pipeline_jobs
                WHERE started_at > NOW() - INTERVAL '%s days'
            """, (days,))
            r = cur.fetchone()
            return {
                "done": r[0] or 0,
                "errors": r[1] or 0,
                "in_progress": r[2] or 0,
                "avg_hours": round(r[3], 1) if r[3] else None,
            }


def get_stuck_clients() -> list[dict]:
    """Клиенты, которые оплатили, но не загрузили материалы > 48ч."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.username, u.telegram_id, d.bot_state, d.updated_at,
                       (SELECT COUNT(*) FROM voice_messages vm WHERE vm.user_id = u.id) AS voice_cnt,
                       (SELECT COUNT(*) FROM photos p WHERE p.user_id = u.id) AS photo_cnt
                FROM draft_orders d
                JOIN users u ON u.id = d.user_id
                WHERE d.status = 'paid'
                  AND d.bot_state IN ('paid', 'narrators_setup', 'collecting_interview_1')
                  AND d.updated_at < NOW() - INTERVAL '48 hours'
                ORDER BY d.updated_at ASC
            """)
            result = []
            for r in cur.fetchall():
                if r[4] == 0 and r[5] == 0:
                    result.append({
                        "username": r[0] or str(r[1]),
                        "telegram_id": r[1],
                        "bot_state": r[2],
                        "last_activity": r[3].isoformat() if r[3] else None,
                    })
            return result


def get_inactive_after_delivery() -> list[dict]:
    """Клиенты, получившие книгу > 5 дней назад без реакции."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.username, u.telegram_id, d.bot_state, bv.created_at AS book_at
                FROM draft_orders d
                JOIN users u ON u.id = d.user_id
                JOIN book_versions bv ON bv.telegram_id = u.telegram_id
                WHERE d.bot_state = 'book_ready'
                  AND bv.created_at < NOW() - INTERVAL '5 days'
                ORDER BY bv.created_at ASC
            """)
            return [
                {
                    "username": r[0] or str(r[1]),
                    "telegram_id": r[1],
                    "book_delivered": r[3].isoformat() if r[3] else None,
                }
                for r in cur.fetchall()
            ]


def get_promo_effectiveness() -> list[dict]:
    """Эффективность промо-кодов."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pc.code, pc.type, pc.discount_value, pc.used_count, pc.max_uses,
                       pc.is_active, pc.expires_at
                FROM promo_codes pc
                ORDER BY pc.used_count DESC
                LIMIT 10
            """)
            return [
                {
                    "code": r[0],
                    "type": r[1],
                    "discount": float(r[2]) if r[2] else 0,
                    "used": r[3],
                    "max_uses": r[4],
                    "active": r[5],
                }
                for r in cur.fetchall()
            ]


def get_total_clients() -> dict:
    """Общее количество клиентов и заказов."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM draft_orders WHERE status = 'paid'")
            paid_orders = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT telegram_id) FROM book_versions")
            clients_with_books = cur.fetchone()[0]
            return {
                "total_users": total_users,
                "paid_orders": paid_orders,
                "clients_with_books": clients_with_books,
            }


def get_revision_stats() -> dict:
    """Статистика правок."""
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    AVG(revision_count) AS avg_revisions,
                    MAX(revision_count) AS max_revisions,
                    COUNT(*) FILTER (WHERE revision_count > 0) AS clients_with_revisions,
                    COUNT(*) FILTER (WHERE bot_state = 'finalized') AS finalized
                FROM draft_orders
                WHERE status = 'paid'
            """)
            r = cur.fetchone()
            return {
                "avg_revisions": round(r[0], 1) if r[0] else 0,
                "max_revisions": r[1] or 0,
                "clients_with_revisions": r[2] or 0,
                "finalized": r[3] or 0,
            }


def collect_all_metrics(days: int = 7) -> str:
    """Собирает все метрики в текстовый блок для промпта."""
    try:
        funnel = get_funnel_summary()
        revenue = get_weekly_revenue(days)
        regs = get_registrations(days)
        books = get_books_delivered(days)
        pipeline = get_pipeline_performance(days)
        stuck = get_stuck_clients()
        inactive = get_inactive_after_delivery()
        promos = get_promo_effectiveness()
        totals = get_total_clients()
        revisions = get_revision_stats()
    except Exception as e:
        logger.exception("Error collecting metrics: %s", e)
        return f"[Ошибка сбора метрик: {e}]"

    lines = [
        f"=== МЕТРИКИ (последние {days} дней) ===",
        "",
        f"--- Общие ---",
        f"Всего пользователей: {totals['total_users']}",
        f"Оплаченных заказов: {totals['paid_orders']}",
        f"Клиентов с книгами: {totals['clients_with_books']}",
        "",
        f"--- Регистрации ---",
        f"Новых за {days} дней: {regs}",
        "",
        f"--- Воронка (bot_state) ---",
    ]
    for state, cnt in funnel.items():
        lines.append(f"  {state}: {cnt}")

    lines += [
        "",
        f"--- Выручка за {days} дней ---",
        f"Оплат: {revenue['paid_count']}",
        f"Выручка: {revenue['revenue_rub']} ₽",
        f"Средний чек: {revenue['avg_check_rub']} ₽",
        "",
        f"--- Книги за {days} дней ---",
        f"Версий доставлено: {books['versions']}",
        f"Уникальных клиентов: {books['unique_clients']}",
        "",
        f"--- Пайплайн за {days} дней ---",
        f"Готово: {pipeline['done']}",
        f"Ошибки: {pipeline['errors']}",
        f"В процессе: {pipeline['in_progress']}",
        f"Среднее время: {pipeline['avg_hours']} ч" if pipeline['avg_hours'] else "Среднее время: нет данных",
        "",
        f"--- Правки ---",
        f"Среднее кол-во правок: {revisions['avg_revisions']}",
        f"Клиентов с правками: {revisions['clients_with_revisions']}",
        f"Финализировано: {revisions['finalized']}",
        "",
        f"--- Промо-коды (топ-10) ---",
    ]
    if promos:
        for p in promos:
            status = "активен" if p["active"] else "неактивен"
            lines.append(f"  {p['code']}: {p['used']}/{p['max_uses'] or '∞'} использований, скидка {p['discount']}%, {status}")
    else:
        lines.append("  Нет данных")

    lines.append("")
    lines.append(f"--- Застрявшие клиенты (оплатили, не загрузили > 48ч) ---")
    if stuck:
        for s in stuck:
            lines.append(f"  @{s['username']}: состояние {s['bot_state']}, последняя активность {s['last_activity']}")
    else:
        lines.append("  Нет застрявших")

    lines.append("")
    lines.append(f"--- Неактивные после доставки книги (> 5 дней) ---")
    if inactive:
        for i in inactive:
            lines.append(f"  @{i['username']}: книга доставлена {i['book_delivered']}")
    else:
        lines.append("  Нет неактивных")

    return "\n".join(lines)
