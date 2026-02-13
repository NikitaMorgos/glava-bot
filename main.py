"""
GLAVA — Telegram-бот для приёма и хранения голосовых сообщений.

Запуск: python main.py

Перед запуском:
1. Создай бота через @BotFather и получи BOT_TOKEN
2. Создай БД PostgreSQL и выполни sql/init_db.sql
3. Настрой S3-хранилище и заполни .env
"""

import logging
import tempfile
from pathlib import Path

from telegram import BotCommand, MenuButtonCommands, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import config
import db
import storage

# Настройка логирования (чтобы видеть, что происходит)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start — приветствие."""
    await update.message.reply_text(
        "Привет! Я бот GLAVA.\n\n"
        "Голосовые — отправь голосовое или аудио-файл (.ogg, .mp3, .m4a, .wav), я сохраню в облаке.\n"
        "Фото — отправь фото, затем напиши подпись (1–2 предложения).\n"
        "Команда /list — покажет твои голосовые и фото с подписями."
    )


AUDIO_EXTENSIONS = {".ogg", ".mp3", ".m4a", ".wav", ".opus", ".oga"}


async def _save_audio_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    suffix: str,
    duration: int | None,
) -> None:
    """Общая логика сохранения аудио (голосовое, audio, document)."""
    user = update.message.from_user
    if not user:
        await update.message.reply_text("Не удалось определить отправителя.")
        return

    telegram_id = user.id
    username = user.username

    try:
        db_user = db.get_or_create_user(telegram_id, username)
        user_id = db_user["id"]

        tg_file = await context.bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        await tg_file.download_to_drive(tmp_path)

        try:
            storage_key = storage.upload_file(tmp_path, user_id)
            db.save_voice_message(
                user_id=user_id,
                telegram_file_id=file_id,
                storage_key=storage_key,
                duration=duration,
            )
            await update.message.reply_text("Аудио сохранено.")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.exception("Ошибка при сохранении аудио")
        await update.message.reply_text(f"Ошибка при сохранении: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик голосовых сообщений (кнопка микрофона)."""
    message = update.message
    if not message.voice:
        return
    await _save_audio_file(
        update, context,
        message.voice.file_id,
        ".ogg",
        message.voice.duration,
    )


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик аудио-файлов (отправленных как «Аудио»)."""
    message = update.message
    if not message.audio:
        return
    ext = Path(message.audio.file_name or "").suffix or ".mp3"
    if ext.lower() not in AUDIO_EXTENSIONS:
        ext = ".mp3"
    await _save_audio_file(
        update, context,
        message.audio.file_id,
        ext,
        message.audio.duration,
    )


async def handle_audio_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик аудио, отправленных как файл (Документ)."""
    message = update.message
    if not message.document:
        return
    name = (message.document.file_name or "").lower()
    ext = Path(name).suffix
    if ext not in AUDIO_EXTENSIONS:
        await message.reply_text(
            "Принимаю только аудио: .ogg, .mp3, .m4a, .wav, .opus. "
            "Голосовые — нажми кнопку микрофона."
        )
        return
    await _save_audio_file(
        update, context,
        message.document.file_id,
        ext,
        None,
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик фото.
    Сохраняет фото в облако. Следующее текстовое сообщение от пользователя
    будет считаться подписью к этому фото.
    """
    message = update.message
    if not message.photo:
        return

    user = message.from_user
    if not user:
        await message.reply_text("Не удалось определить отправителя.")
        return

    telegram_id = user.id
    username = user.username

    try:
        db_user = db.get_or_create_user(telegram_id, username)
        user_id = db_user["id"]

        # Берём фото в наибольшем качестве (последнее в списке)
        photo = message.photo[-1]
        photo_file = await context.bot.get_file(photo.file_id)

        suffix = ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
        await photo_file.download_to_drive(tmp_path)

        try:
            storage_key = storage.upload_file(tmp_path, user_id)
            db.save_photo(user_id=user_id, telegram_file_id=photo.file_id, storage_key=storage_key)
            await message.reply_text(
                "Фото сохранено. Теперь напиши подпись к нему (1–2 предложения), "
                "например: «Мама в 1987, первый год работы в школе»."
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.exception("Ошибка при сохранении фото")
        await message.reply_text(f"Ошибка при сохранении: {e}")


async def handle_caption_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик текста — подпись к последнему фото.
    Если у пользователя есть фото без подписи, текст становится подписью.
    """
    message = update.message
    if not message.text or message.text.startswith("/"):
        return

    user = update.effective_user
    if not user:
        return

    text = message.text.strip()
    if not text:
        return

    try:
        pending = db.get_pending_photo(user.id)
        if pending:
            db.update_photo_caption(pending["id"], text)
            await message.reply_text("Подпись сохранена.")
        else:
            await message.reply_text(
                "Сначала отправь фото, затем напиши подпись к нему."
            )
    except Exception as e:
        logger.exception("Ошибка при сохранении подписи")
        await message.reply_text(f"Ошибка: {e}")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /list — показывает голосовые и фото с подписями.
    """
    user = update.effective_user
    if not user:
        await update.message.reply_text("Не удалось определить пользователя.")
        return

    limit = config.LIST_LIMIT

    try:
        voice_messages = db.get_user_voice_messages(user.id, limit=limit)
        photos = db.get_user_photos(user.id, limit=15)
    except Exception as e:
        logger.exception("Ошибка при получении списка")
        await update.message.reply_text(f"Ошибка: {e}")
        return

    if not voice_messages and not photos:
        await update.message.reply_text(
            "Пока ничего нет. Отправь голосовое или фото с подписью."
        )
        return

    parts = []

    if voice_messages:
        parts.append(f"Голосовые ({len(voice_messages)}):\n")
        for i, msg in enumerate(voice_messages, 1):
            url = storage.get_presigned_download_url(msg["storage_key"])
            duration_str = f" ({msg['duration']} сек)" if msg.get("duration") else ""
            created = msg["created_at"].strftime("%d.%m.%Y %H:%M") if msg.get("created_at") else ""
            parts.append(f"{i}. {created}{duration_str}\n{url}")
        parts.append("")

    if photos:
        parts.append(f"Фото с подписями ({len(photos)}):\n")
        for i, p in enumerate(photos, 1):
            url = storage.get_presigned_download_url(p["storage_key"])
            caption = (p.get("caption") or "")[:100]
            created = p["created_at"].strftime("%d.%m.%Y %H:%M") if p.get("created_at") else ""
            parts.append(f"{i}. {created}\n{caption}\n{url}")
        parts.append("")

    text = "\n\n".join(parts).strip()
    if len(text) > 4000:
        await update.message.reply_text(parts[0])
        for p in parts[1:]:
            if p:
                await update.message.reply_text(p)
    else:
        await update.message.reply_text(text)


def main() -> None:
    """Запуск бота."""
    # Проверяем конфиг при старте
    config.BOT_TOKEN
    config.DATABASE_URL
    config.S3_BUCKET_NAME

    # Создаём бакет, если его нет (для MinIO и др.)
    try:
        storage.ensure_bucket_exists()
    except Exception as e:
        logger.warning("Не удалось создать/проверить бакет: %s. Убедись, что бакет существует.", e)

    # Меню команд (синяя кнопка слева от поля ввода)
    async def set_commands(application: Application) -> None:
        await application.bot.set_my_commands([
            BotCommand("start", "Начать / приветствие"),
            BotCommand("list", "Список голосовых и фото"),
        ])
        # Явно включаем кнопку меню команд (по умолчанию для всех чатов)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    application = Application.builder().token(config.BOT_TOKEN).post_init(set_commands).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("list", cmd_list))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_audio_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    # Текст как подпись к фото (не команда)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption_text)
    )

    # Запускаем бота (polling — бот сам опрашивает Telegram на новые сообщения)
    # drop_pending_updates — сбрасывает старые сообщения при старте, помогает избежать Conflict
    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
