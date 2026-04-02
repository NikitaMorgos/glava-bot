# -*- coding: utf-8 -*-
"""
Сквозной тест SMM-пайплайна.

Покрывает полный цикл:
  Scout (Anthropic) → create_post → Journalist (OpenAI) → Editor (Anthropic) →
  _generate_image (Replicate) → статусы в БД → blueprint-маршруты (Flask).

Все внешние вызовы заменены моками — БД не нужна.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Корень проекта в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные фикстуры
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def fake_plan_id():
    return 42


@pytest.fixture()
def fake_post_id():
    return 7


@pytest.fixture()
def fake_post(fake_plan_id, fake_post_id):
    return {
        "id": fake_post_id,
        "plan_id": fake_plan_id,
        "channel": "dzen",
        "status": "journalist_done",
        "topic": "Как сохранить семейные воспоминания навсегда",
        "article_title": "Семейная книга: хранитель памяти поколений",
        "article_body": "Лид.\n\n## Раздел 1\nТекст.\n\n## Раздел 2\nТекст.\n\n**Заключение**",
        "editor_feedback": "",
        "image_prompt": "",
        "image_url": "",
        "published_url": "",
        "published_at": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Scout — генерация контент-плана
# ─────────────────────────────────────────────────────────────────────────────

class TestScout:
    """smm.scout.generate_content_plan — мокаем Anthropic + db_smm + db_admin."""

    _TOPICS_JSON = json.dumps([
        {"topic": "Тема 1", "angle": "Угол 1", "format": "статья"},
        {"topic": "Тема 2", "angle": "Угол 2", "format": "история"},
        {"topic": "Тема 3", "angle": "Угол 3", "format": "список"},
    ])

    def _make_anthropic_mock(self):
        content_block = MagicMock()
        content_block.text = self._TOPICS_JSON
        resp = MagicMock()
        resp.content = [content_block]
        client = MagicMock()
        client.messages.create.return_value = resp
        return client

    def test_returns_list_of_topics(self, fake_plan_id):
        anthropic_client = self._make_anthropic_mock()

        with (
            patch("anthropic.Anthropic", return_value=anthropic_client),
            patch("smm.scout.os.environ.get", side_effect=lambda k, d="": {
                "ANTHROPIC_API_KEY": "test-key",
                "SMM_CLAUDE_MODEL": "claude-3-5-haiku-20241022",
            }.get(k, d)),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.get_recent_reviews", return_value=[]),
            patch("smm.db_smm.set_plan_raw") as mock_set_raw,
            patch("smm.db_smm.create_post", side_effect=[10, 11, 12]) as mock_create,
        ):
            from smm.scout import generate_content_plan
            topics = generate_content_plan(fake_plan_id, manual_ideas="", num_topics=3)

        assert len(topics) == 3
        assert topics[0]["topic"] == "Тема 1"
        mock_set_raw.assert_called_once_with(fake_plan_id, topics)
        assert mock_create.call_count == 3

    def test_creates_post_per_topic(self, fake_plan_id):
        anthropic_client = self._make_anthropic_mock()

        with (
            patch("anthropic.Anthropic", return_value=anthropic_client),
            patch("smm.scout.os.environ.get", side_effect=lambda k, d="": {
                "ANTHROPIC_API_KEY": "test-key",
            }.get(k, d)),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.get_recent_reviews", return_value=["Отзыв клиента 1"]),
            patch("smm.db_smm.set_plan_raw"),
            patch("smm.db_smm.create_post", return_value=99) as mock_create,
        ):
            from smm.scout import generate_content_plan
            generate_content_plan(fake_plan_id, num_topics=3)

        assert mock_create.call_count == 3
        first_call_topic = mock_create.call_args_list[0][0][1]
        assert first_call_topic == "Тема 1"

    def test_raises_without_api_key(self, fake_plan_id):
        with (
            patch("smm.scout.os.environ.get", return_value=""),
        ):
            from smm.scout import generate_content_plan
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                generate_content_plan(fake_plan_id)

    def test_raises_on_invalid_json(self, fake_plan_id):
        content_block = MagicMock()
        content_block.text = "не JSON вообще"
        resp = MagicMock()
        resp.content = [content_block]
        client = MagicMock()
        client.messages.create.return_value = resp

        with (
            patch("anthropic.Anthropic", return_value=client),
            patch("smm.scout.os.environ.get", side_effect=lambda k, d="": {
                "ANTHROPIC_API_KEY": "test-key",
            }.get(k, d)),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.get_recent_reviews", return_value=[]),
            patch("smm.db_smm.set_plan_raw"),
        ):
            from smm.scout import generate_content_plan
            with pytest.raises(ValueError, match="JSON"):
                generate_content_plan(fake_plan_id)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Journalist — написание статьи
# ─────────────────────────────────────────────────────────────────────────────

class TestJournalist:
    """smm.journalist.write_article — мокаем OpenAI + db_smm + db_admin."""

    _ARTICLE_TEXT = (
        "# Семейная книга: хранитель памяти поколений\n\n"
        "Лид — почему это важно.\n\n"
        "## Первое воспоминание\nТекст раздела.\n\n"
        "## Как начать\nТекст раздела.\n\n"
        "**Заключение** — закажите книгу сегодня."
    )

    def _make_openai_mock(self):
        msg = MagicMock()
        msg.content = self._ARTICLE_TEXT
        choice = MagicMock()
        choice.message = msg
        resp = MagicMock()
        resp.choices = [choice]
        client = MagicMock()
        client.chat.completions.create.return_value = resp
        return client

    def test_returns_title_and_body(self, fake_post):
        openai_client = self._make_openai_mock()
        post_id = fake_post["id"]

        with (
            patch("openai.OpenAI", return_value=openai_client),
            patch("smm.journalist.os.environ.get", side_effect=lambda k, d="": {
                "OPENAI_API_KEY": "sk-test",
                "SMM_GPT_MODEL": "gpt-4o",
            }.get(k, d)),
            patch("smm.db_smm.get_post", return_value=fake_post),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.update_post") as mock_update,
        ):
            from smm.journalist import write_article
            result = write_article(post_id)

        assert result["title"] == "Семейная книга: хранитель памяти поколений"
        assert "Лид" in result["body"]
        mock_update.assert_called_once_with(
            post_id,
            article_title=result["title"],
            article_body=result["body"],
            status="journalist_done",
        )

    def test_raises_without_api_key(self, fake_post):
        with (
            patch("smm.journalist.os.environ.get", return_value=""),
        ):
            from smm.journalist import write_article
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                write_article(fake_post["id"])

    def test_raises_when_post_not_found(self):
        with (
            patch("smm.journalist.os.environ.get", side_effect=lambda k, d="": {
                "OPENAI_API_KEY": "sk-test",
            }.get(k, d)),
            patch("smm.db_smm.get_post", return_value=None),
        ):
            from smm.journalist import write_article
            with pytest.raises(ValueError, match="не найден"):
                write_article(9999)

    def test_split_title_body_no_h1(self):
        from smm.journalist import _split_title_body
        text = "Первая строка как заголовок\nОстаток текста."
        title, body = _split_title_body(text)
        assert title == "Первая строка как заголовок"
        assert body == "Остаток текста."


# ─────────────────────────────────────────────────────────────────────────────
# 3. Editor — ревью + генерация изображения
# ─────────────────────────────────────────────────────────────────────────────

class TestEditor:
    """smm.editor.review_and_generate_image — мокаем Anthropic + Replicate."""

    _EDITOR_JSON = json.dumps({
        "approved": True,
        "comment": "Хорошая статья, можно публиковать.",
        "image_prompt": "Warm family gathering around old photo albums, editorial style",
    })

    def _make_anthropic_mock(self):
        content_block = MagicMock()
        content_block.text = self._EDITOR_JSON
        resp = MagicMock()
        resp.content = [content_block]
        client = MagicMock()
        client.messages.create.return_value = resp
        return client

    def test_approved_sets_ready_status(self, fake_post, tmp_path):
        anthropic_client = self._make_anthropic_mock()
        post_id = fake_post["id"]
        fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # fake PNG

        with (
            patch("anthropic.Anthropic", return_value=anthropic_client),
            patch("smm.editor.os.environ.get", side_effect=lambda k, d="": {
                "ANTHROPIC_API_KEY": "test-key",
                "SMM_CLAUDE_MODEL": "claude-3-5-haiku-20241022",
                "SMM_IMAGES_DIR": str(tmp_path),
            }.get(k, d)),
            patch("smm.db_smm.get_post", return_value=fake_post),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.update_post") as mock_update,
            patch("replicate_client.generate_cover_image", return_value=fake_image_bytes),
        ):
            from smm.editor import review_and_generate_image
            result = review_and_generate_image(post_id)

        assert result["approved"] is True
        assert "Хорошая" in result["comment"]
        assert result["image_url"] is not None

        # Статус должен быть "ready"
        final_call = mock_update.call_args_list[-1]
        assert final_call[1]["status"] == "ready"

        # Файл должен быть записан
        saved = tmp_path / f"post_{post_id}.webp"
        assert saved.exists()
        assert saved.read_bytes() == fake_image_bytes

    def test_rejected_sets_editor_rejected_status(self, fake_post, tmp_path):
        rejected_json = json.dumps({
            "approved": False,
            "comment": "Слишком сухой тон.",
            "image_prompt": "family gathering",
        })
        content_block = MagicMock()
        content_block.text = rejected_json
        resp = MagicMock()
        resp.content = [content_block]
        client = MagicMock()
        client.messages.create.return_value = resp

        with (
            patch("anthropic.Anthropic", return_value=client),
            patch("smm.editor.os.environ.get", side_effect=lambda k, d="": {
                "ANTHROPIC_API_KEY": "test-key",
                "SMM_IMAGES_DIR": str(tmp_path),
            }.get(k, d)),
            patch("smm.db_smm.get_post", return_value=fake_post),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.update_post") as mock_update,
            patch("replicate_client.generate_cover_image", return_value=b"img"),
        ):
            from smm.editor import review_and_generate_image
            result = review_and_generate_image(fake_post["id"])

        assert result["approved"] is False
        final_call = mock_update.call_args_list[-1]
        assert final_call[1]["status"] == "editor_rejected"

    def test_image_generation_failure_does_not_crash(self, fake_post, tmp_path):
        """Если Replicate упал — статья всё равно обновляется, image_url=''.  """
        anthropic_client = self._make_anthropic_mock()

        with (
            patch("anthropic.Anthropic", return_value=anthropic_client),
            patch("smm.editor.os.environ.get", side_effect=lambda k, d="": {
                "ANTHROPIC_API_KEY": "test-key",
                "SMM_IMAGES_DIR": str(tmp_path),
            }.get(k, d)),
            patch("smm.db_smm.get_post", return_value=fake_post),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.update_post"),
            patch("replicate_client.generate_cover_image", side_effect=Exception("Replicate error")),
        ):
            from smm.editor import review_and_generate_image
            result = review_and_generate_image(fake_post["id"])

        assert result["image_url"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Полный пайплайн (Scout → Journalist → Editor)
# ─────────────────────────────────────────────────────────────────────────────

class TestFullPipeline:
    """Сквозной тест: Scout создаёт план → Journalist пишет текст → Editor проверяет."""

    def test_full_pipeline_happy_path(self, fake_plan_id, tmp_path):
        import os as _os

        # Scout mock
        topics_json = json.dumps([
            {"topic": "Семейные альбомы: почему важно хранить", "angle": "ностальгия", "format": "статья"},
        ])
        scout_content = MagicMock()
        scout_content.text = topics_json
        scout_resp = MagicMock()
        scout_resp.content = [scout_content]
        anthropic_client = MagicMock()
        anthropic_client.messages.create.return_value = scout_resp

        # Journalist mock
        article_text = (
            "# Семейные альбомы: почему важно хранить\n\n"
            "Лид.\n\n## Раздел\nТекст.\n\n**Заключение** — закажите книгу."
        )
        journalist_msg = MagicMock()
        journalist_msg.content = article_text
        journalist_choice = MagicMock()
        journalist_choice.message = journalist_msg
        journalist_resp = MagicMock()
        journalist_resp.choices = [journalist_choice]
        openai_client = MagicMock()
        openai_client.chat.completions.create.return_value = journalist_resp

        # Editor mock
        editor_json = json.dumps({
            "approved": True,
            "comment": "Отлично!",
            "image_prompt": "warm family album photo",
        })
        editor_content = MagicMock()
        editor_content.text = editor_json
        editor_resp = MagicMock()
        editor_resp.content = [editor_content]
        anthropic_editor_client = MagicMock()
        anthropic_editor_client.messages.create.return_value = editor_resp

        post_state = {
            "id": 1,
            "plan_id": fake_plan_id,
            "topic": "Семейные альбомы: почему важно хранить",
            "article_title": "",
            "article_body": "",
            "editor_feedback": "",
            "image_prompt": "",
            "image_url": "",
            "status": "draft",
        }

        def fake_update_post(pid, **fields):
            post_state.update(fields)

        def fake_get_post(pid):
            return dict(post_state)

        env_overrides = {
            "ANTHROPIC_API_KEY": "test-key",
            "OPENAI_API_KEY": "sk-test",
            "SMM_GPT_MODEL": "gpt-4o",
            "SMM_CLAUDE_MODEL": "claude-3-5-haiku-20241022",
            "SMM_IMAGES_DIR": str(tmp_path),
        }

        with (
            patch.dict(_os.environ, env_overrides),
            patch("anthropic.Anthropic", side_effect=[anthropic_client, anthropic_editor_client]),
            patch("openai.OpenAI", return_value=openai_client),
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("smm.db_smm.get_recent_reviews", return_value=[]),
            patch("smm.db_smm.set_plan_raw"),
            patch("smm.db_smm.create_post", return_value=1),
            patch("smm.db_smm.get_post", side_effect=fake_get_post),
            patch("smm.db_smm.update_post", side_effect=fake_update_post),
            patch("replicate_client.generate_cover_image", return_value=b"imgdata"),
        ):
            from smm.scout import generate_content_plan
            from smm.journalist import write_article
            from smm.editor import review_and_generate_image

            # Step 1: Scout
            topics = generate_content_plan(fake_plan_id, num_topics=1)
            assert len(topics) == 1

            # Step 2: Journalist
            art = write_article(1)
            assert art["title"] == "Семейные альбомы: почему важно хранить"
            assert post_state["status"] == "journalist_done"

            # Step 3: Editor
            rev = review_and_generate_image(1)
            assert rev["approved"] is True
            assert post_state["status"] == "ready"
            assert post_state["image_url"] == "/smm/image/post_1.webp"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Flask Blueprint маршруты
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def admin_app():
    """Минимальное Flask-приложение с SMM blueprint для тестов маршрутов."""
    import os
    os.environ.setdefault("ADMIN_SECRET_KEY", "test-secret")
    os.environ.setdefault("DATABASE_URL", "postgresql://fake/fake")

    with (
        patch("admin.db_admin.get_prompt", return_value=None),
        patch("admin.db_admin.get_prompt_history", return_value=[]),
    ):
        from flask import Flask
        app = Flask(__name__, template_folder="../admin/templates")
        app.secret_key = "test"
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        from admin.blueprints.smm import bp
        app.register_blueprint(bp)

        yield app


@pytest.fixture()
def client(admin_app):
    with admin_app.test_client() as c:
        with c.session_transaction() as sess:
            sess["username"] = "dev"
            sess["role"] = "dev"
        yield c


class TestSmmBlueprint:
    """Тесты HTTP-маршрутов SMM blueprint."""

    def test_index_returns_200(self, client):
        with (
            patch("smm.db_smm.get_all_posts", return_value=[]),
            patch("smm.db_smm.get_latest_plans", return_value=[]),
            patch("smm.db_smm.ensure_tables"),
        ):
            resp = client.get("/smm/")
        assert resp.status_code == 200

    def test_post_detail_404_on_missing_post(self, client):
        with patch("smm.db_smm.get_post", return_value=None):
            # Blueprint делает redirect на smm.index — не следуем, просто проверяем 302
            resp = client.get("/smm/post/9999", follow_redirects=False)
        assert resp.status_code == 302
        assert "/smm/" in resp.headers["Location"]

    def test_generate_plan_redirects(self, client):
        with (
            patch("smm.db_smm.create_plan", return_value=1),
            patch("smm.db_smm.ensure_tables"),
            patch("threading.Thread") as mock_thread,
        ):
            mock_thread.return_value.start = MagicMock()
            resp = client.post("/smm/generate-plan", data={
                "manual_ideas": "тест",
                "week_start": "",
                "num_topics": "3",
            })
        assert resp.status_code in (302, 200)

    def test_approve_post(self, client, fake_post):
        with (
            patch("smm.db_smm.update_post") as mock_update,
            patch("smm.db_smm.get_post", return_value=fake_post),
        ):
            resp = client.post(f"/smm/post/{fake_post['id']}/approve",
                               follow_redirects=False)
        assert resp.status_code == 302
        mock_update.assert_called_once_with(fake_post["id"], status="approved")

    def test_reject_post(self, client, fake_post):
        with (
            patch("smm.db_smm.update_post") as mock_update,
            patch("smm.db_smm.get_post", return_value=fake_post),
        ):
            resp = client.post(f"/smm/post/{fake_post['id']}/reject",
                               follow_redirects=False)
        assert resp.status_code == 302
        mock_update.assert_called_once_with(fake_post["id"], status="draft")

    def test_job_status_endpoint(self, client):
        resp = client.get("/smm/status/post_7")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "status" in data

    def test_prompts_page_returns_200(self, client):
        with (
            patch("admin.db_admin.get_prompt", return_value=None),
            patch("admin.db_admin.get_prompt_history", return_value=[]),
        ):
            resp = client.get("/smm/prompts")
        assert resp.status_code == 200

    def test_save_prompt_invalid_role(self, client):
        resp = client.post("/smm/prompts/save", data={
            "role": "invalid_role",
            "prompt_text": "Текст",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert "Неверная роль".encode() in resp.data or b"error" in resp.data.lower()

    def test_publish_requires_approved_status(self, client, fake_post):
        draft_post = dict(fake_post, status="draft")
        with patch("smm.db_smm.get_post", return_value=draft_post):
            resp = client.post(f"/smm/post/{fake_post['id']}/publish",
                               follow_redirects=True)
        assert resp.status_code == 200
        assert "Сначала одобрите".encode() in resp.data


# ─────────────────────────────────────────────────────────────────────────────
# 6. db_smm — unit-тесты без БД (мок psycopg2)
# ─────────────────────────────────────────────────────────────────────────────

class TestDbSmm:
    """Тесты функций db_smm с замоканным psycopg2."""

    def _make_conn_mock(self, fetchone_val=None, fetchall_val=None):
        cur = MagicMock()
        cur.fetchone.return_value = fetchone_val
        cur.fetchall.return_value = fetchall_val or []
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        return conn, cur

    def test_create_plan_returns_id(self):
        conn, cur = self._make_conn_mock(fetchone_val={"id": 5})
        with (
            patch("psycopg2.connect", return_value=conn),
            patch("smm.db_smm.ensure_tables"),
        ):
            from smm.db_smm import create_plan
            plan_id = create_plan("2026-04-07", "идеи")
        assert plan_id == 5

    def test_create_post_returns_id(self):
        conn, cur = self._make_conn_mock(fetchone_val={"id": 15})
        with (
            patch("psycopg2.connect", return_value=conn),
            patch("smm.db_smm.ensure_tables"),
        ):
            from smm.db_smm import create_post
            post_id = create_post(1, "Тема для поста")
        assert post_id == 15

    def test_update_post_ignores_unknown_fields(self):
        conn, cur = self._make_conn_mock()
        with patch("psycopg2.connect", return_value=conn):
            from smm.db_smm import update_post
            update_post(1, unknown_field="value", status="ready")
        # Должен выполнить только UPDATE с полем status
        assert cur.execute.called
        sql = cur.execute.call_args[0][0]
        assert "status" in sql
        assert "unknown_field" not in sql

    def test_update_post_noop_on_empty_fields(self):
        conn, cur = self._make_conn_mock()
        with patch("psycopg2.connect", return_value=conn):
            from smm.db_smm import update_post
            update_post(1, unknown_field="value")
        # Никакой UPDATE не должен быть вызван
        assert not cur.execute.called

    def test_get_recent_reviews_handles_missing_table(self):
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        cur = MagicMock()
        cur.execute.side_effect = Exception("relation does not exist")
        conn.cursor.return_value = cur

        with patch("psycopg2.connect", return_value=conn):
            from smm.db_smm import get_recent_reviews
            reviews = get_recent_reviews()
        assert reviews == []
