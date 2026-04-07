# -*- coding: utf-8 -*-
"""
CCO-бот ГЛАВА — AI Chief Customer Officer.
Работает в групповом чате с командой. Отвечает по @mention.
Запуск: python -m cco.bot
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("cco.bot")

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from cco.llm_cco import get_cco_response, generate_digest, analyze_images_from_folder
from cco.report_gen import generate_html_report


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start — приветствие и chat_id."""
    chat = update.effective_chat
    await update.message.reply_text(
        f"CCO-агент ГЛАВА активен.\n"
        f"Chat ID: {chat.id}\n\n"
        f"Упоминайте меня через @, чтобы задать вопрос."
    )


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /digest — еженедельный дайджест."""
    chat = update.effective_chat
    await update.message.reply_text("Собираю данные, формирую дайджест...")

    answer = generate_digest(chat_id=chat.id)
    if answer:
        for chunk in _split_message(answer):
            await update.message.reply_text(chunk)
    else:
        await update.message.reply_text("Не удалось сформировать дайджест.")


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /report <тема> — анализ скринов из папки + HTML-презентация.

    Пример: /report storyworth
    Читает скрины из tasks/audience-research/storyworth-screens/
    Генерирует tasks/audience-research/docs/storyworth-report.html
    """
    args = context.args
    topic = args[0].lower() if args else "storyworth"

    await update.message.reply_text(
        f"Анализирую скрины по теме «{topic}»...\n"
        f"Читаю папку tasks/audience-research/{topic}-screens/\n"
        f"Это займёт ~30-60 секунд."
    )

    analysis = analyze_images_from_folder(topic=topic)
    if not analysis or analysis.startswith("Папка") or analysis.startswith("В папке"):
        await update.message.reply_text(analysis or "Не удалось проанализировать скрины.")
        return

    await update.message.reply_text("Анализ готов, генерирую HTML-презентацию...")

    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    screens_dir = project_root / "tasks" / "audience-research" / f"{topic}-screens"
    screen_count = len([f for f in screens_dir.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]) if screens_dir.exists() else 0

    report_path = generate_html_report(
        topic=topic.capitalize(),
        analysis_md=analysis,
        screen_count=screen_count,
    )

    # Также сохраняем/обновляем md-версию
    md_path = project_root / "tasks" / "audience-research" / "docs" / f"{topic}-analysis.md"
    md_path.write_text(analysis, encoding="utf-8")

    await update.message.reply_text(f"Готово! Отправляю файл...")
    with open(report_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=report_path.name,
            caption=f"Анализ {topic.capitalize()} · {screen_count} скринов",
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений — реагирует на @mention и reply."""
    message = update.message
    if not message or not message.text:
        return

    chat = update.effective_chat
    text = message.text
    user = message.from_user

    bot_username = ""
    try:
        me = await context.bot.get_me()
        bot_username = me.username or ""
    except Exception:
        pass

    mentioned = bot_username and f"@{bot_username}" in text
    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.is_bot
        and message.reply_to_message.from_user.username == bot_username
    )

    if not mentioned and not replied_to_bot:
        return

    if mentioned and bot_username:
        text = text.replace(f"@{bot_username}", "").strip()

    if not text:
        return

    # Проверяем, просят ли сделать отчёт/презу по конкуренту
    report_keywords = ("презу", "отчёт", "отчет", "report", "анализ скрин", "проанализируй скрин",
                       "поизучал сервис", "изучил сервис", "исследовал сервис", "скрины сервис",
                       "пользовательский путь", "ux", "конкурент")
    if any(kw in text.lower() for kw in report_keywords):
        topic = _extract_topic(text)

        await update.message.reply_text(
            f"Читаю скрины из tasks/audience-research/{topic}-screens/ "
            f"и генерирую презентацию. Подожди ~60 секунд..."
        )

        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent

        analysis = analyze_images_from_folder(topic=topic)
        if not analysis or analysis.startswith("Папка") or analysis.startswith("В папке"):
            await message.reply_text(analysis or "Не удалось проанализировать скрины.")
            return

        screens_dir = project_root / "tasks" / "audience-research" / f"{topic}-screens"
        screen_count = len([
            f for f in screens_dir.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]) if screens_dir.exists() else 0

        report_path = generate_html_report(
            topic=topic.capitalize(),
            analysis_md=analysis,
            screen_count=screen_count,
        )
        md_path = project_root / "tasks" / "audience-research" / "docs" / f"{topic}-analysis.md"
        md_path.write_text(analysis, encoding="utf-8")

        with open(report_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=report_path.name,
                caption=f"Анализ {topic.capitalize()} · {screen_count} скринов",
            )
        return

    user_name = user.first_name or user.username or "" if user else ""
    logger.info("CCO query from %s: %s", user_name, text[:100])

    answer = get_cco_response(
        user_message=text,
        chat_id=chat.id,
        user_name=user_name,
    )
    if answer:
        for chunk in _split_message(answer):
            await message.reply_text(chunk)


def _extract_topic(text: str) -> str:
    """Извлекает название темы/продукта из произвольного сообщения.

    Стратегии (по приоритету):
    1. Слово после маркера «сервис/продукт/приложение X»
    2. Известное название продукта в тексте (storyworth, storium, etc.)
    3. Слово после «по/про» рядом с отчётными словами
    4. Fallback → storyworth
    """
    import re as _re

    lower = text.lower()

    # 1. После маркера «сервис/продукт/приложение»
    m = _re.search(r"(?:сервис|продукт|приложение|платформу?)\s+([a-zа-яё0-9_\-]{3,})", lower)
    if m:
        return m.group(1).strip(".,!?")

    # 2. Известные названия продуктов
    known = ["storyworth", "storium", "chatbooks", "artifact", "legacybox",
             "unforgettable", "memorymixer", "remento", "forever"]
    for name in known:
        if name in lower:
            return name

    # 3. После «по/про» — берём следующее слово, если оно не стоп-слово
    stop = {"мне", "нас", "нам", "это", "той", "той", "той", "всем", "всё",
            "все", "нашему", "нашей", "нашего", "такой", "такому", "скринам",
            "скринам", "скрины", "скриншотам", "материалу"}
    m = _re.search(r"(?:по|про)\s+([a-zа-яё0-9_\-]{3,})", lower)
    if m and m.group(1) not in stop:
        return m.group(1).strip(".,!?")

    return "storyworth"



    """Разбивает длинное сообщение на части для Telegram."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


async def _post_init(app: Application) -> None:
    await app.bot.set_my_commands([
        BotCommand("start", "Информация о боте"),
        BotCommand("digest", "Еженедельный дайджест"),
        BotCommand("report", "Анализ скринов конкурента → HTML-презентация"),
    ])
    me = await app.bot.get_me()
    logger.info("CCO бот запущен: @%s", me.username)


def main() -> None:
    token = os.environ.get("CCO_BOT_TOKEN")
    if not token:
        logger.error("CCO_BOT_TOKEN не задан в .env")
        sys.exit(1)

    app = Application.builder().token(token).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("CCO бот запускается...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
