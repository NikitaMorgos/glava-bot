"""
Worker обработки проекта — запускается из Flask через subprocess.Popen
сразу при нажатии «Начать обработку».

Реальный flow:
1. Создать workspace в TEMP
2. Скачать все voice_messages и photos из S3
3. Сгенерировать input/project.yaml из БД (subject, narrators, voices, photos)
4. Запустить glava transcribe для каждого аудио
5. Запустить glava extract-facts для каждого файла
6. Запустить glava build-all
7. Опубликовать questions.md → publish_questions
8. Опубликовать book.pdf + book.html → publish_book
9. Очистить workspace

Использование (Flask делает автоматически):
  python -m cabinet.process_project --project-id 8

Конфиг:
  GLAVA_PIPELINE_PATH — путь к пакету glava (по умолчанию C:/Projects/glava)
  GLAVA_PIPELINE_ENV — путь к .env файлу glava с API-ключами (по умолчанию <GLAVA>/.env)
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import db
import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [proc-worker] %(message)s",
)
logger = logging.getLogger("process_project")

# Конфиг pipeline
GLAVA_PIPELINE_PATH = Path(
    os.environ.get("GLAVA_PIPELINE_PATH", r"C:\Projects\glava")
).resolve()
GLAVA_PIPELINE_ENV = Path(
    os.environ.get("GLAVA_PIPELINE_ENV", str(GLAVA_PIPELINE_PATH / ".env"))
)

# Видимые клиенту стадии. Набор зависит от раунда:
# - Round 1: останавливаемся после coverage и публикуем вопросы.
# - Round 2+: после coverage идём дальше и собираем книгу.
STAGES_ROUND_1 = [
    ("transcribe", "Расшифровка интервью"),
    ("extract", "Анализ фактов"),
    ("coverage", "Поиск пробелов в истории"),
]
STAGES_ROUND_2_PLUS = STAGES_ROUND_1 + [
    ("compose", "Написание текста"),
    ("layout", "Финальная вёрстка"),
]

# Маппинг real-stage-marker → visible-stage-key
MARKER_TO_STAGE = {
    "merge-facts": "extract",
    "canonize-facts": "extract",
    "normalize-hero-surname": "extract",
    "route-facts": "compose",
    "split-character-stories": "compose",
    "detect-proper-nouns": "compose",
    "assemble-key-dates": "compose",
    "assemble-life-story": "compose",
    "assemble-character": "compose",
    "assemble-interesting-stories": "compose",
    "assemble-epilogue": "compose",
    "assemble-contributors": "layout",
    "assemble-photo-album": "layout",
    "assign-chapter-photos": "layout",
    "assemble-cover": "layout",
    "build-book": "layout",
    "render-pdf": "layout",
}


def _glava_env() -> dict:
    """env с API-ключами glava + PYTHONPATH к пакету."""
    env = dict(os.environ)
    if GLAVA_PIPELINE_ENV.exists():
        for raw in GLAVA_PIPELINE_ENV.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            env[k.strip()] = v
    # Добавим путь к пакету glava
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(GLAVA_PIPELINE_PATH) + (
        os.pathsep + existing_pp if existing_pp else ""
    )
    return env


def _run_glava(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Запускает `python -m glava.cli <args>` в указанной cwd. Возвращает (rc, stdout, stderr)."""
    cmd = [sys.executable, "-m", "glava.cli", *args]
    logger.info("CMD: %s (cwd=%s)", " ".join(cmd), cwd)
    proc = subprocess.run(
        cmd, cwd=str(cwd), env=_glava_env(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.stdout:
        for line in proc.stdout.splitlines()[-20:]:
            logger.info("  out: %s", line)
    if proc.returncode != 0 and proc.stderr:
        for line in proc.stderr.splitlines()[-20:]:
            logger.warning("  err: %s", line)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _slugify_respondent(name: str, idx: int) -> str:
    """ID для project.yaml respondents (валидный yaml ключ)."""
    # Берём первое слово, транслитерируем грубо, fallback на rN
    base = re.sub(r"[^a-z0-9]", "", name.lower().split()[0]) if name.strip() else ""
    return base or f"r{idx}"


def _ext_from_key(storage_key: str, default: str = ".bin") -> str:
    """Определяем расширение по storage_key."""
    suffix = Path(storage_key).suffix.lower()
    return suffix if suffix else default


def _prepare_workspace(project_id: int) -> tuple[Path, dict]:
    """
    Создаёт workspace и project.yaml, скачивает все файлы.
    Возвращает (workspace_path, project_info).
    """
    workspace = Path(tempfile.gettempdir()) / "glava-jobs" / f"project-{project_id}"
    # НЕ удаляем workspace — build-all идемпотентен и при retry должен
    # подхватить готовые стадии. Скачивание файлов делаем idempotently ниже.
    input_dir = workspace / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)

    # Копируем .env с API-ключами в workspace — pydantic-settings glava читает .env из cwd
    if GLAVA_PIPELINE_ENV.exists():
        shutil.copy(GLAVA_PIPELINE_ENV, workspace / ".env")
        logger.info(".env скопирован из %s", GLAVA_PIPELINE_ENV)
    else:
        logger.error("Не найден .env с API-ключами: %s", GLAVA_PIPELINE_ENV)
        raise RuntimeError(f".env с API-ключами не найден: {GLAVA_PIPELINE_ENV}")

    # 1. Тянем данные из БД
    subject = None
    heroes = db.get_project_heroes(project_id)
    for h in heroes:
        if h.get("role") == "subject":
            subject = h
            break
    if not subject:
        raise RuntimeError(f"Project {project_id}: subject не найден")

    narrators = [h for h in heroes if h.get("role") != "subject"]
    voices = db.get_project_voices(project_id)
    photos = db.get_project_photos(project_id)

    # 2. Скачиваем voices → input/interview_<id>.<ext>
    s3 = storage.get_s3_client()
    import config as _config
    bucket = _config.S3_BUCKET_NAME

    voice_files: list[tuple[str, dict]] = []
    for v in voices:
        ext = _ext_from_key(v["storage_key"])
        local_name = f"interview_{v['id']}{ext}"
        local_path = input_dir / local_name
        if local_path.exists():
            logger.info("Уже скачано, пропускаю: %s", local_name)
        else:
            logger.info("Скачиваю voice %s → %s", v["storage_key"], local_name)
            s3.download_file(Bucket=bucket, Key=v["storage_key"], Filename=str(local_path))
        voice_files.append((local_name, v))

    # photo_files: только photo_type='photo'. Документы (photo_type='document') —
    # награды/грамоты/аттестаты — НЕ идут в photos манифеста (их нельзя ставить как
    # opener главы). Скачиваем их всё равно — потом подключим как appendix.
    photo_files: list[tuple[str, dict]] = []
    doc_files: list[tuple[str, dict]] = []
    for p in photos:
        ext = _ext_from_key(p["storage_key"], ".jpg")
        local_name = f"photo_{p['id']}{ext}"
        local_path = input_dir / local_name
        if local_path.exists():
            logger.info("Уже скачано, пропускаю: %s", local_name)
        else:
            logger.info("Скачиваю photo %s → %s", p["storage_key"], local_name)
            s3.download_file(Bucket=bucket, Key=p["storage_key"], Filename=str(local_path))
        if p.get("photo_type") == "document":
            doc_files.append((local_name, p))
        else:
            photo_files.append((local_name, p))
    logger.info("Photos: %d иллюстраций, %d документов (документы пока не в pipeline)",
                len(photo_files), len(doc_files))

    # 3. Генерим project.yaml
    yaml_lines = ["hero:"]
    yaml_lines.append(f"  name: {subject['name']}")
    # birth_year и т.п. у нас нет в БД — оставим пустыми или вытащим из years
    if subject.get("years"):
        # пытаемся вытащить год из "1925-2010"
        m = re.search(r"(\d{4})", subject["years"])
        if m:
            yaml_lines.append(f"  birth_year: {m.group(1)}")

    yaml_lines.append("")
    yaml_lines.append("respondents:")
    narrator_id_by_hero_id: dict[int, str] = {}
    for idx, n in enumerate(narrators):
        rid = _slugify_respondent(n["name"], idx)
        # уникальность
        suffix = 1
        base_rid = rid
        while rid in narrator_id_by_hero_id.values():
            rid = f"{base_rid}{suffix}"
            suffix += 1
        narrator_id_by_hero_id[n["id"]] = rid
        yaml_lines.append(f"  - id: {rid}")
        yaml_lines.append(f"    name: {n['name']}")
        if n.get("relation"):
            yaml_lines.append(f"    relation: {n['relation']}")

    yaml_lines.append("")
    yaml_lines.append("recordings:")
    for local_name, v in voice_files:
        yaml_lines.append(f"  - file: {local_name}")
        if v.get("hero_id") and v["hero_id"] in narrator_id_by_hero_id:
            yaml_lines.append(f"    respondent: {narrator_id_by_hero_id[v['hero_id']]}")
        else:
            yaml_lines.append(f"    respondent: unknown")

    if photo_files:
        yaml_lines.append("")
        yaml_lines.append("photos:")
        for local_name, p in photo_files:
            yaml_lines.append(f"  - file: {local_name}")
            # pipeline требует caption всегда — если у фото подписи нет,
            # пишем пустую строку (иначе assemble-cover/render-pdf упадут
            # ValidationError: Field required).
            caption = (p.get("caption") or "").replace('"', "'")
            yaml_lines.append(f'    caption: "{caption}"')

    yaml_text = "\n".join(yaml_lines) + "\n"
    (input_dir / "project.yaml").write_text(yaml_text, encoding="utf-8")
    logger.info("project.yaml создан, %d voices, %d photos", len(voice_files), len(photo_files))

    return workspace, {
        "subject": subject,
        "narrators": narrators,
        "voices": voices,
        "photos": photos,
        "voice_files": voice_files,
        "photo_files": photo_files,
        "narrator_id_by_hero_id": narrator_id_by_hero_id,
    }


def _run_transcribe(workspace: Path, info: dict, project_id: int, round_number: int) -> bool:
    """
    Прогоняет glava transcribe по каждому аудио.
    Для текстовых материалов (.txt/.md/.rtf/.docx/.pdf) — вместо AssemblyAI
    вызывает glava import-transcript: конвертирует текст в Transcript JSON,
    чтобы дальнейший extract-facts мог его прочитать одинаково.
    """
    db.update_job_stage(project_id, round_number, "transcribe", "running")
    audio_exts = {".mp3", ".ogg", ".m4a", ".wav", ".opus", ".oga"}
    text_exts  = {".txt", ".md", ".rtf", ".docx", ".doc", ".pdf"}
    failed = []
    for local_name, _ in info["voice_files"]:
        suffix = Path(local_name).suffix.lower()
        if suffix in audio_exts:
            rc, _, _ = _run_glava(["transcribe", f"input/{local_name}"], workspace)
        elif suffix in text_exts:
            # Готовый текст → Transcript JSON без AssemblyAI
            rc, _, _ = _run_glava(["import-transcript", f"input/{local_name}"], workspace)
        else:
            logger.info("Skipping unsupported file: %s", local_name)
            continue
        if rc != 0:
            failed.append(local_name)
    if failed:
        db.update_job_stage(
            project_id, round_number, "transcribe", "failed",
            error_message=f"Не транскрибировались: {', '.join(failed)}",
        )
        return False
    db.update_job_stage(project_id, round_number, "transcribe", "done")
    return True


def _run_extract(workspace: Path, info: dict, project_id: int, round_number: int) -> bool:
    """Извлекает факты по всем имеющимся транскриптам."""
    db.update_job_stage(project_id, round_number, "extract", "running")
    failed = []
    narrator_id_by_hero = info.get("narrator_id_by_hero_id", {})
    # Маппинг hero_id → объект narrator (для name/relation)
    narrators_by_id = {n["id"]: n for n in info["narrators"]}
    fallback_narrator = info["narrators"][0] if info["narrators"] else None

    for local_name, voice in info["voice_files"]:
        # Все интервью — и аудио, и текст — после _run_transcribe уже
        # имеют JSON-транскрипт в output/_intermediate/transcripts/<stem>.json.
        # (аудио → через transcribe / AssemblyAI, текст → через import-transcript).
        transcript_path = (
            workspace / "output" / "_intermediate" / "transcripts"
            / (Path(local_name).stem + ".json")
        )
        if not transcript_path.exists():
            failed.append(f"{local_name} (нет транскрипта)")
            continue
        arg = str(transcript_path.relative_to(workspace)).replace("\\", "/")

        # Подбираем narrator
        narrator = narrators_by_id.get(voice.get("hero_id")) or fallback_narrator
        if not narrator:
            failed.append(f"{local_name} (нет рассказчика)")
            continue
        respondent_id = narrator_id_by_hero.get(narrator["id"])
        if not respondent_id:
            failed.append(f"{local_name} (нет id рассказчика)")
            continue

        cmd_args = [
            "extract-facts", arg,
            "--respondent-id", respondent_id,
            "--respondent-name", narrator["name"],
            "--respondent-relation", narrator.get("relation") or "родственник",
        ]
        # Прокидываем героя — без --hero-name pipeline упадёт на Hero(name=None)
        subject = info.get("subject") or {}
        if subject.get("name"):
            cmd_args += ["--hero-name", subject["name"]]
        if subject.get("years"):
            m = re.search(r"(\d{4})", subject["years"])
            if m:
                cmd_args += ["--hero-birth", m.group(1)]
        rc, _, _ = _run_glava(cmd_args, workspace)
        if rc != 0:
            failed.append(local_name)
    if failed:
        db.update_job_stage(
            project_id, round_number, "extract", "failed",
            error_message=f"extract-facts упал на: {', '.join(failed)}",
        )
        return False
    db.update_job_stage(project_id, round_number, "extract", "done")
    return True


def _run_coverage(workspace: Path, info: dict, project_id: int, round_number: int) -> bool:
    """
    Запускает glava check-coverage — генерит output/_intermediate/questions.md и review.md.
    """
    db.update_job_stage(project_id, round_number, "coverage", "running")
    cmd_args = ["check-coverage"]
    subject = info.get("subject") or {}
    if subject.get("name"):
        cmd_args += ["--hero-name", subject["name"]]
    if subject.get("years"):
        m = re.search(r"(\d{4})", subject["years"])
        if m:
            cmd_args += ["--hero-birth", m.group(1)]
    rc, _, _ = _run_glava(cmd_args, workspace)
    if rc != 0:
        db.update_job_stage(
            project_id, round_number, "coverage", "failed",
            error_message=f"check-coverage exit code {rc}",
        )
        return False
    db.update_job_stage(project_id, round_number, "coverage", "done")
    return True


def _run_build_all(workspace: Path, project_id: int, round_number: int) -> bool:
    """
    Запускает glava build-all, стримит stdout и обновляет compose/layout стадии
    по мере того как pipeline объявляет о подстадиях.

    Успех определяем по rc==0 И наличию output/book.pdf — НЕ по маркеру в stdout
    (на Windows кириллица в stdout может корраптиться, маркер ГОТОВО: не найдётся).
    """
    db.update_job_stage(project_id, round_number, "compose", "running")
    cmd = [sys.executable, "-m", "glava.cli", "build-all"]
    proc = subprocess.Popen(
        cmd, cwd=str(workspace), env=_glava_env(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    current_visible = "compose"
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip()
        if not line:
            continue
        logger.info("  build-all: %s", line)
        # >>stage-name маркер — английский, не страдает от encoding
        m = re.search(r">>([a-z\-]+)", line)
        if m:
            stage = m.group(1)
            visible = MARKER_TO_STAGE.get(stage)
            if visible and visible != current_visible:
                db.update_job_stage(project_id, round_number, current_visible, "done")
                db.update_job_stage(project_id, round_number, visible, "running")
                current_visible = visible
    rc = proc.wait()
    pdf_path = workspace / "output" / "book.pdf"
    if rc != 0 or not pdf_path.exists():
        err = (
            f"glava build-all: rc={rc}, pdf_exists={pdf_path.exists()}"
        )
        db.update_job_stage(
            project_id, round_number, current_visible, "failed",
            error_message=err,
        )
        return False
    db.update_job_stage(project_id, round_number, current_visible, "done")
    return True


def _notify_owner(
    project_id: int,
    kind: str,
    hero_name: str | None = None,
    book_version: int | None = None,
) -> None:
    """
    Отправляет email владельцу проекта. kind: 'questions' или 'book'.
    Тихо игнорирует ошибки — уведомление не должно ронять сборку.
    """
    try:
        email = db.get_project_owner_email(project_id)
        if not email:
            logger.info("Владелец проекта %s без email — уведомление пропущено", project_id)
            return
        from cabinet.email_sender import send_questions_ready, send_book_ready
        if kind == "questions":
            ok = send_questions_ready(email, project_id, hero_name)
        elif kind == "book":
            ok = send_book_ready(email, project_id, hero_name, book_version)
        else:
            logger.warning("Неизвестный kind уведомления: %s", kind)
            return
        logger.info("Email-уведомление (%s) для %s: %s", kind, email, "OK" if ok else "FAIL")
    except Exception as e:
        logger.exception("Не удалось отправить email-уведомление (%s): %s", kind, e)


def _publish_book_only(workspace: Path, project_id: int) -> None:
    """Публикует book.pdf (+ опц. book.html + book.json) в кабинет.
    questions уже опубликованы в process()."""
    output_dir = workspace / "output"
    pdf_path = output_dir / "book.pdf"
    html_path = output_dir / "book.html"
    book_json_path = output_dir / "book.json"  # структура для веб-редактора
    if pdf_path.exists():
        try:
            from cabinet.publish_book import publish as publish_book_fn
            publish_book_fn(
                pdf_path=pdf_path,
                project_id=project_id,
                notes="автосборка",
                html_path=html_path if html_path.exists() else None,
                book_json_path=book_json_path if book_json_path.exists() else None,
            )
            logger.info("book.pdf опубликован")
            # Сбрасываем materials_submitted_at → клиент может догрузить
            # новые материалы и запустить Round 3 (пересборку).
            try:
                db.reset_project_submission(project_id)
                logger.info("materials_submitted_at сброшен — цикл открыт для новых материалов")
            except Exception as e:
                logger.warning("reset_project_submission failed: %s", e)
        except Exception as e:
            logger.exception("publish_book failed: %s", e)
    else:
        logger.warning("output/book.pdf не найден — публикация книги пропущена")


def process(project_id: int) -> int:
    logger.info("=== Starting processing of project_id=%s ===", project_id)
    logger.info("GLAVA_PIPELINE_PATH=%s exists=%s",
                GLAVA_PIPELINE_PATH, GLAVA_PIPELINE_PATH.exists())

    # Проверка проекта
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT owner_user_id, materials_submitted_at FROM projects WHERE id = %s",
                (project_id,),
            )
            row = cur.fetchone()
    if not row:
        logger.error("Project %s not found", project_id)
        return 1
    if row[1] is None:
        logger.error("Project %s has no materials_submitted_at", project_id)
        return 1

    round_number = db.get_current_round_number(project_id)
    logger.info("Round number: %s", round_number)
    stages_for_round = STAGES_ROUND_1 if round_number == 1 else STAGES_ROUND_2_PLUS
    db.init_job_stages(project_id, round_number, stages_for_round)

    workspace = None
    try:
        workspace, info = _prepare_workspace(project_id)
        if not _run_transcribe(workspace, info, project_id, round_number):
            return 1
        if not _run_extract(workspace, info, project_id, round_number):
            return 1
        if not _run_coverage(workspace, info, project_id, round_number):
            return 1

        # Round 1: останавливаемся после coverage. Публикуем только questions.md.
        # Клиент увидит «Доп. вопросы готовы», догрузит ответы, нажмёт «Начать» снова — round 2.
        hero_name = info["subject"]["name"] if info.get("subject") else None
        questions_path = workspace / "output" / "_intermediate" / "questions.md"
        questions_published = False
        if questions_path.exists():
            try:
                from cabinet.publish_questions import publish as publish_questions_fn
                # В round 1 сбрасываем submission (клиент уходит ждать ответов).
                # В round 2+ НЕ сбрасываем — мы продолжаем processing и собираем книгу.
                publish_questions_fn(
                    questions_path, project_id,
                    notes=f"round {round_number}",
                    reset_submission=(round_number == 1),
                )
                logger.info("questions.md опубликованы (round %s)", round_number)
                questions_published = True
            except Exception as e:
                logger.exception("publish_questions failed: %s", e)
        else:
            logger.warning("questions.md не найден после coverage")

        if round_number == 1:
            # Email клиенту: готовы уточняющие вопросы
            if questions_published:
                _notify_owner(
                    project_id,
                    kind="questions",
                    hero_name=hero_name,
                )
            logger.info("=== ROUND 1 DONE — ждём ответы клиента на доп. вопросы ===")
            return 0

        # Round 2+: собираем книгу
        if not _run_build_all(workspace, project_id, round_number):
            return 1
        _publish_book_only(workspace, project_id)
        # Email клиенту: книга готова
        latest_book = db.get_latest_project_book(project_id)
        _notify_owner(
            project_id,
            kind="book",
            hero_name=hero_name,
            book_version=latest_book["version"] if latest_book else None,
        )
        logger.info("=== ROUND %s DONE ===", round_number)
        return 0
    except Exception as e:
        logger.exception("FATAL during processing of project %s: %s", project_id, e)
        tb = traceback.format_exc()[-500:]
        # Если знаем какая стадия открыта — пометим failed
        try:
            stages = db.get_job_stages(project_id, round_number)
            for s in stages:
                if s["status"] == "running":
                    db.update_job_stage(
                        project_id, round_number, s["stage_key"], "failed",
                        error_message=str(e)[:300],
                    )
                    break
        except Exception:
            pass
        return 1
    finally:
        # Workspace оставляем для разбора при ошибке. Чистим только при успехе.
        # TODO: в проде — отдельная стадия очистки или TTL.
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", type=int, required=True)
    args = parser.parse_args()
    return process(args.project_id)


if __name__ == "__main__":
    sys.exit(main())
