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


def kb_order_summary(draft_id: int, promo_applied: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("💳 Перейти к оплате", callback_data=f"order_pay:{draft_id}")],
    ]
    if promo_applied:
        buttons.append([InlineKeyboardButton("❌ Убрать промо-код", callback_data=f"promo_remove:{draft_id}")])
    else:
        buttons.append([InlineKeyboardButton("🎟 Ввести промо-код", callback_data=f"promo_enter:{draft_id}")])
    buttons.append([InlineKeyboardButton("✏ Изменить", callback_data=f"order_edit:{draft_id}")])
    buttons.append([InlineKeyboardButton("← Назад", callback_data=f"order_back:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_promo_cancel(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("← Отмена", callback_data=f"promo_cancel:{draft_id}")],
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


# ── Клавиатуры bot scenario v2 ───────────────────────────────────────────────

def kb_narrators(draft_id: int, narrators: list[dict], has_narrators: bool) -> InlineKeyboardMarkup:
    """Экран 6.1: список нарраторов + добавить/удалить/продолжить."""
    buttons = []
    for n in narrators:
        label = f"🗑 {n['name']} ({n.get('relation', '')})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"narrator_del:{draft_id}:{n['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить рассказчика", callback_data=f"narrator_add:{draft_id}")])
    if has_narrators:
        buttons.append([InlineKeyboardButton("Продолжить →", callback_data=f"narrator_continue:{draft_id}")])
    buttons.append([InlineKeyboardButton("← Назад", callback_data="intro_main")])
    return InlineKeyboardMarkup(buttons)


def kb_interview_guide(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 7.1: подготовка к интервью."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Показать вопросы в чате", callback_data=f"guide_questions:{draft_id}")],
        [InlineKeyboardButton("📄 Скачать вопросы PDF", callback_data=f"guide_pdf:{draft_id}")],
        [InlineKeyboardButton("📞 Получить ссылку для звонка", callback_data=f"guide_call_link:{draft_id}")],
        [InlineKeyboardButton("⬆️ Загрузить материалы", callback_data=f"upload_start:{draft_id}")],
        [InlineKeyboardButton("← Назад", callback_data=f"narrator_back:{draft_id}")],
    ])


def kb_interview_questions(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 7.2: список вопросов."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬆️ Загрузить материалы", callback_data=f"upload_start:{draft_id}")],
        [InlineKeyboardButton("← Назад", callback_data=f"guide_back:{draft_id}")],
    ])


def kb_narrator_select(narrators: list[dict], draft_id: int) -> InlineKeyboardMarkup:
    """Экран 8.1: выбор нарратора для загрузки."""
    buttons = []
    for n in narrators:
        label = f"{n['name']} — {n.get('relation', '')}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"upload_narrator:{draft_id}:{n['id']}")])
    buttons.append([InlineKeyboardButton("← Назад", callback_data=f"guide_back:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_upload_audio(draft_id: int, has_files: bool) -> InlineKeyboardMarkup:
    """Экран 8.2: загрузка аудио."""
    buttons = []
    if has_files:
        buttons.append([InlineKeyboardButton("➕ Добавить ещё файл", callback_data=f"upload_more:{draft_id}")])
        buttons.append([InlineKeyboardButton("Далее →", callback_data=f"upload_to_photos:{draft_id}")])
    buttons.append([InlineKeyboardButton("← Назад", callback_data=f"upload_start:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_upload_photos(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 8.3: выбор типа фото."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Фотографии персонажа", callback_data=f"photo_type_photo:{draft_id}")],
        [InlineKeyboardButton("📄 Фото документов", callback_data=f"photo_type_doc:{draft_id}")],
        [InlineKeyboardButton("Добавить позже", callback_data=f"upload_summary:{draft_id}")],
        [InlineKeyboardButton("Далее →", callback_data=f"upload_summary:{draft_id}")],
    ])


def kb_upload_summary(draft_id: int, has_more_narrators: bool) -> InlineKeyboardMarkup:
    """Экран 8.4: итог загрузки."""
    buttons = []
    if has_more_narrators:
        buttons.append([InlineKeyboardButton("🎤 Загрузить от другого рассказчика", callback_data=f"upload_start:{draft_id}")])
    buttons.append([InlineKeyboardButton("✅ Все интервью загружены", callback_data=f"upload_done:{draft_id}")])
    buttons.append([InlineKeyboardButton("➕ Добавить ещё файлы", callback_data=f"upload_more:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_interview_result(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 8.6: уточняющие вопросы готовы."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Перейти к этапу 2", callback_data=f"interview2_start:{draft_id}")],
        [InlineKeyboardButton("⏭ Пропустить, собрать книгу", callback_data=f"assemble_book:{draft_id}")],
    ])


def kb_interview2_confirm(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 9.2: подтверждение второго интервью."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да, собирайте книгу", callback_data=f"assemble_book:{draft_id}")],
        [InlineKeyboardButton("➕ Добавить ещё", callback_data=f"interview2_start:{draft_id}")],
    ])


def kb_book_ready(draft_id: int, revision_count: int, max_revisions: int = 3) -> InlineKeyboardMarkup:
    """Экран 10.2 / 11.3: книга готова."""
    buttons = [
        [InlineKeyboardButton("📄 Открыть PDF", callback_data=f"book_get_pdf:{draft_id}")],
    ]
    if revision_count < max_revisions:
        buttons.append([InlineKeyboardButton("💬 Оставить комментарий", callback_data=f"revision_start:{draft_id}")])
    buttons.append([InlineKeyboardButton("✅ Всё отлично, завершить", callback_data=f"book_finalize:{draft_id}")])
    if revision_count > 0:
        buttons.append([InlineKeyboardButton("😞 Не нравится результат", callback_data=f"refund_start:{draft_id}")])
    buttons.append([InlineKeyboardButton("📜 Версии книги", callback_data=f"versions_list:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_revision_comment(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 11.1: ввод комментария к правке."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Отправить комментарий", callback_data=f"revision_submit:{draft_id}")],
        [InlineKeyboardButton("← Назад к книге", callback_data=f"book_ready_back:{draft_id}")],
    ])


def kb_versions_list(versions: list[dict], draft_id: int) -> InlineKeyboardMarkup:
    """Экран 12.1: список версий книги."""
    buttons = []
    for v in versions:
        ver = v.get("version", "?")
        date = str(v.get("created_at", ""))[:10]
        buttons.append([
            InlineKeyboardButton(f"📄 v{ver} · {date}", callback_data=f"version_open:{draft_id}:{ver}"),
            InlineKeyboardButton("↩️ Откатить", callback_data=f"version_rollback:{draft_id}:{ver}"),
        ])
    buttons.append([InlineKeyboardButton("← Назад", callback_data=f"book_ready_back:{draft_id}")])
    return InlineKeyboardMarkup(buttons)


def kb_version_rollback_confirm(draft_id: int, version: int) -> InlineKeyboardMarkup:
    """Экран 12.2: подтверждение отката."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да, откатить", callback_data=f"version_rollback_confirm:{draft_id}:{version}")],
        [InlineKeyboardButton("Отмена", callback_data=f"versions_list:{draft_id}")],
    ])


def kb_finalize_confirm(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 13.1: подтверждение завершения."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Завершить книгу", callback_data=f"finalize_confirm:{draft_id}")],
        [InlineKeyboardButton("← Назад", callback_data=f"book_ready_back:{draft_id}")],
    ])


def kb_finalized(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 14.1: книга завершена."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Скачать PDF", callback_data=f"book_get_pdf:{draft_id}")],
        [InlineKeyboardButton("🖨 Заказать печать", callback_data=f"print_info:{draft_id}")],
        [InlineKeyboardButton("📤 Поделиться", callback_data=f"book_share:{draft_id}")],
    ])


def kb_print_soon(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 14.2: печать скоро."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Уведомить меня", callback_data=f"print_waitlist:{draft_id}")],
        [InlineKeyboardButton("← Назад", callback_data=f"finalize_done:{draft_id}")],
    ])


def kb_refund_reason(draft_id: int) -> InlineKeyboardMarkup:
    """Экран 15.1: причина возврата."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Запросить возврат", callback_data=f"refund_submit:{draft_id}")],
        [InlineKeyboardButton("← Передумал, назад к книге", callback_data=f"book_ready_back:{draft_id}")],
    ])
