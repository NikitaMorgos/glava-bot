# -*- coding: utf-8 -*-
"""
GLAVA — Telegram-бот. Pre-pay flow: навигация до оплаты.

Запуск: python main.py
Перед первым запуском: psql -d your_db -f sql/add_draft_orders.sql
"""

import html
import logging
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
from prepay.messages import (
    INTRO_MAIN_MSG, INTRO_EXAMPLE_MSG, INTRO_PRICE_MSG,
    CONFIG_CHARACTERS_MSG, CONFIG_CHARACTERS_LIST_MSG,
    EMAIL_INPUT_MSG, EMAIL_ERROR_MSG, ORDER_SUMMARY_MSG,
    PAYMENT_INIT_MSG, PAYMENT_WAIT_MSG, PAYMENT_STILL_PENDING_MSG,
    RESUME_DRAFT_MSG, RESUME_PAYMENT_MSG, BLOCKED_MEDIA_MSG,
    ONLINE_MEETING_INTRO_MSG, ONLINE_MEETING_LINK_SENT_MSG,
    ONLINE_MEETING_TELEMOST_SENT_MSG, ONLINE_MEETING_BAD_LINK_MSG, ONLINE_MEETING_ERROR_MSG,
)
from prepay.keyboards import (
    kb_intro_main, kb_intro_example, kb_intro_price,
    kb_config_characters, kb_config_edit_list, kb_email_back,
    kb_order_summary, kb_payment, kb_resume_draft, kb_resume_payment, kb_blocked_start,
    kb_online_meeting,
)

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


def _online_meeting_api_key() -> tuple[str, str]:
    """
    Возвращает (provider, api_key) для записи онлайн-встреч.
    Приоритет: recall → mymeet.
    """
    recall_key = getattr(config, "RECALL_API_KEY", "") or ""
    mymeet_key = getattr(config, "MYMEET_API_KEY", "") or ""
    if recall_key:
        return "recall", recall_key
    if mymeet_key:
        return "mymeet", mymeet_key
    return "", ""


async def _start_online_meeting_recording(
    link: str, provider: str, api_key: str
) -> str | None:
    """
    Запускает запись встречи через Recall.ai или MyMeet.
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
    return None


def _run_online_meeting_background(
    bot_id: str, provider: str, telegram_id: int, username: str | None
) -> None:
    """Запускает фоновую обработку онлайн-встречи через нужный провайдер."""
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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """START — только приветствие и главное меню (ТЗ 4.1–4.2)."""
    user = update.effective_user
    if not user:
        return

    # Устанавливаем кнопку меню WebApp для этого конкретного чата
    try:
        await context.bot.set_chat_menu_button(
            chat_id=update.effective_chat.id,
            menu_button=MenuButtonWebApp(text="📱 Кабинет", web_app=WebAppInfo(url=TMA_URL)),
        )
        logger.info("set_chat_menu_button per-chat OK: chat_id=%s", update.effective_chat.id)
    except Exception as e:
        logger.error("set_chat_menu_button per-chat FAILED: chat_id=%s err=%s", update.effective_chat.id, e)

    context.user_data.clear()
    markup = kb_intro_main()
    # WebApp-кнопка добавляется всем — она отображается как «Open» в списке чатов Telegram.
    # Для неоплативших TMA покажет информационный экран; для оплативших — полный кабинет.
    btn_label = "📱 Мой кабинет" if _user_has_paid(user.id) else "📱 Открыть кабинет"
    markup = InlineKeyboardMarkup(
        list(markup.inline_keyboard) + [[
            InlineKeyboardButton(btn_label, web_app=WebAppInfo(url=TMA_URL))
        ]]
    )
    await update.message.reply_text(INTRO_MAIN_MSG, reply_markup=markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not user:
        return
    data = query.data or ""

    if data == "intro_main":
        await query.edit_message_text(INTRO_MAIN_MSG, reply_markup=kb_intro_main())
        return

    if data == "intro_example":
        logger.info("event: example_viewed")
        await query.edit_message_text(INTRO_EXAMPLE_MSG, reply_markup=kb_intro_example())
        return

    if data == "intro_price":
        logger.info("event: price_viewed")
        await query.edit_message_text(INTRO_PRICE_MSG, reply_markup=kb_intro_price())
        return

    if data == "intro_start":
        draft = db_draft.get_or_create_draft(user.id, user.username)
        if not draft:
            return
        logger.info("event: draft_created")
        status = draft.get("status", "")
        if status == "payment_pending":
            await query.edit_message_text(
                PAYMENT_WAIT_MSG,
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
                await query.answer(PAYMENT_STILL_PENDING_MSG, show_alert=True)
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
                PAYMENT_INIT_MSG.format(payment_url=payment_url),
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
                await query.answer(PAYMENT_STILL_PENDING_MSG, show_alert=True)
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
        provider, api_key = _online_meeting_api_key()
        if not link or not provider:
            await query.answer("Ссылка на встречу не настроена.", show_alert=True)
            return
        bot_id = await _start_online_meeting_recording(link, provider, api_key)
        if bot_id:
            _run_online_meeting_background(bot_id, provider, user.id, user.username)
            await query.edit_message_text(
                f"{link}\n\n{ONLINE_MEETING_TELEMOST_SENT_MSG}",
            )
        else:
            await query.answer(ONLINE_MEETING_ERROR_MSG, show_alert=True)
        return


async def _show_config_characters(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id: int) -> None:
    draft = db_draft.get_or_create_draft(telegram_id, update.effective_user and update.effective_user.username)
    if not draft:
        return
    chars = draft.get("characters") or []
    msg = CONFIG_CHARACTERS_MSG
    if chars:
        msg = CONFIG_CHARACTERS_LIST_MSG.format(characters=_format_characters(chars))
    await update.message.reply_text(msg, reply_markup=kb_config_characters(draft["id"], len(chars) >= 1))


async def _show_config_characters_callback(query, context, telegram_id: int) -> None:
    draft = db_draft.get_or_create_draft(telegram_id, None)
    if not draft:
        return
    chars = draft.get("characters") or []
    msg = CONFIG_CHARACTERS_MSG
    if chars:
        msg = CONFIG_CHARACTERS_LIST_MSG.format(characters=_format_characters(chars))
    await query.edit_message_text(msg, reply_markup=kb_config_characters(draft["id"], len(chars) >= 1))


async def _show_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE, draft_id: int) -> None:
    await update.message.reply_text(EMAIL_INPUT_MSG, reply_markup=kb_email_back(draft_id))


async def _show_email_input_callback(query, context, draft_id: int) -> None:
    context.user_data.pop("prepay_awaiting", None)
    context.user_data.pop("prepay_char_name", None)
    context.user_data["prepay_awaiting"] = "email"
    context.user_data["prepay_draft_id"] = draft_id
    await query.edit_message_text(EMAIL_INPUT_MSG, reply_markup=kb_email_back(draft_id))


async def _show_order_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, draft: dict) -> None:
    chars = draft.get("characters") or []
    total = _format_price(draft.get("total_price", 0))
    email = draft.get("email") or ""
    msg = ORDER_SUMMARY_MSG.format(
        characters=_format_characters(chars),
        total=total,
        email=email,
    )
    await update.message.reply_text(msg, reply_markup=kb_order_summary(draft["id"]))


async def _show_order_summary_callback(query, context, draft: dict) -> None:
    chars = draft.get("characters") or []
    total = _format_price(draft.get("total_price", 0))
    email = draft.get("email") or ""
    msg = ORDER_SUMMARY_MSG.format(
        characters=_format_characters(chars),
        total=total,
        email=email,
    )
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
            await update.message.reply_text(EMAIL_ERROR_MSG, reply_markup=kb_email_back(draft_id or 0))
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
    await update.message.reply_text(BLOCKED_MEDIA_MSG, reply_markup=kb_blocked_start())


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
            db.save_photo(db_user["id"], photo.file_id, storage_key)
            await update.message.reply_text("Фото сохранено. Напиши подпись к нему (1-2 предложения).")
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
            await update.message.reply_text(ONLINE_MEETING_BAD_LINK_MSG)
            return
        provider, api_key = _online_meeting_api_key()
        if not provider:
            await update.message.reply_text("Запись онлайн-встреч временно недоступна.")
            return
        bot_id = await _start_online_meeting_recording(text, provider, api_key)
        if bot_id:
            _run_online_meeting_background(bot_id, provider, user.id, user.username)
            await update.message.reply_text(ONLINE_MEETING_LINK_SENT_MSG)
        else:
            await update.message.reply_text(ONLINE_MEETING_ERROR_MSG)
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
    pending = db.get_pending_photo(user.id)
    if pending:
        db.update_photo_caption(pending["id"], text)
        await update.message.reply_text("Подпись сохранена.")
    elif await _handle_prepay_text(update, context, text, user):
        pass
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
        provider, _ = _online_meeting_api_key()
        if not provider:
            await update.message.reply_text("Запись онлайн-встреч временно недоступна.")
            return
        context.user_data["awaiting_meeting_link"] = True
        has_telemost = bool(getattr(config, "TELEMOST_MEETING_LINK", "") or "")
        reply_markup = kb_online_meeting(has_telemost)
        await update.message.reply_text(
            ONLINE_MEETING_INTRO_MSG,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.exception("cmd_online: %s", e)
        if update.message:
            await update.message.reply_text("Ошибка. Попробуйте позже или напишите в поддержку.")


async def _post_init(app: Application) -> None:
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.bot.set_my_commands([
        BotCommand("start", "Начать"),
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
