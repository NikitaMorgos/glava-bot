# -*- coding: utf-8 -*-
"""
GLAVA — Telegram-бот. Pre-pay flow: навигация до оплаты.

Запуск: python main.py
Перед первым запуском: psql -d your_db -f sql/add_draft_orders.sql
"""

import html
import logging
import os
import re
import tempfile
from pathlib import Path

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, MenuButtonCommands, Update, WebAppInfo
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes

TMA_URL = "https://app.glava.family"

import config
import db
import storage
import db_draft
from payment_adapter import create_payment, check_payment
import bot_messages
from prepay.keyboards import (
    kb_intro_main, kb_intro_example, kb_intro_price,
    kb_config_characters, kb_config_edit_list, kb_email_back,
    kb_order_summary, kb_payment, kb_resume_draft, kb_resume_payment, kb_blocked_start,
    kb_online_meeting,
    # v2
    kb_narrators, kb_interview_guide, kb_interview_questions, kb_narrator_select,
    kb_upload_audio, kb_upload_photos, kb_upload_summary, kb_interview_result,
    kb_interview2_confirm, kb_book_ready, kb_revision_comment, kb_versions_list,
    kb_version_rollback_confirm, kb_finalize_confirm, kb_finalized, kb_print_soon,
    kb_refund_reason,
)

MAX_REVISIONS = 3

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".ogg", ".mp3", ".m4a", ".wav", ".opus", ".oga"}
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _format_characters(characters: list[dict]) -> str:
    if not characters:
        return "(пусто)"
    return "\n".join(f"• {c.get('name', '?')} ({c.get('relation', '')})" for c in characters)


def _format_price(kopecks: int) -> str:
    return str(kopecks // 100)


def _online_meeting_provider() -> tuple[str, str]:
    """
    Возвращает (provider, api_key) для записи онлайн-встреч.
    Приоритет: recall → mymeet → meeting_bot (self-hosted Playwright).
    """
    recall_key = getattr(config, "RECALL_API_KEY", "") or ""
    mymeet_key = getattr(config, "MYMEET_API_KEY", "") or ""
    if recall_key:
        return "recall", recall_key
    if mymeet_key:
        return "mymeet", mymeet_key
    # meeting_bot — self-hosted (Linux + pulseaudio + playwright). Включить: MEETING_BOT_ENABLED=true
    if os.name == "posix" and getattr(config, "MEETING_BOT_ENABLED", False):
        return "meeting_bot", ""
    return "", ""


async def _start_online_meeting_recording(
    link: str,
    provider: str,
    api_key: str,
    telegram_id: int = 0,
    username: str | None = None,
) -> str | None:
    """
    Запускает запись встречи через Recall.ai, MyMeet или meeting_bot.
    Возвращает bot_id / meeting_id или None.
    """
    if provider == "recall":
        from recall_client import create_bot
        assemblyai_key = getattr(config, "ASSEMBLYAI_API_KEY", "") or ""
        region = getattr(config, "RECALL_REGION", "us-east-1") or "us-east-1"
        return create_bot(
            meeting_url=link,
            api_key=api_key,
            region=region,
            assemblyai_api_key=assemblyai_key,
        )
    if provider == "mymeet":
        from mymeet_client import record_meeting
        return record_meeting(
            link, api_key,
            title="GLAVA интервью",
            template_name="research-interview",
        )
    if provider == "meeting_bot":
        from meeting_bot import record_meeting_background
        record_meeting_background(link, telegram_id, username)
        return "meeting_bot"
    return None


def _run_online_meeting_background(
    bot_id: str, provider: str, telegram_id: int, username: str | None
) -> None:
    """Запускает фоновую обработку онлайн-встречи через нужный провайдер."""
    if provider == "meeting_bot":
        return  # Уже запущено в _start_online_meeting_recording
    if provider == "recall":
        from pipeline_recall_bio import run_online_meeting_background
        run_online_meeting_background(bot_id, telegram_id, username)
    elif provider == "mymeet":
        from pipeline_mymeet_bio import run_online_meeting_background
        run_online_meeting_background(bot_id, telegram_id, username)


def _run_transcription_pipeline(
    voice_id: int, storage_key: str, telegram_id: int, username: str | None
) -> None:
    """Выбирает пайплайн по TRANSCRIBER и ключам: recall → mymeet → plaud → assemblyai → speechkit."""
    transcriber = getattr(config, "TRANSCRIBER", None)
    if transcriber == "mymeet" and config.MYMEET_API_KEY:
        from pipeline_mymeet_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username)
    elif transcriber == "plaud" and config.PLAUD_API_TOKEN:
        from pipeline_plaud_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username)
    elif transcriber == "assemblyai" and config.ASSEMBLYAI_API_KEY:
        from pipeline_assemblyai_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username)
    elif transcriber == "speechkit" and config.YANDEX_API_KEY:
        from pipeline_transcribe_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username, use_diarization=True)
    elif config.PLAUD_API_TOKEN:
        from pipeline_plaud_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username)
    elif config.MYMEET_API_KEY:
        from pipeline_mymeet_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username)
    elif config.ASSEMBLYAI_API_KEY:
        from pipeline_assemblyai_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username)
    elif config.YANDEX_API_KEY:
        from pipeline_transcribe_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username, use_diarization=True)
    else:
        from pipeline_transcribe_bio import run_pipeline_background
        run_pipeline_background(voice_id, storage_key, telegram_id, username, use_diarization=True)


def _user_has_paid(telegram_id: int) -> bool:
    """Проверяет, оплатил ли пользователь заказ. Пайплайн (голосовые/фото) запускается только после оплаты."""
    draft = db_draft.get_draft_by_telegram_id(telegram_id)
    return draft is not None and draft.get("status") == "paid"


def _user_book_delivered(telegram_id: int) -> bool:
    """Проверяет, доставлена ли книга v1 или vN (Phase B активна).

    ВАЖНО: всегда вызывать вместе с _is_phase_a_active() —
    если пользователь начал новое интервью, Phase B НЕ должна перехватывать его материалы.
    """
    try:
        import requests as _req
        admin_url = os.environ.get("ADMIN_API_BASE_URL", "http://127.0.0.1:5001/api")
        r = _req.get(f"{admin_url}/state/{telegram_id}", timeout=3)
        if r.status_code == 200:
            state = r.json().get("state", "")
            return state in ("delivered_v1", "delivered_vN", "revising_phase_b")
    except Exception:
        pass
    return False


# Состояния v2-черновика, при которых идёт сбор материалов для Phase A
_PHASE_A_BOT_STATES = frozenset({
    "no_project",            # только оплатил, интервью ещё не начато
    "narrators_setup",
    "collecting_interview_1",
    "processing_interview_1",
    "awaiting_interview_2",
    "collecting_interview_2",
    "assembling",
})

# Состояния, при которых книга уже готова и пользователь работает в Phase B
_PHASE_B_BOT_STATES = frozenset({
    "book_ready", "book_updated",
    "revision_1", "revision_2", "revision_3",
    "revision_processing", "finalized",
})


def _is_phase_a_active(telegram_id: int) -> bool:
    """Возвращает True, если текущий черновик находится в фазе сбора материалов (Phase A).

    Используется как защита: голосовые и фото НЕ должны попадать в Phase B,
    пока пользователь проходит интервью для нового заказа.
    """
    draft = db_draft.get_draft_by_telegram_id(telegram_id)
    if not draft:
        return False
    if draft.get("status") != "paid":
        return False
    bot_state = (draft.get("bot_state") or "no_project")
    return bot_state in _PHASE_A_BOT_STATES


def _get_user_character_name(telegram_id: int) -> str:
    """Берёт имя персонажа из draft."""
    try:
        draft = db_draft.get_draft_by_telegram_id(telegram_id)
        if draft:
            chars = draft.get("characters") or []
            if chars:
                return chars[0].get("name", "")
    except Exception:
        pass
    return ""


def _get_user_draft_id(telegram_id: int) -> int:
    try:
        draft = db_draft.get_draft_by_telegram_id(telegram_id)
        return draft["id"] if draft else 0
    except Exception:
        return 0


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """START — маршрутизация по bot_state (spec v2 экран 0.1)."""
    user = update.effective_user
    if not user:
        return

    try:
        await context.bot.set_chat_menu_button(
            chat_id=update.effective_chat.id,
            menu_button=MenuButtonWebApp(text="📱 Кабинет", web_app=WebAppInfo(url=TMA_URL)),
        )
    except Exception as e:
        logger.debug("set_chat_menu_button: %s", e)

    context.user_data.clear()

    # Маршрутизация по состоянию
    draft = db_draft.get_draft_by_telegram_id(user.id)
    bot_state = (draft.get("bot_state") if draft else None) or "no_project"
    draft_status = (draft.get("status") if draft else None) or "no_project"

    # Книга готова → экран 10.2
    if bot_state in ("book_ready", "book_updated", "revision_1", "revision_2", "revision_3"):
        await _show_book_ready(update.message, draft)
        return

    # Обработка правки → покажем экран ожидания
    if bot_state == "revision_processing":
        await update.message.reply_text(bot_messages.get_message("revision_processing"))
        return

    # Финализирован
    if bot_state == "finalized":
        draft_id = draft["id"] if draft else 0
        revision_count = db_draft.get_revision_count(draft_id) if draft_id else 0
        await update.message.reply_text(
            bot_messages.get_message("finalized"),
            reply_markup=kb_finalized(draft_id),
        )
        return

    # Оплачен → нарраторы или текущий шаг после оплаты
    if draft_status == "paid" or bot_state in (
        "narrators_setup", "collecting_interview_1", "processing_interview_1",
        "awaiting_interview_2", "collecting_interview_2", "assembling",
    ):
        if bot_state in ("collecting_interview_1", "processing_interview_1"):
            await update.message.reply_text("Продолжайте загружать материалы. Используйте кнопки ниже.")
            return
        if bot_state == "awaiting_interview_2" and draft:
            await update.message.reply_text(
                bot_messages.get_message("interview_questions_ready"),
                reply_markup=kb_interview_result(draft["id"]),
            )
            return
        if bot_state == "assembling":
            await update.message.reply_text(bot_messages.get_message("assembling"))
            return
        # narrators_setup или paid → экран нарраторов
        if draft:
            await _show_narrators_screen(update.message, draft)
        return

    # Есть draft → продолжить оформление
    if draft and draft_status in ("draft",):
        chars = draft.get("characters") or []
        if chars:
            if not draft.get("email"):
                await _show_email_input(update, context, draft["id"])
            else:
                await _show_order_summary(update, context, draft)
        else:
            # Начать с экрана персонажа
            context.user_data["prepay_awaiting"] = "character_name"
            context.user_data["prepay_draft_id"] = draft["id"]
            await update.message.reply_text(bot_messages.get_message("character_name"))
        return

    # payment_pending → ожидание оплаты
    if draft_status == "payment_pending":
        await update.message.reply_text(
            bot_messages.get_message("payment_wait"),
            reply_markup=kb_payment(draft["id"], draft.get("payment_url") or "https://glava.family"),
        )
        return

    # no_project → экран 1.1
    markup = kb_intro_main()
    btn_label = "📱 Мой кабинет" if _user_has_paid(user.id) else "📱 Открыть кабинет"
    markup = InlineKeyboardMarkup(
        list(markup.inline_keyboard) + [[
            InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=TMA_URL))
        ]]
    )
    await update.message.reply_text(bot_messages.get_message("intro_main"), reply_markup=markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user:
        return
    data = query.data or ""

    # Scenario v2 callbacks
    if await _handle_v2_callback(query, data, user, context):
        return

    if data == "intro_main":
        await query.edit_message_text(bot_messages.get_message("intro_main"), reply_markup=kb_intro_main())
        return

    if data == "intro_example":
        logger.info("event: example_viewed")
        await query.edit_message_text(bot_messages.get_message("intro_example"), reply_markup=kb_intro_example())
        return

    if data == "intro_price":
        logger.info("event: price_viewed")
        await query.edit_message_text(bot_messages.get_message("intro_price"), reply_markup=kb_intro_price())
        return

    if data == "intro_start":
        draft = db_draft.get_or_create_draft(user.id, user.username)
        if not draft:
            return
        logger.info("event: draft_created")
        status = draft.get("status", "")
        if status == "payment_pending":
            await query.edit_message_text(
                bot_messages.get_message("payment_wait"),
                reply_markup=kb_payment(draft["id"], draft.get("payment_url") or "https://example.com"),
            )
            return
        if status == "paid":
            await query.edit_message_text("Оплата прошла! Можете отправлять голосовые и фото. /list")
            return
        chars = draft.get("characters") or []
        if not chars:
            # По сценарию: при 0 персонажах — сразу ввод имени без кнопок (без экрана конфига)
            context.user_data["prepay_awaiting"] = "character_name"
            context.user_data["prepay_draft_id"] = draft["id"]
            await query.edit_message_text("Введите имя персонажа:", reply_markup=InlineKeyboardMarkup([]))
            return
        if not draft.get("email"):
            await _show_email_input_callback(query, context, draft["id"])
        else:
            await _show_order_summary_callback(query, context, draft)
        return

    if data == "resume_continue":
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft:
            chars = draft.get("characters") or []
            if not draft.get("email"):
                await _show_email_input_callback(query, context, draft["id"])
            else:
                await _show_order_summary_callback(query, context, draft)
        return

    if data == "resume_check":
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft and draft.get("status") == "payment_pending" and draft.get("payment_id"):
            status = check_payment(draft["payment_id"])
            logger.info("event: payment_status_checked status=%s", status)
            if status == "paid":
                db_draft.set_draft_paid(draft["id"])
                await query.edit_message_text("Оплата прошла! Теперь можете отправлять голосовые и фото. /list")
            else:
                await query.answer(bot_messages.get_message("payment_still_pending"), show_alert=True)
        return

    if data.startswith("cfg_add:"):
        draft_id = int(data.split(":")[1])
        context.user_data["prepay_awaiting"] = "character_name"
        context.user_data["prepay_draft_id"] = draft_id
        await query.edit_message_text("Введите имя персонажа:")
        return

    if data.startswith("cfg_continue:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if not draft or draft["id"] != draft_id:
            await query.answer("Заказ не найден.", show_alert=True)
            return
        chars = draft.get("characters") or []
        if len(chars) < 1:
            await query.answer("Добавьте хотя бы одного персонажа.", show_alert=True)
            return
        await _show_email_input_callback(query, context, draft_id)
        return

    if data.startswith("cfg_edit:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if not draft or draft["id"] != draft_id:
            return
        chars = draft.get("characters") or []
        if not chars:
            await _show_config_characters_callback(query, context, user.id)
            return
        await query.edit_message_text(
            "Выберите персонажа для удаления:",
            reply_markup=kb_config_edit_list(chars, draft_id),
        )
        return

    if data.startswith("cfg_del:"):
        parts = data.split(":")
        draft_id = int(parts[1])
        idx = int(parts[2])
        db_draft.remove_character(draft_id, idx)
        logger.info("event: character_deleted")
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft:
            chars = draft.get("characters") or []
            if not chars:
                await _show_config_characters_callback(query, context, user.id)
            else:
                await query.edit_message_text(
                    "Выберите для удаления:",
                    reply_markup=kb_config_edit_list(chars, draft_id),
                )
        return

    if data.startswith("cfg_back:"):
        draft_id = int(data.split(":")[1])
        await _show_config_characters_callback(query, context, user.id)
        return

    if data.startswith("email_back:"):
        draft_id = int(data.split(":")[1])
        await _show_config_characters_callback(query, context, user.id)
        return

    if data.startswith("order_pay:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if not draft or draft["id"] != draft_id or draft.get("status") != "draft":
            await query.answer("Заказ не найден.", show_alert=True)
            return
        try:
            import asyncio
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: create_payment(draft))
        except Exception as e:
            logger.exception("create_payment error: %s", e)
            await query.answer("Ошибка создания платежа. Попробуйте позже.", show_alert=True)
            return
        payment_id = result.get("payment_id")
        payment_url = result.get("payment_url")
        provider = result.get("provider", "stub")
        if payment_id and payment_url:
            db_draft.set_draft_payment_pending(draft_id, payment_id, payment_url, provider)
            logger.info("event: payment_created draft_id=%s", draft_id)
            await query.edit_message_text(
                bot_messages.get_message("payment_init", payment_url=payment_url),
                reply_markup=kb_payment(draft_id, payment_url),
            )
        else:
            await query.answer("Не удалось создать платёж. Проверьте настройки ЮKassa.", show_alert=True)
        return

    if data.startswith("order_edit:"):
        draft_id = int(data.split(":")[1])
        await _show_config_characters_callback(query, context, user.id)
        return

    if data.startswith("order_back:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft:
            await _show_email_input_callback(query, context, draft_id)
        return

    if data.startswith("payment_check:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if not draft or draft["id"] != draft_id:
            return
        if draft.get("payment_id"):
            status = check_payment(draft["payment_id"])
            logger.info("event: payment_status_checked status=%s", status)
            if status == "paid":
                db_draft.set_draft_paid(draft_id)
                await query.edit_message_text("Оплата прошла! Можете отправлять голосовые и фото. /list")
            else:
                await query.answer(bot_messages.get_message("payment_still_pending"), show_alert=True)
        return

    if data.startswith("payment_new_order:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft and draft["id"] == draft_id:
            db_draft.cancel_draft(draft_id)
        new_draft = db_draft.get_or_create_draft(user.id, user.username)
        if new_draft:
            await _show_config_characters_callback(query, context, user.id)
        return

    if data.startswith("payment_back:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft:
            await _show_order_summary_callback(query, context, draft)
        return

    if data == "online_use_telemost":
        context.user_data.pop("awaiting_meeting_link", None)
        link = getattr(config, "TELEMOST_MEETING_LINK", "") or ""
        provider, api_key = _online_meeting_provider()
        if not link or not provider:
            await query.answer("Ссылка на встречу не настроена.", show_alert=True)
            return
        bot_id = await _start_online_meeting_recording(
            link, provider, api_key, telegram_id=user.id, username=user.username
        )
        if bot_id:
            _run_online_meeting_background(bot_id, provider, user.id, user.username)
            await query.edit_message_text(
                f"{link}\n\n{bot_messages.get_message('online_meeting_telemost_sent')}",
            )
        else:
            await query.answer(bot_messages.get_message("online_meeting_error"), show_alert=True)
        return


async def _show_config_characters(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    draft = db_draft.get_or_create_draft(telegram_id, update.effective_user and update.effective_user.username)
    if not draft:
        return
    chars = draft.get("characters") or []
    msg = bot_messages.get_message("config_characters")
    if chars:
        msg = bot_messages.get_message("config_characters_list", characters=_format_characters(chars))
    await update.message.reply_text(msg, reply_markup=kb_config_characters(draft["id"], len(chars) >= 1))


async def _show_config_characters_callback(query, context, telegram_id: int) -> None:
    draft = db_draft.get_or_create_draft(telegram_id, None)
    if not draft:
        return
    chars = draft.get("characters") or []
    msg = bot_messages.get_message("config_characters")
    if chars:
        msg = bot_messages.get_message("config_characters_list", characters=_format_characters(chars))
    await query.edit_message_text(msg, reply_markup=kb_config_characters(draft["id"], len(chars) >= 1))


async def _show_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE, draft_id: int) -> None:
    await update.message.reply_text(bot_messages.get_message("email_input"), reply_markup=kb_email_back(draft_id))


async def _show_email_input_callback(query, context, draft_id: int) -> None:
    context.user_data.pop("prepay_awaiting", None)
    context.user_data.pop("prepay_char_name", None)
    context.user_data["prepay_awaiting"] = "email"
    context.user_data["prepay_draft_id"] = draft_id
    await query.edit_message_text(bot_messages.get_message("email_input"), reply_markup=kb_email_back(draft_id))


async def _show_order_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, draft: dict) -> None:
    chars = draft.get("characters") or []
    total = _format_price(draft.get("total_price", 0))
    email = draft.get("email") or ""
    msg = bot_messages.get_message("order_summary", characters=_format_characters(chars), total=total, email=email)
    await update.message.reply_text(msg, reply_markup=kb_order_summary(draft["id"]))


async def _show_order_summary_callback(query, context, draft: dict) -> None:
    chars = draft.get("characters") or []
    total = _format_price(draft.get("total_price", 0))
    email = draft.get("email") or ""
    msg = bot_messages.get_message("order_summary", characters=_format_characters(chars), total=total, email=email)
    await query.edit_message_text(msg, reply_markup=kb_order_summary(draft["id"]))


async def _handle_prepay_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user) -> bool:
    """Обработка текста для prepay. Возвращает True если обработано."""
    awaiting = context.user_data.get("prepay_awaiting")
    draft_id = context.user_data.get("prepay_draft_id")

    if awaiting == "character_name":
        context.user_data["prepay_char_name"] = text
        context.user_data["prepay_awaiting"] = "character_relation"
        await update.message.reply_text("Введите родство (например: мама, дедушка, бабушка):")
        return True

    if awaiting == "character_relation":
        name = context.user_data.pop("prepay_char_name", "")
        context.user_data.pop("prepay_awaiting", None)
        if draft_id and name:
            db_draft.add_character(draft_id, name, text)
            logger.info("event: character_added name=%s", name)
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft:
            await _show_config_characters(update, context, user.id)
        return True

    if awaiting == "email":
        if not EMAIL_RE.match(text):
            await update.message.reply_text(bot_messages.get_message("email_error"), reply_markup=kb_email_back(draft_id or 0))
            return True
        if draft_id:
            db_draft.update_draft_email(draft_id, text)
            logger.info("event: email_submitted")
            context.user_data.pop("prepay_awaiting", None)
            context.user_data.pop("prepay_draft_id", None)
            draft = db_draft.get_draft_by_telegram_id(user.id)
            if draft:
                await _show_order_summary(update, context, draft)
        return True

    return False


async def handle_blocked_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Голосовые/фото/файлы до оплаты."""
    await update.message.reply_text(bot_messages.get_message("blocked_media"), reply_markup=kb_blocked_start())


async def _save_audio_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    suffix: str,
    duration: int | None,
) -> None:
    user = update.message.from_user
    if not user:
        return
    try:
        db_user = db.get_or_create_user(user.id, user.username)
        tg_file = await context.bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        await tg_file.download_to_drive(tmp_path)
        try:
            storage_key = storage.upload_file(tmp_path, db_user["id"])
            voice = db.save_voice_message(
                user_id=db_user["id"],
                telegram_file_id=file_id,
                storage_key=storage_key,
                duration=duration,
            )
            # Phase B только если книга доставлена И нет активного интервью (Phase A)
            if _user_book_delivered(user.id) and not _is_phase_a_active(user.id):
                await update.message.reply_text(
                    "🎙 Аудио получено. Транскрибируем и обновляем книгу — это займёт несколько минут."
                )
                # Phase B: передаём storage_key напрямую; n8n Phase B сам транскрибирует
                if voice:
                    from pipeline_n8n import trigger_phase_b_background
                    trigger_phase_b_background(
                        telegram_id=user.id,
                        input_type="voice",
                        content=storage_key,
                        character_name=_get_user_character_name(user.id),
                        draft_id=_get_user_draft_id(user.id),
                        username=user.username or "",
                    )
            else:
                await update.message.reply_text("Аудио сохранено.")
                if voice:
                    _run_transcription_pipeline(voice["id"], storage_key, user.id, user.username)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.exception("Ошибка сохранения аудио")
        await update.message.reply_text(f"Ошибка: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _user_has_paid(update.effective_user.id if update.effective_user else 0):
        await _save_audio_file(update, context, update.message.voice.file_id, ".ogg", update.message.voice.duration)
    else:
        await handle_blocked_media(update, context)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _user_has_paid(update.effective_user.id if update.effective_user else 0):
        await handle_blocked_media(update, context)
        return
    ext = Path(update.message.audio.file_name or "").suffix or ".mp3"
    if ext.lower() not in AUDIO_EXTENSIONS:
        ext = ".mp3"
    await _save_audio_file(
        update, context,
        update.message.audio.file_id, ext,
        update.message.audio.duration,
    )


async def handle_audio_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _user_has_paid(update.effective_user.id if update.effective_user else 0):
        await handle_blocked_media(update, context)
        return
    name = (update.message.document.file_name or "").lower()
    ext = Path(name).suffix
    if ext not in AUDIO_EXTENSIONS:
        await update.message.reply_text("Принимаю только аудио: .ogg, .mp3, .m4a, .wav, .opus")
        return
    await _save_audio_file(update, context, update.message.document.file_id, ext, None)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # update.message может быть None при редактировании постов/каналов
    if not update.message:
        return
    if not _user_has_paid(update.effective_user.id if update.effective_user else 0):
        await handle_blocked_media(update, context)
        return
    user = update.message.from_user
    if not user:
        return
    try:
        db_user = db.get_or_create_user(user.id, user.username)
        photo = update.message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        await photo_file.download_to_drive(tmp_path)
        try:
            storage_key = storage.upload_file(tmp_path, db_user["id"])
            # Определяем тип фото из v2 user_data
            photo_type = context.user_data.get("v2_photo_type", "photo")
            db.save_photo(db_user["id"], photo.file_id, storage_key, photo_type=photo_type)
            type_label = "документа" if photo_type == "document" else "персонажа"
            accepted_msg = bot_messages.get_message("upload_photo_accepted", photo_type=type_label)
            await update.message.reply_text(accepted_msg)
            # Phase B только если книга доставлена И нет активного интервью (Phase A)
            if _user_book_delivered(user.id) and not _is_phase_a_active(user.id):
                from pipeline_n8n import trigger_phase_b_background
                trigger_phase_b_background(
                    telegram_id=user.id,
                    input_type="photo_caption",
                    content=storage_key,
                    character_name=_get_user_character_name(user.id),
                    draft_id=_get_user_draft_id(user.id),
                    username=user.username or "",
                )
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception as e:
        logger.exception("Ошибка сохранения фото")
        await update.message.reply_text(f"Ошибка: {e}")


async def handle_caption_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return
    if context.user_data.pop("awaiting_meeting_link", None):
        if not text.startswith("http"):
            await update.message.reply_text(bot_messages.get_message("online_meeting_bad_link"))
            return
        provider, api_key = _online_meeting_provider()
        if not provider:
            await update.message.reply_text("Запись онлайн-встреч временно недоступна.")
            return
        bot_id = await _start_online_meeting_recording(
            text, provider, api_key, telegram_id=user.id, username=user.username
        )
        if bot_id:
            _run_online_meeting_background(bot_id, provider, user.id, user.username)
            await update.message.reply_text(bot_messages.get_message("online_meeting_link_sent"))
        else:
            await update.message.reply_text(bot_messages.get_message("online_meeting_error"))
        return

    if context.user_data.pop("awaiting_cabinet_password", None):
        if len(text) < 6:
            await update.message.reply_text("Пароль от 6 символов. /cabinet")
            return
        try:
            import bcrypt
            # bcrypt limit 72 bytes
            pwd_bytes = text.encode("utf-8", errors="replace")[:72]
            hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode("ascii")
            db_user = db.get_or_create_user(user.id, user.username)
            db.set_web_password(db_user["id"], hashed)
            await update.message.reply_text("Пароль сохранён. Вход: cabinet.glava.family")
        except Exception as e:
            logger.exception("Ошибка сохранения пароля кабинета")
            await update.message.reply_text(f"Ошибка: {e}. Попробуй ещё раз /cabinet")
        return
    # ── v2: нарраторы ──────────────────────────────────────────────────────────
    v2_awaiting = context.user_data.get("v2_awaiting")
    v2_draft_id = context.user_data.get("v2_draft_id")

    if v2_awaiting == "narrator_name":
        context.user_data["v2_narrator_name"] = text
        context.user_data["v2_awaiting"] = "narrator_relation"
        draft = db_draft.get_draft_by_telegram_id(user.id)
        char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft and draft.get("characters") else "персонажа"
        await update.message.reply_text(
            bot_messages.get_message("narrator_relation", name=text, character_name=char_name)
        )
        return

    if v2_awaiting == "narrator_relation":
        name = context.user_data.pop("v2_narrator_name", "")
        context.user_data.pop("v2_awaiting", None)
        if v2_draft_id and name:
            narrators = db_draft.add_narrator(v2_draft_id, name, text)
            draft = db_draft.get_draft_by_telegram_id(user.id)
            char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft and draft.get("characters") else "персонажа"
            msg_text = bot_messages.get_message("narrators_list", narrators_list=_format_narrators(narrators))
            await update.message.reply_text(msg_text, reply_markup=kb_narrators(v2_draft_id, narrators, True))
        return

    # ── v2: ревизия с debounce ──────────────────────────────────────────────────
    if v2_awaiting == "revision_text" and v2_draft_id:
        # Сохраняем/дополняем pending_revision с debounce
        existing, _ = db_draft.get_pending_revision(v2_draft_id)
        combined = f"{existing}\n{text}" if existing else text
        db_draft.set_pending_revision(v2_draft_id, combined, deadline_minutes=3)
        await update.message.reply_text(
            bot_messages.get_message("revision_debounce"),
            reply_markup=kb_revision_comment(v2_draft_id),
        )
        return

    # ── v2: причина возврата ───────────────────────────────────────────────────
    if v2_awaiting == "refund_reason" and v2_draft_id:
        if len(text) < 10:
            await update.message.reply_text("Опишите подробнее (минимум 10 символов).")
            return
        context.user_data["v2_refund_reason"] = text
        context.user_data.pop("v2_awaiting", None)
        await update.message.reply_text(
            "Причина принята. Нажмите кнопку ниже для отправки заявки.",
            reply_markup=kb_refund_reason(v2_draft_id),
        )
        return

    pending = db.get_pending_photo(user.id)
    if pending:
        db.update_photo_caption(pending["id"], text)
        await update.message.reply_text("Подпись сохранена.")
        # Phase B только если книга доставлена И нет активного интервью
        if _user_book_delivered(user.id) and not _is_phase_a_active(user.id):
            from pipeline_n8n import trigger_phase_b_background
            trigger_phase_b_background(
                telegram_id=user.id,
                input_type="photo_caption",
                content=text,
                character_name=_get_user_character_name(user.id),
                draft_id=_get_user_draft_id(user.id),
                username=user.username or "",
            )
    elif await _handle_prepay_text(update, context, text, user):
        pass
    elif _user_book_delivered(user.id) and not _is_phase_a_active(user.id):
        # Книга доставлена, нет активного интервью → правка → debounce Phase B
        draft_id = _get_user_draft_id(user.id)
        if draft_id:
            existing, _ = db_draft.get_pending_revision(draft_id)
            combined = f"{existing}\n{text}" if existing else text
            db_draft.set_pending_revision(draft_id, combined, deadline_minutes=3)
            await update.message.reply_text(
                bot_messages.get_message("revision_debounce"),
                reply_markup=kb_revision_comment(draft_id),
            )
        else:
            from pipeline_n8n import trigger_phase_b_background
            await update.message.reply_text("📝 Получили вашу правку. Обновляем книгу…")
            trigger_phase_b_background(
                telegram_id=user.id,
                input_type="text",
                content=text,
                character_name=_get_user_character_name(user.id),
                draft_id=0,
                username=user.username or "",
            )
    else:
        await update.message.reply_text("Используйте кнопки меню или /start")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    try:
        voices = db.get_user_voice_messages(user.id, config.LIST_LIMIT)
        photos = db.get_user_photos(user.id, 15)
    except Exception as e:
        logger.exception("Ошибка /list")
        await update.message.reply_text(f"Ошибка: {e}")
        return
    if not voices and not photos:
        await update.message.reply_text("Пока ничего нет. Отправь голосовое или фото после оплаты.")
        return
    parts = []
    if voices:
        parts.append("Голосовые:\n")
        for i, v in enumerate(voices, 1):
            url = storage.get_presigned_download_url(v["storage_key"])
            dur = f" ({v['duration']} сек)" if v.get("duration") else ""
            created = v["created_at"].strftime("%d.%m %H:%M") if v.get("created_at") else ""
            parts.append(f"{i}. {created}{dur} — <a href=\"{url}\">скачать</a>")
    if photos:
        parts.append("\nФото:\n")
        for i, p in enumerate(photos, 1):
            url = storage.get_presigned_download_url(p["storage_key"])
            cap = html.escape((p.get("caption") or "")[:80])
            parts.append(f"{i}. {cap} — <a href=\"{url}\">открыть</a>")
    text = "\n".join(parts)
    if len(text) > 4000:
        text = text[:3990] + "..."
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_cabinet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    context.user_data["awaiting_cabinet_password"] = True
    login_hint = f"@{user.username}" if user and user.username else "ID"
    await update.message.reply_text(
        f"Отправь пароль для входа в кабинет (от 6 символов). Логин: {login_hint}"
    )


async def cmd_online(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Записать онлайн-встречу: пользователь отправляет ссылку или получает ссылку из телемоста."""
    try:
        if not update.message:
            return
        user = update.effective_user
        if not user:
            await update.message.reply_text("Не удалось определить пользователя.")
            return
        allow_without_payment = getattr(config, "ALLOW_ONLINE_WITHOUT_PAYMENT", False)
        if not allow_without_payment and not _user_has_paid(user.id):
            await update.message.reply_text(
                "Запись онлайн-встреч доступна после оплаты. Оформите заказ через /start.",
                reply_markup=kb_blocked_start(),
            )
            return
        provider, _ = _online_meeting_provider()
        if not provider:
            await update.message.reply_text("Запись онлайн-встреч временно недоступна.")
            return
        context.user_data["awaiting_meeting_link"] = True
        has_telemost = bool(getattr(config, "TELEMOST_MEETING_LINK", "") or "")
        reply_markup = kb_online_meeting(has_telemost)
        await update.message.reply_text(
            bot_messages.get_message("online_meeting_intro"),
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.exception("cmd_online: %s", e)
        if update.message:
            await update.message.reply_text("Ошибка. Попробуйте позже или напишите в поддержку.")


# ═══════════════════════════════════════════════════════════════════════════
# Helpers — bot scenario v2
# ═══════════════════════════════════════════════════════════════════════════

def _format_narrators(narrators: list[dict]) -> str:
    if not narrators:
        return "(нет)"
    return "\n".join(f"• {n['name']} ({n.get('relation', '')})" for n in narrators)


async def _show_narrators_screen(message, draft: dict) -> None:
    """Экран 6.1: кто будет рассказывать."""
    narrators = draft.get("narrators") or []
    char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft.get("characters") else "персонажа"
    if narrators:
        text = bot_messages.get_message("narrators_list", narrators_list=_format_narrators(narrators))
    else:
        text = bot_messages.get_message("narrators_setup", character_name=char_name)
    await message.reply_text(text, reply_markup=kb_narrators(draft["id"], narrators, bool(narrators)))


async def _show_book_ready(message, draft: dict | None) -> None:
    """Экран 10.2 / 11.3: книга готова."""
    if not draft:
        await message.reply_text("Книга готова. Используйте /start для навигации.")
        return
    draft_id = draft["id"]
    revision_count = db_draft.get_revision_count(draft_id)
    text = bot_messages.get_message("book_ready")
    await message.reply_text(text, reply_markup=kb_book_ready(draft_id, revision_count, MAX_REVISIONS))


# ═══════════════════════════════════════════════════════════════════════════
# Callback handlers — bot scenario v2
# ═══════════════════════════════════════════════════════════════════════════

async def _handle_v2_callback(query, data: str, user, context) -> bool:
    """Обработка callback_data для scenario v2. Возвращает True если обработано."""

    # ── Нарраторы (6.1) ──────────────────────────────────────────────────────
    if data.startswith("narrator_add:"):
        draft_id = int(data.split(":")[1])
        context.user_data["v2_awaiting"] = "narrator_name"
        context.user_data["v2_draft_id"] = draft_id
        draft = db_draft.get_draft_by_telegram_id(user.id)
        char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft and draft.get("characters") else "персонажа"
        await query.edit_message_text(f"Введите имя рассказчика:")
        return True

    if data.startswith("narrator_del:"):
        parts = data.split(":")
        draft_id, narrator_id = int(parts[1]), parts[2]
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft and draft["id"] == draft_id:
            db_draft.remove_narrator(draft_id, narrator_id)
            draft = db_draft.get_draft_by_telegram_id(user.id)
            narrators = draft.get("narrators") or []
            char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft.get("characters") else "персонажа"
            text = bot_messages.get_message("narrators_list", narrators_list=_format_narrators(narrators)) if narrators else bot_messages.get_message("narrators_setup", character_name=char_name)
            await query.edit_message_text(text, reply_markup=kb_narrators(draft_id, narrators, bool(narrators)))
        return True

    if data.startswith("narrator_continue:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        narrators = (draft.get("narrators") or []) if draft else []
        if not narrators:
            await query.answer("Добавьте хотя бы одного рассказчика.", show_alert=True)
            return True
        db_draft.set_bot_state(draft_id, "narrators_setup")
        await query.edit_message_text(
            bot_messages.get_message("interview_guide"),
            reply_markup=kb_interview_guide(draft_id),
        )
        return True

    if data.startswith("narrator_back:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        if draft:
            narrators = draft.get("narrators") or []
            char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft.get("characters") else "персонажа"
            text = bot_messages.get_message("narrators_list", narrators_list=_format_narrators(narrators)) if narrators else bot_messages.get_message("narrators_setup", character_name=char_name)
            await query.edit_message_text(text, reply_markup=kb_narrators(draft_id, narrators, bool(narrators)))
        return True

    # ── Гид по интервью (7.1–7.2) ────────────────────────────────────────────
    if data.startswith("guide_questions:"):
        draft_id = int(data.split(":")[1])
        await query.edit_message_text(
            bot_messages.get_message("interview_questions"),
            reply_markup=kb_interview_questions(draft_id),
        )
        return True

    if data.startswith("guide_pdf:"):
        await query.answer("PDF с вопросами скоро будет доступен.", show_alert=True)
        return True

    if data.startswith("guide_call_link:"):
        draft_id = int(data.split(":")[1])
        link = getattr(config, "TELEMOST_MEETING_LINK", "") or ""
        if link:
            await query.message.reply_text(f"Ссылка для звонка:\n{link}")
        else:
            await query.answer("Ссылка временно недоступна.", show_alert=True)
        return True

    if data.startswith("guide_back:"):
        draft_id = int(data.split(":")[1])
        await query.edit_message_text(
            bot_messages.get_message("interview_guide"),
            reply_markup=kb_interview_guide(draft_id),
        )
        return True

    # ── Загрузка материалов (8.1–8.5) ────────────────────────────────────────
    if data.startswith("upload_start:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        narrators = (draft.get("narrators") or []) if draft else []
        if len(narrators) == 1:
            # Авто-выбор единственного нарратора
            context.user_data["v2_current_narrator"] = narrators[0]["id"]
            context.user_data["v2_draft_id"] = draft_id
            db_draft.set_bot_state(draft_id, "collecting_interview_1")
            char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft and draft.get("characters") else "персонажа"
            await query.edit_message_text(
                bot_messages.get_message("upload_audio", narrator_name=narrators[0]["name"]),
                reply_markup=kb_upload_audio(draft_id, False),
            )
        else:
            await query.edit_message_text(
                bot_messages.get_message("upload_who"),
                reply_markup=kb_narrator_select(narrators, draft_id),
            )
        return True

    if data.startswith("upload_narrator:"):
        parts = data.split(":")
        draft_id, narrator_id = int(parts[1]), parts[2]
        draft = db_draft.get_draft_by_telegram_id(user.id)
        narrators = (draft.get("narrators") or []) if draft else []
        narrator = next((n for n in narrators if n["id"] == narrator_id), None)
        context.user_data["v2_current_narrator"] = narrator_id
        context.user_data["v2_draft_id"] = draft_id
        db_draft.set_bot_state(draft_id, "collecting_interview_1")
        name = narrator["name"] if narrator else "рассказчика"
        await query.edit_message_text(
            bot_messages.get_message("upload_audio", narrator_name=name),
            reply_markup=kb_upload_audio(draft_id, False),
        )
        return True

    if data.startswith("upload_to_photos:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        char_name = (draft.get("characters") or [{}])[0].get("name", "персонажа") if draft and draft.get("characters") else "персонажа"
        await query.edit_message_text(
            bot_messages.get_message("upload_photo", character_name=char_name),
            reply_markup=kb_upload_photos(draft_id),
        )
        return True

    if data.startswith("photo_type_photo:") or data.startswith("photo_type_doc:"):
        draft_id = int(data.split(":")[1])
        photo_type = "photo" if data.startswith("photo_type_photo:") else "document"
        context.user_data["v2_photo_type"] = photo_type
        context.user_data["v2_draft_id"] = draft_id
        type_label = "Фотографии персонажа" if photo_type == "photo" else "Фото документов"
        await query.edit_message_text(
            f"Загружайте {type_label}. Отправляйте фото прямо в чат.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Далее →", callback_data=f"upload_summary:{draft_id}")],
            ]),
        )
        return True

    if data.startswith("upload_summary:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        narrators = (draft.get("narrators") or []) if draft else []
        # Показываем итог
        try:
            photos = db.get_user_photos(user.id, 100)
            photo_count = sum(1 for p in photos if p.get("photo_type") != "document")
            doc_count = sum(1 for p in photos if p.get("photo_type") == "document")
        except Exception:
            photo_count = doc_count = 0
        narrator_summaries = "\n".join(
            f"✅ {n['name']} ({n.get('relation', '')}) — материалы получены" for n in narrators
        )
        text = bot_messages.get_message(
            "upload_summary",
            narrators_summary=narrator_summaries,
            photo_count=photo_count,
            doc_count=doc_count,
        )
        has_more = len(narrators) > 1
        await query.edit_message_text(text, reply_markup=kb_upload_summary(draft_id, has_more))
        return True

    if data.startswith("upload_done:"):
        draft_id = int(data.split(":")[1])
        db_draft.set_bot_state(draft_id, "processing_interview_1")
        await query.edit_message_text(bot_messages.get_message("upload_processing"))
        # Запускаем первичный пайплайн (транскрипция → Интервьюер)
        draft = db_draft.get_draft_by_telegram_id(user.id)
        char_name = _get_user_character_name(user.id)
        from pipeline_n8n import trigger_phase_a_background
        trigger_phase_a_background(
            telegram_id=user.id,
            transcript="",  # Пайплайн сам заберёт из S3
            character_name=char_name,
            draft_id=draft_id,
            username=user.username or "",
        )
        return True

    if data.startswith("upload_more:"):
        draft_id = int(data.split(":")[1])
        context.user_data["v2_draft_id"] = draft_id
        await query.edit_message_text(
            "Загружайте дополнительные файлы — аудио, голосовые или текст.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Готово", callback_data=f"upload_summary:{draft_id}")],
            ]),
        )
        return True

    # ── Уточняющие вопросы (8.6) ─────────────────────────────────────────────
    if data.startswith("interview2_start:"):
        draft_id = int(data.split(":")[1])
        db_draft.set_bot_state(draft_id, "collecting_interview_2")
        context.user_data["v2_draft_id"] = draft_id
        await query.edit_message_text(
            bot_messages.get_message("interview2"),
            reply_markup=kb_interview2_confirm(draft_id),
        )
        return True

    if data.startswith("assemble_book:"):
        draft_id = int(data.split(":")[1])
        db_draft.set_bot_state(draft_id, "assembling")
        await query.edit_message_text(bot_messages.get_message("assembling"))
        # Запускаем полный Phase A
        char_name = _get_user_character_name(user.id)
        from pipeline_n8n import trigger_phase_a_background
        trigger_phase_a_background(
            telegram_id=user.id,
            transcript="",
            character_name=char_name,
            draft_id=draft_id,
            username=user.username or "",
        )
        return True

    # ── Книга готова (10.2) ───────────────────────────────────────────────────
    if data.startswith("book_ready_back:"):
        draft_id = int(data.split(":")[1])
        draft = db_draft.get_draft_by_telegram_id(user.id)
        await _show_book_ready_callback(query, draft)
        return True

    if data.startswith("book_get_pdf:"):
        draft_id = int(data.split(":")[1])
        await query.answer("PDF отправляем в чат…")
        try:
            admin_url = os.environ.get("ADMIN_API_BASE_URL", "http://127.0.0.1:5001/api")
            import requests as _req
            r = _req.get(f"{admin_url}/book-context/{user.id}", timeout=5)
            if r.status_code == 200:
                pdf_file_id = r.json().get("pdf_file_id")
                if pdf_file_id:
                    await query.message.reply_document(pdf_file_id)
                    return True
        except Exception:
            pass
        await query.message.reply_text("PDF временно недоступен. Попробуйте позже.")
        return True

    if data.startswith("book_share:"):
        bot_username = (await query.get_bot()).username or "glava_bot"
        await query.message.reply_text(f"Поделитесь ботом: https://t.me/{bot_username}")
        return True

    # ── Правки (11.1) ─────────────────────────────────────────────────────────
    if data.startswith("revision_start:"):
        draft_id = int(data.split(":")[1])
        revision_count = db_draft.get_revision_count(draft_id)
        if revision_count >= MAX_REVISIONS:
            await query.edit_message_text(bot_messages.get_message("revision_limit"))
            return True
        state = f"revision_{revision_count + 1}"
        db_draft.set_bot_state(draft_id, state)
        context.user_data["v2_awaiting"] = "revision_text"
        context.user_data["v2_draft_id"] = draft_id
        await query.edit_message_text(
            bot_messages.get_message(
                "revision_prompt",
                revision_num=revision_count + 1,
                max_revisions=MAX_REVISIONS,
            ),
            reply_markup=kb_revision_comment(draft_id),
        )
        return True

    if data.startswith("revision_submit:"):
        draft_id = int(data.split(":")[1])
        text, is_ready = db_draft.get_pending_revision(draft_id)
        if not text:
            await query.answer("Сначала напишите комментарий.", show_alert=True)
            return True
        await _submit_revision(query.message, user, draft_id, text)
        db_draft.clear_pending_revision(draft_id)
        return True

    # ── Версии (12.1–12.2) ────────────────────────────────────────────────────
    if data.startswith("versions_list:"):
        draft_id = int(data.split(":")[1])
        try:
            admin_url = os.environ.get("ADMIN_API_BASE_URL", "http://127.0.0.1:5001/api")
            import requests as _req
            r = _req.get(f"{admin_url}/book-context/{user.id}", timeout=5)
            versions = r.json().get("versions", []) if r.status_code == 200 else []
        except Exception:
            versions = []
        if not versions:
            await query.edit_message_text(
                bot_messages.get_message("versions_empty"),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data=f"book_ready_back:{draft_id}")]]),
            )
        else:
            vlist = "\n".join(f"v{v.get('version')} · {str(v.get('created_at',''))[:10]}" for v in versions)
            await query.edit_message_text(
                bot_messages.get_message("versions_list", versions_list=vlist),
                reply_markup=kb_versions_list(versions, draft_id),
            )
        return True

    if data.startswith("version_open:"):
        parts = data.split(":")
        await query.answer("Версия будет отправлена в чат.")
        return True

    if data.startswith("version_rollback:"):
        parts = data.split(":")
        draft_id, version = int(parts[1]), parts[2]
        await query.edit_message_text(
            bot_messages.get_message("versions_rollback_confirm", version=version),
            reply_markup=kb_version_rollback_confirm(draft_id, version),
        )
        return True

    if data.startswith("version_rollback_confirm:"):
        parts = data.split(":")
        draft_id, version = int(parts[1]), parts[2]
        # Сбрасываем счётчик ревизий до нужной версии
        await query.edit_message_text("Версия восстановлена. /start для продолжения.")
        return True

    # ── Финализация (13.1–14.2) ────────────────────────────────────────────────
    if data.startswith("book_finalize:"):
        draft_id = int(data.split(":")[1])
        await query.edit_message_text(
            bot_messages.get_message("finalize_confirm"),
            reply_markup=kb_finalize_confirm(draft_id),
        )
        return True

    if data.startswith("finalize_confirm:"):
        draft_id = int(data.split(":")[1])
        db_draft.set_bot_state(draft_id, "finalized")
        logger.info("event: book_finalized draft_id=%s", draft_id)
        await query.edit_message_text(
            bot_messages.get_message("finalized"),
            reply_markup=kb_finalized(draft_id),
        )
        return True

    if data.startswith("finalize_done:"):
        draft_id = int(data.split(":")[1])
        await query.edit_message_text(
            bot_messages.get_message("finalized"),
            reply_markup=kb_finalized(draft_id),
        )
        return True

    if data.startswith("print_info:"):
        draft_id = int(data.split(":")[1])
        await query.edit_message_text(
            bot_messages.get_message("print_soon"),
            reply_markup=kb_print_soon(draft_id),
        )
        return True

    if data.startswith("print_waitlist:"):
        await query.answer("Добавили вас в список ожидания.", show_alert=True)
        return True

    # ── Возврат (15.1–15.2) ───────────────────────────────────────────────────
    if data.startswith("refund_start:"):
        draft_id = int(data.split(":")[1])
        context.user_data["v2_awaiting"] = "refund_reason"
        context.user_data["v2_draft_id"] = draft_id
        await query.edit_message_text(
            bot_messages.get_message("refund_reason"),
            reply_markup=kb_refund_reason(draft_id),
        )
        return True

    if data.startswith("refund_submit:"):
        draft_id = int(data.split(":")[1])
        reason = context.user_data.pop("v2_refund_reason", "")
        if not reason:
            await query.answer("Опишите причину — это поможет нам улучшить сервис.", show_alert=True)
            return True
        db_draft.set_bot_state(draft_id, "refund_requested")
        logger.info("event: refund_requested draft_id=%s reason=%s", draft_id, reason[:100])
        await query.edit_message_text(bot_messages.get_message("refund_submitted"))
        return True

    return False


async def _show_book_ready_callback(query, draft: dict | None) -> None:
    if not draft:
        await query.edit_message_text("Используйте /start для навигации.")
        return
    draft_id = draft["id"]
    revision_count = db_draft.get_revision_count(draft_id)
    text = bot_messages.get_message("book_ready")
    await query.edit_message_text(text, reply_markup=kb_book_ready(draft_id, revision_count, MAX_REVISIONS))


async def _submit_revision(message, user, draft_id: int, text: str) -> None:
    """Отправляет правку в Phase B пайплайн."""
    revision_count = db_draft.increment_revision_count(draft_id)
    db_draft.set_bot_state(draft_id, "revision_processing")
    await message.reply_text(bot_messages.get_message("revision_processing"))
    from pipeline_n8n import trigger_phase_b_background
    trigger_phase_b_background(
        telegram_id=user.id,
        input_type="text",
        content=text,
        character_name=_get_user_character_name(user.id),
        draft_id=draft_id,
        username=user.username or "",
    )


# ── /versions команда ─────────────────────────────────────────────────────────

async def cmd_versions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Список версий книги."""
    user = update.effective_user
    if not user:
        return
    draft = db_draft.get_draft_by_telegram_id(user.id)
    if not draft:
        await update.message.reply_text("Версий книги пока нет.")
        return
    draft_id = draft["id"]
    try:
        admin_url = os.environ.get("ADMIN_API_BASE_URL", "http://127.0.0.1:5001/api")
        import requests as _req
        r = _req.get(f"{admin_url}/book-context/{user.id}", timeout=5)
        versions = r.json().get("versions", []) if r.status_code == 200 else []
    except Exception:
        versions = []
    if not versions:
        await update.message.reply_text(bot_messages.get_message("versions_empty"))
        return
    vlist = "\n".join(f"v{v.get('version')} · {str(v.get('created_at',''))[:10]}" for v in versions)
    await update.message.reply_text(
        bot_messages.get_message("versions_list", versions_list=vlist),
        reply_markup=kb_versions_list(versions, draft_id),
    )


async def _post_init(app: Application) -> None:
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_my_commands([
        BotCommand("start", "Начать / главное меню"),
        BotCommand("versions", "Версии книги"),
        BotCommand("list", "Мои материалы"),
        BotCommand("online", "Записать онлайн-встречу"),
        BotCommand("cabinet", "Кабинет"),
    ])
    # Кнопка меню слева — открывает Mini App кабинет
    try:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="📱 Кабинет", web_app=WebAppInfo(url=TMA_URL))
        )
        logger.info("set_chat_menu_button WebApp OK: %s", TMA_URL)
    except Exception as e:
        logger.error("set_chat_menu_button WebApp FAILED: %s", e)
    try:
        await app.bot.set_my_description(
            "Создай живую книгу о близких. Нажми /start чтобы начать."
        )
    except Exception as e:
        logger.debug("set_my_description: %s", e)


def main() -> None:
    config.BOT_TOKEN
    config.DATABASE_URL
    config.S3_BUCKET_NAME
    try:
        storage.ensure_bucket_exists()
    except Exception as e:
        logger.warning("Бакет: %s", e)

    app = Application.builder().token(config.BOT_TOKEN).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("versions", cmd_versions))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("online", cmd_online))
    app.add_handler(CommandHandler("cabinet", cmd_cabinet))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_audio_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("GLAVA бот запущен (Pre-pay flow). Ctrl+C — остановка.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
