# -*- coding: utf-8 -*-
"""
Массовый импорт контент-календаря.

Поддерживает 3 формата (определяются автоматически):

1. PIPE (по умолчанию) — каждая строка как:
   ``ГГГГ-ММ-ДД | площадка/формат | рубрика | тема [| заголовок | промпт_картинки | диалог]``

2. TSV — те же колонки через TAB. Первая строка-заголовок (без даты в первой ячейке)
   автоматически пропускается. Удобно копировать из Excel/Google Sheets.

3. JSON — массив объектов ``[{"date": ..., "platform_format": ..., "rubric": ..., "topic": ...}, ...]``.
   Принимаются также ключи ``publish_date``, ``platform``, ``pf``, ``title``,
   ``article_title``, ``image_prompt``, ``initiate_dialog``.

Дедупликация: совпадение по полному набору ``(publish_date, platform_format_id,
rubric_id, lower(topic))``. Дубль внутри текущей загрузки И дубль уже существующего
поста в БД — оба пропускаются с маркером ``duplicate``.

Все обращения к БД вынесены в коллбэки — модуль чистый и тестируемый без коннекта
к Postgres.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Optional


_SEP_RE = re.compile(r"\s*\|\s*")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ── Структуры данных ─────────────────────────────────────────────────────────


@dataclass
class ParsedItem:
    """Одна успешно распарсенная запись из массива."""
    publish_date: date
    pf_ref: str           # Слаг или "platform/format" или имя площадки
    rubric_ref: str       # Слаг или имя рубрики
    topic: str
    article_title: str = ""
    image_prompt: str = ""
    initiate_dialog: bool = False
    line_no: int = 0      # 1-based — для сообщений


@dataclass
class ImportRow:
    """Результат обработки одной строки/элемента."""
    line_no: int = 0
    status: str = ""      # created | duplicate | error
    message: str = ""
    item: Optional[ParsedItem] = None


@dataclass
class ImportReport:
    created: int = 0
    duplicate: int = 0
    error: int = 0
    rows: list[ImportRow] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.duplicate + self.error

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "duplicate": self.duplicate,
            "error": self.error,
            "total": self.total,
            "rows": [
                {
                    "line_no": r.line_no,
                    "status": r.status,
                    "message": r.message,
                }
                for r in self.rows
            ],
        }


# ── Парсинг ──────────────────────────────────────────────────────────────────


def parse_text(text: str) -> tuple[list[ParsedItem], list[ImportRow]]:
    """Парсит произвольный текст, автоопределяя формат.

    Возвращает (items, parse_errors).
    Если text пустой/whitespace — оба списка пустые.
    """
    text = (text or "").strip()
    if not text:
        return [], []

    if text.startswith("[") or text.startswith("{"):
        return _parse_json(text)
    if "\t" in text:
        return _parse_tsv(text)
    return _parse_pipe(text)


def _parse_pipe(text: str) -> tuple[list[ParsedItem], list[ImportRow]]:
    items: list[ParsedItem] = []
    errors: list[ImportRow] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in _SEP_RE.split(line)]
        if len(parts) < 4:
            errors.append(ImportRow(
                line_no=line_no, status="error",
                message=f"строка {line_no}: ожидалось 4+ поля через '|', получено {len(parts)}",
            ))
            continue
        item, err = _build_item_from_parts(parts, line_no)
        if err is not None:
            errors.append(err)
        elif item is not None:
            items.append(item)
    return items, errors


def _parse_tsv(text: str) -> tuple[list[ParsedItem], list[ImportRow]]:
    items: list[ParsedItem] = []
    errors: list[ImportRow] = []
    lines = text.splitlines()
    if not lines:
        return items, errors
    start = 0
    first_cols = lines[0].split("\t")
    first_first = (first_cols[0] if first_cols else "").strip()
    if first_first and not _ISO_DATE_RE.match(first_first) and not _looks_like_date(first_first):
        start = 1
    for idx, raw in enumerate(lines[start:], start=start + 1):
        if not raw.strip():
            continue
        parts = [p.strip() for p in raw.split("\t")]
        if len(parts) < 4:
            errors.append(ImportRow(
                line_no=idx, status="error",
                message=f"строка {idx}: ожидалось 4+ колонки через TAB, получено {len(parts)}",
            ))
            continue
        item, err = _build_item_from_parts(parts, idx)
        if err is not None:
            errors.append(err)
        elif item is not None:
            items.append(item)
    return items, errors


def _parse_json(text: str) -> tuple[list[ParsedItem], list[ImportRow]]:
    items: list[ParsedItem] = []
    errors: list[ImportRow] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [], [ImportRow(line_no=e.lineno, status="error", message=f"JSON: {e.msg}")]
    if not isinstance(data, list):
        return [], [ImportRow(line_no=0, status="error", message="ожидался JSON-массив объектов")]
    for idx, raw in enumerate(data, start=1):
        if not isinstance(raw, dict):
            errors.append(ImportRow(line_no=idx, status="error", message=f"элемент {idx}: не объект"))
            continue
        try:
            d = _parse_date(str(raw.get("date") or raw.get("publish_date") or ""))
            pf = str(raw.get("platform_format") or raw.get("pf") or raw.get("platform") or "").strip()
            rubric = str(raw.get("rubric") or "").strip()
            topic = str(raw.get("topic") or "").strip()
            if d is None or not pf or not rubric or not topic:
                missing = [k for k, v in (
                    ("date", d), ("platform_format", pf), ("rubric", rubric), ("topic", topic)
                ) if not v]
                raise ValueError(f"не заданы поля: {', '.join(missing)}")
            items.append(ParsedItem(
                publish_date=d, pf_ref=pf, rubric_ref=rubric, topic=topic,
                article_title=str(raw.get("title") or raw.get("article_title") or "").strip(),
                image_prompt=str(raw.get("image_prompt") or "").strip(),
                initiate_dialog=_parse_bool(raw.get("initiate_dialog")),
                line_no=idx,
            ))
        except Exception as e:
            errors.append(ImportRow(line_no=idx, status="error", message=f"элемент {idx}: {e}"))
    return items, errors


def _build_item_from_parts(parts: list[str], line_no: int) -> tuple[Optional[ParsedItem], Optional[ImportRow]]:
    try:
        d = _parse_date(parts[0])
        if d is None:
            raise ValueError(f"некорректная дата '{parts[0]}' (нужен формат ГГГГ-ММ-ДД или ДД.ММ.ГГГГ)")
        pf = parts[1].strip()
        rubric = parts[2].strip()
        topic = parts[3].strip()
        if not pf or not rubric or not topic:
            raise ValueError("пустое обязательное поле (площадка/рубрика/тема)")
        title = parts[4].strip() if len(parts) > 4 else ""
        image_prompt = parts[5].strip() if len(parts) > 5 else ""
        dialog = _parse_bool(parts[6]) if len(parts) > 6 else False
        return ParsedItem(
            publish_date=d, pf_ref=pf, rubric_ref=rubric, topic=topic,
            article_title=title, image_prompt=image_prompt, initiate_dialog=dialog,
            line_no=line_no,
        ), None
    except Exception as e:
        return None, ImportRow(line_no=line_no, status="error", message=f"строка {line_no}: {e}")


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _looks_like_date(value: str) -> bool:
    return _parse_date(value) is not None


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "да", "y", "✓", "+")


# ── Резолв ссылок rubric / pformat ───────────────────────────────────────────


def resolve_rubric_id(ref: str, rubrics: list[dict]) -> Optional[int]:
    """Ищет рубрику по slug, затем по name (case-insensitive)."""
    if not ref:
        return None
    needle = ref.strip().lower()
    for r in rubrics:
        if (r.get("slug") or "").lower() == needle:
            return r.get("id")
    for r in rubrics:
        if (r.get("name") or "").lower() == needle:
            return r.get("id")
    return None


def resolve_pformat_id(ref: str, pformats: list[dict]) -> Optional[int]:
    """Резолвит площадку/формат: по slug, по "platform/format", либо по имени площадки."""
    if not ref:
        return None
    needle = ref.strip().lower()
    for pf in pformats:
        if (pf.get("slug") or "").lower() == needle:
            return pf.get("id")
    if "/" in needle:
        plat, _, fmt = needle.partition("/")
        plat, fmt = plat.strip(), fmt.strip()
        for pf in pformats:
            if (pf.get("platform_name") or "").lower() == plat \
                    and (pf.get("format_name") or "").lower() == fmt:
                return pf.get("id")
    for pf in pformats:
        if (pf.get("platform_name") or "").lower() == needle:
            return pf.get("id")
    return None


# ── Импорт ───────────────────────────────────────────────────────────────────


def import_items(
    items: list[ParsedItem],
    parse_errors: list[ImportRow],
    *,
    rubrics: list[dict],
    pformats: list[dict],
    existing_posts: list[dict],
    create_plan_fn: Callable[[], int],
    create_post_fn: Callable[[int, ParsedItem, int, int], int],
    apply_extras_fn: Callable[[int, ParsedItem], None],
) -> ImportReport:
    """Чистая функция импорта.

    Аргументы-коллбэки:
      * ``create_plan_fn()`` — вызывается **один раз** при первой реальной вставке,
        возвращает ``plan_id`` для всей пачки.
      * ``create_post_fn(plan_id, item, rubric_id, pf_id)`` — создаёт пост и
        возвращает его ``id``. Должна сразу проставить ``rubric_id``, ``platform_format_id``.
      * ``apply_extras_fn(post_id, item)`` — проставляет ``publish_date``, опциональные
        ``article_title``/``image_prompt``/``initiate_dialog``. Разделено с
        ``create_post_fn``, чтобы тесты могли проверять оба шага независимо.

    Параметр ``existing_posts`` — список dict с ключами
    ``publish_date``, ``platform_format_id``, ``rubric_id``, ``topic`` (для дедупа).
    """
    report = ImportReport()

    for err in parse_errors:
        report.error += 1
        report.rows.append(err)

    if not items:
        return report

    existing_sigs = {
        _signature(
            p.get("publish_date"),
            p.get("platform_format_id"),
            p.get("rubric_id"),
            p.get("topic"),
        )
        for p in existing_posts
    }

    seen_in_batch: set[tuple] = set()
    plan_id: Optional[int] = None

    for item in items:
        rid = resolve_rubric_id(item.rubric_ref, rubrics)
        pf_id = resolve_pformat_id(item.pf_ref, pformats)
        if rid is None:
            report.error += 1
            report.rows.append(ImportRow(
                line_no=item.line_no, status="error",
                message=f"строка {item.line_no}: не найдена рубрика '{item.rubric_ref}'",
                item=item,
            ))
            continue
        if pf_id is None:
            report.error += 1
            report.rows.append(ImportRow(
                line_no=item.line_no, status="error",
                message=f"строка {item.line_no}: не найден формат площадки '{item.pf_ref}'",
                item=item,
            ))
            continue
        sig = _signature(item.publish_date, pf_id, rid, item.topic)
        if sig in seen_in_batch or sig in existing_sigs:
            report.duplicate += 1
            report.rows.append(ImportRow(
                line_no=item.line_no, status="duplicate",
                message=(
                    f"строка {item.line_no}: дубль "
                    f"({item.publish_date} · {item.pf_ref} · {item.rubric_ref} · {item.topic[:40]})"
                ),
                item=item,
            ))
            continue
        seen_in_batch.add(sig)

        if plan_id is None:
            plan_id = create_plan_fn()

        try:
            post_id = create_post_fn(plan_id, item, rid, pf_id)
            apply_extras_fn(post_id, item)
        except Exception as e:
            report.error += 1
            report.rows.append(ImportRow(
                line_no=item.line_no, status="error",
                message=f"строка {item.line_no}: ошибка при создании поста: {e}",
                item=item,
            ))
            continue

        report.created += 1
        report.rows.append(ImportRow(
            line_no=item.line_no, status="created",
            message=f"строка {item.line_no}: создан пост #{post_id} ({item.topic[:40]})",
            item=item,
        ))

    return report


def _signature(publish_date, pf_id, rubric_id, topic) -> tuple:
    if hasattr(publish_date, "isoformat"):
        d = publish_date.isoformat()
    elif publish_date:
        d = str(publish_date)
    else:
        d = ""
    return (d, pf_id, rubric_id, (topic or "").strip().lower())
