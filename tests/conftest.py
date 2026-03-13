# -*- coding: utf-8 -*-
"""Фикстуры для тестов бота: моки Update, Context и зависимостей (db, db_draft, storage)."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = 12345
    u.username = "testuser"
    return u


@pytest.fixture
def mock_message(mock_user):
    m = MagicMock()
    m.from_user = mock_user
    m.reply_text = AsyncMock()
    m.text = ""
    return m


@pytest.fixture
def mock_update(mock_user, mock_message):
    u = MagicMock(spec_set=["effective_user", "message", "callback_query"])
    u.effective_user = mock_user
    u.message = mock_message
    u.callback_query = None
    return u


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.user_data = {}
    ctx.bot = MagicMock()
    ctx.bot.get_file = AsyncMock(return_value=MagicMock(download_to_drive=AsyncMock()))
    return ctx


@pytest.fixture
def mock_callback_query(mock_user):
    q = MagicMock()
    q.answer = AsyncMock()
    q.edit_message_text = AsyncMock()
    q.data = ""
    return q


def make_callback_update(mock_user, callback_data: str, mock_callback_query):
    """Update с callback_query (кнопки)."""
    u = MagicMock()
    u.effective_user = mock_user
    u.message = None
    u.callback_query = mock_callback_query
    mock_callback_query.data = callback_data
    return u
