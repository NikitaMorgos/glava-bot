# -*- coding: utf-8 -*-
"""Inline клавиатуры для Pre-pay flow."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def kb_intro_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Посмотреть пример", callback_data="intro_example")],
        [InlineKeyboardButton("💰 Узнать стоимость", callback_data="intro_price")],
        [InlineKeyboardButton("🚀 Начать", callback_data="intro_start")],
    ])


def kb_intro_example() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Создать свою книгу", callback_data="intro_start")],
        [InlineKeyboardButton("← Назад", callback_data="intro_main")],
    ])


def kb_intro_price() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать создание", callback_data="intro_start")],
        [InlineKeyboardButton("← Назад", callback_data="intro_main")],
    ])


def kb_config_characters(draft_id: int, has_characters: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ Добавить персонажа", callback_data=f"cfg_add:{draft_id}")],
    ]
    if has_characters:
        buttons.append([InlineKeyboardButton("Продолжить →", callback_data=f"cfg_continue:{draft_id}")])
        buttons.append([InlineKeyboardButton("✏ Изменить список", callback_data=f"cfg_edit:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_config_edit_list(characters: list[dict], draft_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for i, c in enumerate(characters):
        name = c.get("name", "?")
        rel = c.get("relation", "")
        label = f"🗑 {name}" + (f" ({rel})" if rel else "")
        buttons.append([InlineKeyboardButton(label, callback_data=f"cfg_del:{draft_id}:{i}")])
    buttons.append([InlineKeyboardButton("← Назад", callback_data=f"cfg_back:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_email_back(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("← Назад", callback_data=f"email_back:{draft_id}")],
    ])


def kb_order_summary(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Перейти к оплате", callback_data=f"order_pay:{draft_id}")],
        [InlineKeyboardButton("✏ Изменить", callback_data=f"order_edit:{draft_id}")],
        [InlineKeyboardButton("← Назад", callback_data=f"order_back:{draft_id}")],
    ])


def kb_payment(draft_id: int, payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Открыть оплату", url=payment_url)],
        [InlineKeyboardButton("Проверить оплату", callback_data=f"payment_check:{draft_id}")],
        [InlineKeyboardButton("🔄 Начать новый заказ", callback_data=f"payment_new_order:{draft_id}")],
        [InlineKeyboardButton("← Назад", callback_data=f"payment_back:{draft_id}")],
    ])


def kb_resume_draft() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Продолжить оформление", callback_data="resume_continue")],
    ])


def kb_resume_payment(payment_url: str, draft_id: int | None = None) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("Открыть оплату", url=payment_url)],
        [InlineKeyboardButton("Проверить оплату", callback_data="resume_check")],
    ]
    if draft_id is not None:
        buttons.append([InlineKeyboardButton("🔄 Начать новый заказ", callback_data=f"payment_new_order:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_blocked_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Начать", callback_data="intro_start")],
    ])


def kb_online_meeting(has_telemost_link: bool) -> InlineKeyboardMarkup:
    """Клавиатура для записи онлайн-встречи: при наличии TELEMOST_MEETING_LINK — кнопка «Получить ссылку»."""
    buttons = []
    if has_telemost_link:
        buttons.append([InlineKeyboardButton("🔗 Получить ссылку на встречу", callback_data="online_use_telemost")])
    return InlineKeyboardMarkup(buttons) if buttons else None
