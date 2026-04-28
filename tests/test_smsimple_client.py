"""Тесты клиента SMSimple (мок HTTP)."""

from unittest.mock import MagicMock, patch

import smsimple_client


def test_normalize_ru_phone():
    assert smsimple_client.normalize_ru_phone("+7 (911) 222-33-44") == "79112223344"
    assert smsimple_client.normalize_ru_phone("89112223344") == "79112223344"
    assert smsimple_client.normalize_ru_phone("9112223344") == "79112223344"


@patch("smsimple_client.config")
def test_send_sms_success(mock_cfg):
    mock_cfg.SMSIMPLE_USER = "u"
    mock_cfg.SMSIMPLE_PASSWORD = "p"
    mock_cfg.SMSIMPLE_ORIGIN_ID = "50101"
    mock_cfg.SMSIMPLE_BASE_URL = "https://smsimple.ru"

    mock_resp = MagicMock()
    mock_resp.text = "Сообщение #424242 отослано."
    mock_resp.raise_for_status = MagicMock()

    with patch("smsimple_client._session") as mock_session:
        mock_session.return_value.get.return_value = mock_resp
        r = smsimple_client.send_sms("+79161234567", "Привет")

    assert r.ok is True
    assert r.message_id == 424242
    assert r.error is None
    call_kw = mock_session.return_value.get.call_args
    assert "http_send.php" in call_kw[0][0]
    params = call_kw[1]["params"]
    assert params["phone"] == "79161234567"
    assert params["message"] == "Привет"
    assert params["or_id"] == 50101


@patch("smsimple_client.config")
def test_send_sms_error_response(mock_cfg):
    mock_cfg.SMSIMPLE_USER = "u"
    mock_cfg.SMSIMPLE_PASSWORD = "p"
    mock_cfg.SMSIMPLE_ORIGIN_ID = "1"
    mock_cfg.SMSIMPLE_BASE_URL = "https://smsimple.ru"

    mock_resp = MagicMock()
    mock_resp.text = "Ошибка при отправке: Исчерпан баланс"
    mock_resp.raise_for_status = MagicMock()

    with patch("smsimple_client._session") as mock_session:
        mock_session.return_value.get.return_value = mock_resp
        r = smsimple_client.send_sms("89161234567", "X")

    assert r.ok is False
    assert r.message_id is None
    assert "баланс" in (r.error or "")


@patch("smsimple_client.config")
def test_send_sms_missing_origin(mock_cfg):
    mock_cfg.SMSIMPLE_USER = "u"
    mock_cfg.SMSIMPLE_PASSWORD = "p"
    mock_cfg.SMSIMPLE_ORIGIN_ID = ""
    mock_cfg.SMSIMPLE_BASE_URL = "https://smsimple.ru"

    r = smsimple_client.send_sms("79161234567", "Hi")
    assert r.ok is False
    assert "подпись" in (r.error or "").lower() or "origin" in (r.error or "").lower()


@patch("smsimple_client.config")
def test_origin_id_argument_without_env(mock_cfg):
    mock_cfg.SMSIMPLE_USER = "u"
    mock_cfg.SMSIMPLE_PASSWORD = "p"
    mock_cfg.SMSIMPLE_ORIGIN_ID = ""
    mock_cfg.SMSIMPLE_BASE_URL = "https://smsimple.ru"

    mock_resp = MagicMock()
    mock_resp.text = "Сообщение #1 отослано."
    mock_resp.raise_for_status = MagicMock()

    with patch("smsimple_client._session") as mock_session:
        mock_session.return_value.get.return_value = mock_resp
        r = smsimple_client.send_sms("79161234567", "Hi", origin_id=999)

    assert r.ok is True
    params = mock_session.return_value.get.call_args[1]["params"]
    assert params["or_id"] == 999
