# -*- coding: utf-8 -*-
"""
CCO-бот ГЛАВА — AI Chief Customer Officer.
Работает в групповом чате с командой. Отвечает по @mention.
Запуск: python -m cco.bot
"""
import asyncio
import logging
import os
import re
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

from cco.llm_cco import (
    get_cco_response,
    generate_digest,
    analyze_images_from_folder,
    analyze_question_bank_from_input,
)
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
    raw_path = args[1] if len(args) > 1 else ""
    explicit_path = _extract_folder_path(raw_path) if raw_path else None
    screens_folder = explicit_path if explicit_path and explicit_path.name.endswith("-screens") else None
    input_dir = explicit_path if explicit_path and explicit_path.name.endswith("-input") else None
    if input_dir and screens_folder is None:
        # Явно просили анализировать input-папку: не подмешиваем старые скрины по topic.
        project_root = Path(__file__).resolve().parent.parent
        screens_folder = project_root / "tasks" / "audience-research" / "__no-screens__"

    await update.message.reply_text(
        f"Анализирую материалы по теме «{topic}»...\n"
        f"Скрины: {screens_folder or f'tasks/audience-research/{topic}-screens/'}\n"
        f"Текст: {input_dir or f'tasks/audience-research/{topic}-input/'}\n"
        f"Это займёт ~30-60 секунд."
    )

    # Если явно передали *-input, считаем это задачей анализа банка вопросов.
    input_only_mode = input_dir is not None and (screens_folder is not None and screens_folder.name == "__no-screens__")
    if input_only_mode:
        analysis = await asyncio.to_thread(analyze_question_bank_from_input, topic, input_dir)
    else:
        analysis = await asyncio.to_thread(
            analyze_images_from_folder,
            topic,
            screens_folder,
            None,
            input_dir,
        )
    if not analysis or analysis.startswith("Не нашёл материалов"):
        await update.message.reply_text(analysis or "Не удалось проанализировать скрины.")
        return

    await update.message.reply_text("Анализ готов, генерирую HTML-презентацию...")

    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    screens_dir = screens_folder or (project_root / "tasks" / "audience-research" / f"{topic}-screens")
    screen_count = len([f for f in screens_dir.iterdir() if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]) if screens_dir.exists() else 0

    report_title = f"{topic.capitalize()} Question Bank" if input_only_mode else topic.capitalize()
    report_path = await asyncio.to_thread(generate_html_report, report_title, analysis, screen_count)

    # Также сохраняем/обновляем md-версию
    md_path = project_root / "tasks" / "audience-research" / "docs" / f"{topic}-analysis.md"
    await asyncio.to_thread(md_path.write_text, analysis, "utf-8")

    await update.message.reply_text(f"Готово! Отправляю файл...")
    with open(report_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=report_path.name,
            caption=(
                f"Анализ {topic.capitalize()} · question bank"
                if input_only_mode
                else f"Анализ {topic.capitalize()} · {screen_count} скринов"
            ),
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений — реагирует на @mention и reply."""
    message = update.message
    if not message or not message.text:
        return

    chat = update.effective_chat
    project_root = Path(__file__).resolve().parent.parent
    text = message.text
    user = message.from_user

    bot_username = ""
    try:
        me = await context.bot.get_me()
        bot_username = me.username or ""
    except Exception:
        pass

    text_lower = text.lower()
    bot_username_lower = (bot_username or "").lower()
    mentioned = bool(bot_username_lower and f"@{bot_username_lower}" in text_lower)
    replied_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.is_bot
        and (message.reply_to_message.from_user.username or "").lower() == bot_username_lower
    )

    if not mentioned and not replied_to_bot:
        return

    if mentioned and bot_username:
        text = text.replace(f"@{bot_username}", "").replace(f"@{bot_username_lower}", "").strip()

    if not text:
        return

    # Проверяем, просят ли сделать отчёт/презу по конкуренту
    report_keywords = ("презу", "отчёт", "отчет", "report", "анализ скрин", "проанализируй скрин",
                       "поизучал сервис", "изучил сервис", "исследовал сервис", "скрины сервис",
                       "пользовательский путь", "ux", "конкурент")
    if any(kw in text.lower() for kw in report_keywords):
        topic = _extract_topic(text)
        explicit_path = _extract_folder_path(text)
        screens_folder = explicit_path if explicit_path and explicit_path.name.endswith("-screens") else None
        input_dir = explicit_path if explicit_path and explicit_path.name.endswith("-input") else None
        if input_dir and screens_folder is None:
            # Явно просили анализировать input-папку: не подмешиваем старые скрины по topic.
            screens_folder = project_root / "tasks" / "audience-research" / "__no-screens__"

        await update.message.reply_text(
            f"Читаю материалы и генерирую презентацию.\n"
            f"Скрины: {screens_folder or f'tasks/audience-research/{topic}-screens/'}\n"
            f"Текст: {input_dir or f'tasks/audience-research/{topic}-input/'}\n"
            f"Подожди ~60 секунд..."
        )

        input_only_mode = input_dir is not None and (screens_folder is not None and screens_folder.name == "__no-screens__")
        if input_only_mode:
            analysis = await asyncio.to_thread(analyze_question_bank_from_input, topic, input_dir)
        else:
            analysis = await asyncio.to_thread(
                analyze_images_from_folder,
                topic,
                screens_folder,
                None,
                input_dir,
            )
        if not analysis or analysis.startswith("Не нашёл материалов"):
            await message.reply_text(analysis or "Не удалось проанализировать скрины.")
            return

        screens_dir = screens_folder or (project_root / "tasks" / "audience-research" / f"{topic}-screens")
        screen_count = len([
            f for f in screens_dir.iterdir()
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]) if screens_dir.exists() else 0

        report_title = f"{topic.capitalize()} Question Bank" if input_only_mode else topic.capitalize()
        report_path = await asyncio.to_thread(generate_html_report, report_title, analysis, screen_count)
        md_path = project_root / "tasks" / "audience-research" / "docs" / f"{topic}-analysis.md"
        await asyncio.to_thread(md_path.write_text, analysis, "utf-8")

        with open(report_path, "rb") as f:
            await message.reply_document(
                document=f,
                filename=report_path.name,
                caption=(
                    f"Анализ {topic.capitalize()} · question bank"
                    if input_only_mode
                    else f"Анализ {topic.capitalize()} · {screen_count} скринов"
                ),
            )
        return

    user_name = user.first_name or user.username or "" if user else ""
    logger.info("CCO query from %s: %s", user_name, text[:100])

    answer = await asyncio.to_thread(
        get_cco_response,
        text,
        chat.id,
        user_name,
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


def _extract_folder_path(text: str) -> Path | None:
    """Извлекает путь вида tasks/audience-research/* из текста сообщения."""
    m = re.search(r"(tasks[\\/][^\s]+)", text, flags=re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).strip().strip(".,!?:;")
    rel = raw.replace("\\", "/")
    project_root = Path(__file__).resolve().parent.parent
    return project_root / rel
def _split_message(text: str, max_len: int = 4000) -> list[str]:
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
