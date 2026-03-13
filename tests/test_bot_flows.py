# -*- coding: utf-8 -*-
"""
Тесты сценариев бота GLAVA (с моками БД и Telegram API).
Запуск: из корня проекта: pytest tests/ -v
Требуется: pip install pytest pytest-asyncio
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch



@pytest.fixture(autouse=True)
def mock_deps():
    """Мокаем db, db_draft, storage для всех тестов. Патчим до импорта main в тесте."""
    with patch("main.db") as m_db, patch("main.db_draft") as m_draft, patch("main.storage") as m_storage:
        m_db.get_or_create_user.return_value = {"id": 1}
        m_db.get_user_voice_messages.return_value = []
        m_db.get_user_photos.return_value = []
        m_db.get_pending_photo.return_value = None
        m_draft.get_or_create_draft.return_value = None
        m_draft.get_draft_by_telegram_id.return_value = None
        yield {"db": m_db, "db_draft": m_draft, "storage": m_storage}


@pytest.mark.asyncio
async def test_cmd_start_sends_intro(mock_deps):
    """/start — приветствие и главное меню."""
    import main
    update = MagicMock()
    update.effective_user = MagicMock(id=999, username="u")
    update.message = MagicMock(reply_text=AsyncMock())
    context = MagicMock(user_data={})
    await main.cmd_start(update, context)
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "Glava" in text or "книгу" in text


@pytest.mark.asyncio
async def test_callback_intro_main(mock_deps):
    """Кнопка «Назад» с примера/цены — возврат в главное меню."""
    import main
    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_main"
    update = MagicMock(effective_user=MagicMock(id=1, username="u"), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    query.edit_message_text.assert_called_once()
    assert "intro_main" in str(query.edit_message_text.call_args) or query.edit_message_text.called


@pytest.mark.asyncio
async def test_callback_intro_example(mock_deps):
    """Кнопка «Посмотреть пример» — показ примера."""
    import main
    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_example"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_callback_intro_start_creates_draft(mock_deps):
    """«Начать» — создаётся черновик, показ конфига персонажей или email."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [], "email": None, "total_price": 0}
    mock_deps["db_draft"].get_or_create_draft.return_value = draft
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_start"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    query.edit_message_text.assert_called()
    mock_deps["db_draft"].get_or_create_draft.assert_called()


@pytest.mark.asyncio
async def test_callback_intro_start_payment_pending(mock_deps):
    """«Начать» при статусе payment_pending — показ ссылки на оплату."""
    import main
    draft = {"id": 1, "status": "payment_pending", "payment_url": "https://pay.example/1", "payment_id": "p1"}
    mock_deps["db_draft"].get_or_create_draft.return_value = draft
    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_start"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    call_text = query.edit_message_text.call_args[0][0]
    assert "Ожидаем" in call_text or "pay" in call_text.lower() or "оплат" in call_text


@pytest.mark.asyncio
async def test_callback_intro_start_paid(mock_deps):
    """«Начать» при статусе paid — сообщение «Оплата прошла», /list."""
    import main
    draft = {"id": 1, "status": "paid"}
    mock_deps["db_draft"].get_or_create_draft.return_value = draft
    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_start"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    call_text = query.edit_message_text.call_args[0][0]
    assert "Оплата прошла" in call_text or "/list" in call_text


@pytest.mark.asyncio
async def test_callback_order_pay_calls_create_payment(mock_deps):
    """«Перейти к оплате» — вызов create_payment и показ ссылки."""
    import main
    draft = {"id": 10, "status": "draft", "characters": [{"name": "Анна", "relation": "бабушка"}], "email": "a@b.c", "total_price": 99000}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    with patch("main.create_payment") as m_pay:
        m_pay.return_value = {"payment_id": "pid1", "payment_url": "https://pay.example/10"}
        with patch("main.db_draft.set_draft_payment_pending"):
            query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
            query.data = "order_pay:10"
            update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
            context = MagicMock(user_data={})
            await main.handle_callback(update, context)
            m_pay.assert_called_once()
            call_text = query.edit_message_text.call_args[0][0]
            assert "https://pay.example" in call_text or "оплат" in call_text.lower()


@pytest.mark.asyncio
async def test_callback_payment_check_paid(mock_deps):
    """«Проверить оплату» при paid — set_draft_paid и сообщение об успехе."""
    import main
    draft = {"id": 2, "status": "payment_pending", "payment_id": "p2"}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    with patch("main.check_payment", return_value="paid"):
        with patch("main.db_draft.set_draft_paid") as m_set_paid:
            query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
            query.data = "payment_check:2"
            update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
            context = MagicMock(user_data={})
            await main.handle_callback(update, context)
            m_set_paid.assert_called_once_with(2)
            call_text = query.edit_message_text.call_args[0][0]
            assert "Оплата прошла" in call_text or "/list" in call_text


@pytest.mark.asyncio
async def test_voice_without_paid_blocked(mock_deps):
    """Голосовое до оплаты — блокировка, предложение /start."""
    import main
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = None  # нет paid
    update = MagicMock()
    update.effective_user = MagicMock(id=1)
    update.message = MagicMock(reply_text=AsyncMock(), voice=MagicMock(file_id="f1", duration=5))
    context = MagicMock(user_data={}, bot=MagicMock(get_file=AsyncMock(return_value=MagicMock(download_to_drive=AsyncMock()))))
    await main.handle_voice(update, context)
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "оформ" in text.lower() or "заказ" in text.lower() or "начать" in text.lower()


@pytest.mark.asyncio
async def test_list_empty(mock_deps):
    """/list при пустом списке — сообщение «Пока ничего нет»."""
    import main
    mock_deps["db"].get_user_voice_messages.return_value = []
    mock_deps["db"].get_user_photos.return_value = []
    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock()))
    context = MagicMock()
    await main.cmd_list(update, context)
    call_text = update.message.reply_text.call_args[0][0]
    assert "ничего нет" in call_text or "голосов" in call_text or "фото" in call_text


@pytest.mark.asyncio
async def test_cabinet_sets_awaiting_password(mock_deps):
    """/cabinet — просьба ввести пароль, user_data.awaiting_cabinet_password."""
    import main
    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock()))
    context = MagicMock(user_data={})
    await main.cmd_cabinet(update, context)
    assert context.user_data.get("awaiting_cabinet_password") is True
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_text_unknown_no_prepay_reply(mock_deps):
    """Произвольный текст без активного prepay — «Используйте кнопки»."""
    import main
    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="какой-то текст"))
    context = MagicMock(user_data={})  # не в режиме ввода имени/email
    mock_deps["db"].get_pending_photo.return_value = None
    await main.handle_caption_text(update, context)
    update.message.reply_text.assert_called_once()
    assert "кнопки" in update.message.reply_text.call_args[0][0] or "меню" in update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_prepay_character_name_then_relation(mock_deps):
    """Ввод имени персонажа → запрос родства → добавление в черновик."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [], "email": None}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="Анна"))
    context = MagicMock(user_data={"prepay_awaiting": "character_name", "prepay_draft_id": 1})
    await main.handle_caption_text(update, context)
    assert context.user_data.get("prepay_awaiting") == "character_relation"
    assert context.user_data.get("prepay_char_name") == "Анна"
    update.message.reply_text.assert_called()
    call_text = update.message.reply_text.call_args[0][0]
    assert "родств" in call_text.lower()


@pytest.mark.asyncio
async def test_prepay_email_invalid_reply(mock_deps):
    """Неверный email — сообщение об ошибке."""
    import main
    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="not-an-email"))
    context = MagicMock(user_data={"prepay_awaiting": "email", "prepay_draft_id": 1})
    await main.handle_caption_text(update, context)
    update.message.reply_text.assert_called()
    call_text = update.message.reply_text.call_args[0][0]
    assert "email" in call_text.lower() or "неверн" in call_text.lower()


@pytest.mark.asyncio
async def test_photo_without_paid_blocked(mock_deps):
    """Фото до оплаты — блокировка."""
    import main
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = None
    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), photo=[MagicMock(file_id="p1")]))
    context = MagicMock(user_data={})
    await main.handle_photo(update, context)
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "оформ" in text.lower() or "заказ" in text.lower() or "начать" in text.lower()


# --- TC-06: Ввод родства → кнопки Добавить/Продолжить ---
@pytest.mark.asyncio
async def test_prepay_relation_then_show_buttons(mock_deps):
    """Ввод родства → персонаж добавлен, показ кнопок Добавить ещё / Продолжить."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [], "email": None}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    mock_deps["db_draft"].get_or_create_draft.return_value = draft

    def add_char(draft_id, name, relation):
        draft["characters"] = draft.get("characters", []) + [{"name": name, "relation": relation}]
        return draft["characters"]
    mock_deps["db_draft"].add_character.side_effect = add_char

    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="мама"))
    context = MagicMock(user_data={"prepay_awaiting": "character_relation", "prepay_char_name": "Анна", "prepay_draft_id": 1})
    await main.handle_caption_text(update, context)
    mock_deps["db_draft"].add_character.assert_called_once_with(1, "Анна", "мама")
    assert update.message.reply_text.called
    text = (update.message.reply_text.call_args[0][0] if update.message.reply_text.call_args[0] else "") or ""
    assert "Персонаж" in text or "Добавить" in text or "Продолжить" in text or "мама" in text or "Анна" in text


# --- TC-07: Добавить ещё → ввод имени → родства → список 2 персонажа ---
@pytest.mark.asyncio
async def test_prepay_add_second_character(mock_deps):
    """Добавить ещё → Иван, дедушка → в списке 2 персонажа."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [{"name": "Мария", "relation": "мама"}], "email": None}

    def add_char(draft_id, name, relation):
        draft["characters"] = draft["characters"] + [{"name": name, "relation": relation}]
        return draft["characters"]
    mock_deps["db_draft"].add_character.side_effect = add_char
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    mock_deps["db_draft"].get_or_create_draft.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "cfg_add:1"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    assert context.user_data.get("prepay_awaiting") == "character_name"
    call_text = query.edit_message_text.call_args[0][0]
    assert "имя" in call_text.lower()

    update2 = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="Иван"))
    context.user_data["prepay_awaiting"] = "character_name"
    context.user_data["prepay_draft_id"] = 1
    await main.handle_caption_text(update2, context)
    assert context.user_data.get("prepay_awaiting") == "character_relation"
    assert context.user_data.get("prepay_char_name") == "Иван"

    update3 = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="дедушка"))
    await main.handle_caption_text(update3, context)
    assert len(draft["characters"]) == 2
    assert update3.message.reply_text.called
    text3 = (update3.message.reply_text.call_args[0][0] if update3.message.reply_text.call_args[0] else "") or ""
    assert "Иван" in text3 or "дедушка" in text3 or "Мария" in text3


# --- TC-08: Удалить одного персонажа ---
@pytest.mark.asyncio
async def test_prepay_delete_one_character(mock_deps):
    """Удалить одного персонажа → в списке остаётся второй."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [{"name": "Мария", "relation": "мама"}, {"name": "Иван", "relation": "дедушка"}], "email": None}

    def remove_char(draft_id, idx):
        draft["characters"] = [c for i, c in enumerate(draft["characters"]) if i != idx]
        return draft["characters"]
    mock_deps["db_draft"].remove_character.side_effect = remove_char
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "cfg_edit:1"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    call_text = query.edit_message_text.call_args[0][0]
    assert "удален" in call_text.lower() or "выберите" in call_text.lower()

    query2 = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query2.data = "cfg_del:1:0"
    update2 = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query2)
    await main.handle_callback(update2, context)
    mock_deps["db_draft"].remove_character.assert_called_once_with(1, 0)
    assert len(draft["characters"]) == 1
    assert draft["characters"][0]["name"] == "Иван"


# --- TC-09: Удалить последнего → снова запрос имени / экран без Продолжить ---
@pytest.mark.asyncio
async def test_prepay_delete_last_character_shows_add_only(mock_deps):
    """Удалить последнего персонажа → список пуст, только кнопка Добавить (без Продолжить)."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [{"name": "Мария", "relation": "мама"}], "email": None}

    def remove_char(draft_id, idx):
        draft["characters"] = []
        return draft["characters"]
    mock_deps["db_draft"].remove_character.side_effect = remove_char
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    mock_deps["db_draft"].get_or_create_draft.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "cfg_del:1:0"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    assert len(draft["characters"]) == 0
    assert query.edit_message_text.called
    call_text = (query.edit_message_text.call_args[0][0] if query.edit_message_text.call_args[0] else "") or ""
    assert "Добавить" in call_text or "персонаж" in call_text.lower()


# --- TC-10: Продолжить без персонажей запрещено ---
@pytest.mark.asyncio
async def test_prepay_continue_without_characters_forbidden(mock_deps):
    """Продолжить при 0 персонажах → ответ «Добавьте хотя бы одного»."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [], "email": None}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "cfg_continue:1"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    assert query.answer.call_count >= 1
    last_answer = query.answer.call_args_list[-1]
    msg = (last_answer[0][0] if last_answer[0] else "") or last_answer[1].get("text", "")
    assert "персонаж" in msg.lower() or "хотя бы" in msg.lower()


# --- TC-11: Продолжить → запрос email ---
@pytest.mark.asyncio
async def test_prepay_continue_shows_email_request(mock_deps):
    """Продолжить при ≥1 персонаже → запрос email."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [{"name": "Анна", "relation": "бабушка"}], "email": None}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "cfg_continue:1"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    call_text = query.edit_message_text.call_args[0][0]
    assert "email" in call_text.lower() or "почт" in call_text.lower() or "чек" in call_text.lower()


# --- TC-13: Валидный email → экран Итого ---
@pytest.mark.asyncio
async def test_prepay_valid_email_shows_summary(mock_deps):
    """Валидный email → экран Итого (список + сумма)."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [{"name": "Анна", "relation": "бабушка"}], "email": None, "total_price": 99000}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft

    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="user@example.com"))
    context = MagicMock(user_data={"prepay_awaiting": "email", "prepay_draft_id": 1})
    await main.handle_caption_text(update, context)
    mock_deps["db_draft"].update_draft_email.assert_called_once_with(1, "user@example.com")
    text = update.message.reply_text.call_args[0][0]
    assert "Итого" in text or "990" in text or "оплат" in text.lower() or "Перейти" in text


# --- TC-16: Проверить оплату при not paid ---
@pytest.mark.asyncio
async def test_callback_payment_check_not_paid(mock_deps):
    """Проверить оплату при статусе не paid → остаётся ожидание, answer с сообщением."""
    import main
    draft = {"id": 2, "status": "payment_pending", "payment_id": "p2"}
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft
    with patch("main.check_payment", return_value="pending"):
        query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
        query.data = "payment_check:2"
        update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
        context = MagicMock(user_data={})
        await main.handle_callback(update, context)
        assert query.answer.call_count >= 1
        last = query.answer.call_args_list[-1]
        assert last[1].get("show_alert") is True


# --- TC-20: Аудио/документ до оплаты блокируется ---
@pytest.mark.asyncio
async def test_audio_without_paid_blocked(mock_deps):
    """Аудио (не голос) до оплаты — блокировка."""
    import main
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = None
    update = MagicMock(
        effective_user=MagicMock(id=1),
        message=MagicMock(reply_text=AsyncMock(), audio=MagicMock(file_id="a1", file_name="x.mp3", duration=10)),
    )
    context = MagicMock(user_data={})
    await main.handle_audio(update, context)
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "оформ" in text.lower() or "заказ" in text.lower() or "начать" in text.lower()


# --- TC-22: /start при draft без персонажей → запрос имени без кнопок ---
@pytest.mark.asyncio
async def test_callback_intro_start_draft_empty_characters(mock_deps):
    """/start при draft с characters=[] → сразу запрос имени, без кнопок."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [], "email": None}
    mock_deps["db_draft"].get_or_create_draft.return_value = draft
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_start"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    assert context.user_data.get("prepay_awaiting") == "character_name"
    call_text = query.edit_message_text.call_args[0][0]
    assert "имя" in call_text.lower() and "персонаж" in call_text.lower()
    reply_markup = query.edit_message_text.call_args[1].get("reply_markup")
    assert reply_markup is not None and (not reply_markup.inline_keyboard or len(reply_markup.inline_keyboard) == 0)


# --- TC-23: /start при draft с персонажами, без email → email ---
@pytest.mark.asyncio
async def test_callback_intro_start_draft_with_characters_no_email(mock_deps):
    """/start при draft с персонажами, email=null → переход на ввод email."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [{"name": "Анна", "relation": "бабушка"}], "email": None}
    mock_deps["db_draft"].get_or_create_draft.return_value = draft
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_start"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    call_text = query.edit_message_text.call_args[0][0]
    assert "email" in call_text.lower() or "почт" in call_text.lower()


# --- TC-24: /start при draft с email → Итого ---
@pytest.mark.asyncio
async def test_callback_intro_start_draft_with_email_shows_summary(mock_deps):
    """/start при draft с email → экран Итого."""
    import main
    draft = {"id": 1, "status": "draft", "characters": [{"name": "Анна", "relation": "бабушка"}], "email": "a@b.c", "total_price": 99000}
    mock_deps["db_draft"].get_or_create_draft.return_value = draft
    mock_deps["db_draft"].get_draft_by_telegram_id.return_value = draft

    query = MagicMock(answer=AsyncMock(), edit_message_text=AsyncMock())
    query.data = "intro_start"
    update = MagicMock(effective_user=MagicMock(id=1), message=None, callback_query=query)
    context = MagicMock(user_data={})
    await main.handle_callback(update, context)
    call_text = query.edit_message_text.call_args[0][0]
    assert "Итого" in call_text or "990" in call_text or "оплат" in call_text.lower() or "Перейти" in call_text


# --- TC-27: /cabinet пароль короткий ---
@pytest.mark.asyncio
async def test_cabinet_short_password_error(mock_deps):
    """/cabinet → ввод 123 → ошибка «Пароль от 6 символов»."""
    import main
    update = MagicMock(effective_user=MagicMock(id=1), message=MagicMock(reply_text=AsyncMock(), text="123"))
    context = MagicMock(user_data={"awaiting_cabinet_password": True})
    await main.handle_caption_text(update, context)
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args[0][0]
    assert "6" in text and ("символ" in text.lower() or "пароль" in text.lower())
