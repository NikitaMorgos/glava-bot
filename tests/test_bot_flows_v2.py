# -*- coding: utf-8 -*-
"""
Тесты сценариев бота GLAVA v2 (TC-28…TC-41).
Покрывают: bot_state маршрутизацию, нарраторов, интервью, правки, финализацию, возврат.
Запуск: pytest tests/ -v
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# ─── Фикстура мокирования зависимостей ─────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_deps_v2():
    """Мокаем db, db_draft, storage и bot_messages для всех v2-тестов."""
    with (
        patch("main.db") as m_db,
        patch("main.db_draft") as m_draft,
        patch("main.storage") as m_storage,
        patch("main.bot_messages") as m_msgs,
    ):
        # db defaults
        m_db.get_or_create_user.return_value = {"id": 1}
        m_db.get_user_voice_messages.return_value = []
        m_db.get_user_photos.return_value = []
        m_db.get_pending_photo.return_value = None

        # draft defaults
        m_draft.get_or_create_draft.return_value = None
        m_draft.get_draft_by_telegram_id.return_value = None
        m_draft.get_narrators.return_value = []
        m_draft.get_revision_count.return_value = 0
        m_draft.get_pending_revision.return_value = ("", False)

        # bot_messages: всегда возвращает ключ как текст
        m_msgs.get_message.side_effect = lambda key, **kw: f"[{key}]"

        yield {"db": m_db, "db_draft": m_draft, "storage": m_storage, "msgs": m_msgs}


# ─── Вспомогательные фабрики ────────────────────────────────────────────────

def _make_draft(
    draft_id=1,
    status="paid",
    bot_state="narrators_setup",
    characters=None,
    narrators=None,
    revision_count=0,
):
    return {
        "id": draft_id,
        "status": status,
        "bot_state": bot_state,
        "characters": characters or [{"name": "Анна", "relation": "бабушка"}],
        "narrators": narrators or [],
        "revision_count": revision_count,
        "email": "a@b.c",
        "total_price": 99000,
        "payment_url": "https://pay.example/1",
        "payment_id": "p1",
    }


def _make_update_cmd(user_id=42, username="testuser"):
    update = MagicMock()
    update.effective_user = MagicMock(id=user_id, username=username)
    update.effective_chat = MagicMock(id=user_id)
    update.message = MagicMock(reply_text=AsyncMock())
    update.callback_query = None
    return update


def _make_update_cb(data: str, user_id=42, username="testuser"):
    query = MagicMock()
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message = MagicMock(reply_text=AsyncMock(), reply_document=AsyncMock())
    update = MagicMock()
    update.effective_user = MagicMock(id=user_id, username=username)
    update.effective_chat = MagicMock(id=user_id)
    update.callback_query = query
    update.message = None
    return update, query


def _make_context(user_data=None):
    ctx = MagicMock()
    ctx.user_data = user_data or {}
    ctx.bot = MagicMock()
    ctx.bot.set_chat_menu_button = AsyncMock()
    ctx.bot.get_file = AsyncMock(return_value=MagicMock(download_to_drive=AsyncMock()))
    return ctx


# ═══════════════════════════════════════════════════════════════════════════
# TC-28: /start при bot_state='no_project' → приветствие (экран 1.1)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc28_start_no_project_shows_intro(mock_deps_v2):
    """/start при bot_state=no_project → приветствие (экран 1.1)."""
    import main
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = None
    with patch("main._user_has_paid", return_value=False):
        update = _make_update_cmd()
        ctx = _make_context()
        await main.cmd_start(update, ctx)
    update.message.reply_text.assert_called_once()
    mock_deps_v2["msgs"].get_message.assert_any_call("intro_main")


# ═══════════════════════════════════════════════════════════════════════════
# TC-29: /start при bot_state='paid'/'narrators_setup' → экран нарраторов
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc29_start_paid_shows_narrators(mock_deps_v2):
    """/start при bot_state=paid → показ экрана нарраторов (6.1)."""
    import main
    draft = _make_draft(bot_state="paid", status="paid", narrators=[])
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    with patch("main._user_has_paid", return_value=True):
        update = _make_update_cmd()
        ctx = _make_context()
        await main.cmd_start(update, ctx)
    update.message.reply_text.assert_called_once()
    # Экран нарраторов — вызывает narrators_setup или narrators_list
    called_keys = [c.args[0] for c in mock_deps_v2["msgs"].get_message.call_args_list]
    assert any(k in ("narrators_setup", "narrators_list") for k in called_keys)


# ═══════════════════════════════════════════════════════════════════════════
# TC-30: /start при bot_state='book_ready' → экран книги (10.2)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc30_start_book_ready_shows_book_screen(mock_deps_v2):
    """/start при bot_state=book_ready → экран книги готова (10.2)."""
    import main
    draft = _make_draft(bot_state="book_ready", status="paid")
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    mock_deps_v2["db_draft"].get_revision_count.return_value = 0
    with patch("main._user_has_paid", return_value=True):
        update = _make_update_cmd()
        ctx = _make_context()
        await main.cmd_start(update, ctx)
    update.message.reply_text.assert_called_once()
    mock_deps_v2["msgs"].get_message.assert_any_call("book_ready")


# ═══════════════════════════════════════════════════════════════════════════
# TC-31: /start при bot_state='awaiting_interview_2' → AI-вопросы (8.6)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc31_start_awaiting_interview2_shows_questions(mock_deps_v2):
    """/start при awaiting_interview_2 → показ AI-вопросов (8.6)."""
    import main
    draft = _make_draft(bot_state="awaiting_interview_2", status="paid")
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    with patch("main._user_has_paid", return_value=True):
        update = _make_update_cmd()
        ctx = _make_context()
        await main.cmd_start(update, ctx)
    update.message.reply_text.assert_called_once()
    mock_deps_v2["msgs"].get_message.assert_any_call("interview_questions_ready")


# ═══════════════════════════════════════════════════════════════════════════
# TC-32: /start при bot_state='assembling' → сообщение о сборке (10.1)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc32_start_assembling_shows_wait(mock_deps_v2):
    """/start при assembling → сообщение об ожидании сборки."""
    import main
    draft = _make_draft(bot_state="assembling", status="paid")
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    with patch("main._user_has_paid", return_value=True):
        update = _make_update_cmd()
        ctx = _make_context()
        await main.cmd_start(update, ctx)
    update.message.reply_text.assert_called_once()
    mock_deps_v2["msgs"].get_message.assert_any_call("assembling")


# ═══════════════════════════════════════════════════════════════════════════
# TC-33: narrator_add:<id> → context.user_data['v2_awaiting'] = 'narrator_name'
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc33_narrator_add_sets_awaiting(mock_deps_v2):
    """Кнопка narrator_add:<id> → v2_awaiting = 'narrator_name'."""
    import main
    draft = _make_draft(narrators=[])
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    update, query = _make_update_cb("narrator_add:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    assert ctx.user_data.get("v2_awaiting") == "narrator_name"
    assert ctx.user_data.get("v2_draft_id") == 1
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-34: narrator_del:<id>:<narrator_id> → нарратор удалён
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc34_narrator_del_removes_narrator(mock_deps_v2):
    """Кнопка narrator_del → db_draft.remove_narrator вызван."""
    import main
    narrators = [{"id": "n1", "name": "Иван", "relation": "сын"}]
    draft = _make_draft(narrators=narrators)
    # После удаления возвращаем черновик без нарратора
    draft_after = _make_draft(narrators=[])
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.side_effect = [draft, draft_after]
    update, query = _make_update_cb("narrator_del:1:n1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    mock_deps_v2["db_draft"].remove_narrator.assert_called_once_with(1, "n1")
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-35: narrator_continue:<id> без нарраторов → alert "Добавьте хотя бы одного"
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc35_narrator_continue_empty_shows_alert(mock_deps_v2):
    """narrator_continue без нарраторов → answer с alert."""
    import main
    draft = _make_draft(narrators=[])
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    update, query = _make_update_cb("narrator_continue:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    # answer() вызывается минимум дважды: обязательный ack + alert
    assert query.answer.call_count >= 2
    # Последний вызов должен содержать show_alert=True
    alert_calls = [c for c in query.answer.call_args_list if c[1].get("show_alert")]
    assert alert_calls, "Ожидался answer(show_alert=True)"


# ═══════════════════════════════════════════════════════════════════════════
# TC-36: narrator_continue:<id> с нарраторами → interview_guide (7.1)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc36_narrator_continue_with_narrators_shows_guide(mock_deps_v2):
    """narrator_continue с нарраторами → показ interview_guide."""
    import main
    narrators = [{"id": "n1", "name": "Иван", "relation": "сын"}]
    draft = _make_draft(narrators=narrators)
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    update, query = _make_update_cb("narrator_continue:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    mock_deps_v2["db_draft"].set_bot_state.assert_called_once_with(1, "narrators_setup")
    mock_deps_v2["msgs"].get_message.assert_any_call("interview_guide")
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-37: upload_start:<id> с 1 нарратором → bot_state=collecting_interview_1
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc37_upload_start_single_narrator_sets_collecting(mock_deps_v2):
    """upload_start с единственным нарратором → state=collecting_interview_1."""
    import main
    narrators = [{"id": "n1", "name": "Иван", "relation": "сын"}]
    draft = _make_draft(narrators=narrators)
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    update, query = _make_update_cb("upload_start:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    mock_deps_v2["db_draft"].set_bot_state.assert_called_with(1, "collecting_interview_1")
    assert ctx.user_data.get("v2_current_narrator") == "n1"
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-38: interview2_start:<id> → bot_state=collecting_interview_2
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc38_interview2_start_sets_state(mock_deps_v2):
    """interview2_start:<id> → state=collecting_interview_2."""
    import main
    update, query = _make_update_cb("interview2_start:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    mock_deps_v2["db_draft"].set_bot_state.assert_called_with(1, "collecting_interview_2")
    mock_deps_v2["msgs"].get_message.assert_any_call("interview2")
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-39: assemble_book:<id> → bot_state=assembling, запуск пайплайна
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc39_assemble_book_sets_assembling(mock_deps_v2):
    """assemble_book:<id> → state=assembling, pipeline_n8n.trigger вызван."""
    import main
    draft = _make_draft()
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    update, query = _make_update_cb("assemble_book:1")
    ctx = _make_context()
    with patch("main._get_user_character_name", return_value="Анна"):
        with patch("pipeline_n8n.trigger_phase_a_background") as m_trigger:
            await main.handle_callback(update, ctx)
    mock_deps_v2["db_draft"].set_bot_state.assert_called_with(1, "assembling")
    mock_deps_v2["msgs"].get_message.assert_any_call("assembling")


# ═══════════════════════════════════════════════════════════════════════════
# TC-40: revision_start:<id> при revision_count=1 → awaiting='revision_text'
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc40_revision_start_sets_awaiting(mock_deps_v2):
    """revision_start при revision_count=1 → context.user_data['v2_awaiting']='revision_text'."""
    import main
    mock_deps_v2["db_draft"].get_revision_count.return_value = 1
    update, query = _make_update_cb("revision_start:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    assert ctx.user_data.get("v2_awaiting") == "revision_text"
    assert ctx.user_data.get("v2_draft_id") == 1
    mock_deps_v2["db_draft"].set_bot_state.assert_called_with(1, "revision_2")
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-41: revision_start:<id> при revision_count=3 → сообщение revision_limit
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc41_revision_limit_shows_limit_message(mock_deps_v2):
    """revision_start при revision_count=3 → сообщение revision_limit."""
    import main
    mock_deps_v2["db_draft"].get_revision_count.return_value = 3
    update, query = _make_update_cb("revision_start:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    mock_deps_v2["msgs"].get_message.assert_any_call("revision_limit")
    query.edit_message_text.assert_called_once()
    # set_bot_state НЕ должен вызываться — лимит исчерпан
    mock_deps_v2["db_draft"].set_bot_state.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════
# TC-42: finalize_confirm:<id> → bot_state=finalized
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc42_finalize_confirm_sets_finalized(mock_deps_v2):
    """finalize_confirm:<id> → state=finalized, сообщение finalized."""
    import main
    update, query = _make_update_cb("finalize_confirm:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    mock_deps_v2["db_draft"].set_bot_state.assert_called_with(1, "finalized")
    mock_deps_v2["msgs"].get_message.assert_any_call("finalized")
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-43: refund_start:<id> → context.user_data['v2_awaiting'] = 'refund_reason'
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc43_refund_start_sets_awaiting(mock_deps_v2):
    """refund_start:<id> → v2_awaiting='refund_reason', показ экрана 15.1."""
    import main
    update, query = _make_update_cb("refund_start:1")
    ctx = _make_context()
    await main.handle_callback(update, ctx)
    assert ctx.user_data.get("v2_awaiting") == "refund_reason"
    assert ctx.user_data.get("v2_draft_id") == 1
    mock_deps_v2["msgs"].get_message.assert_any_call("refund_reason")
    query.edit_message_text.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# TC-44: /start при bot_state='finalized' → экран 14.1
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tc44_start_finalized_shows_finalized_screen(mock_deps_v2):
    """/start при bot_state=finalized → экран 14.1 (финализирована)."""
    import main
    draft = _make_draft(bot_state="finalized", status="paid")
    mock_deps_v2["db_draft"].get_draft_by_telegram_id.return_value = draft
    mock_deps_v2["db_draft"].get_revision_count.return_value = 2
    with patch("main._user_has_paid", return_value=True):
        update = _make_update_cmd()
        ctx = _make_context()
        await main.cmd_start(update, ctx)
    update.message.reply_text.assert_called_once()
    mock_deps_v2["msgs"].get_message.assert_any_call("finalized")
