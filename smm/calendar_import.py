# -*- coding: utf-8 -*-
"""
Массовый импорт записей контент-календаря (smm_content_calendar).

Поддерживает 3 формата (определяются автоматически):

1. PIPE (по умолчанию) — каждая строка:
   ``ДАТА | ПЛОЩАДКА | ТИП | РУБРИКА | НАЗВАНИЕ [| ДОП_ИНФО]``

   Пример:
   ``2026-05-29 | Дзен | статья | семейная память | Что проще вспомнить``

2. TSV — те же колонки через TAB. Первая строка-заголовок пропускается.
   Удобно копировать из Google Sheets / Excel.

3. JSON — массив объектов:
   ``[{"date": ..., "platform": ..., "material_type": ...,
       "rubric": ..., "title": ..., "extra_info": ...}, ...]``

Дедупликация: (platform_id, publish_date, lower(title)).
Дубли внутри одной загрузки и дубли с существующими записями — пропускаются.

Все обращения к БД вынесены в коллбэки — модуль тестируется без Postgres.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Optional


_SEP_RE = re.compile(r"\s*\|\s*")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ── Структуры данных ──────────────────────────────────────────────────────────


@dataclass
class ParsedItem:
    """Одна успешно распарсенная строка."""
    publish_date: date
    platform_name: str          # Имя площадки как введено
    material_type: str          # Тип материала (статья, пост…)
    rubric_name: str            # Имя рубрики как введено (может быть пустым)
    title: str                  # Название / тема
    extra_info: str = ""        # Доп. информация (необязательно)
    line_no: int = 0


@dataclass
class ImportRow:
    """Результат обработки одной строки."""
    line_no: int = 0
    status: str = ""            # created | duplicate | error
    message: str = ""
    item: Optional[ParsedItem] = None


@dataclass
class ImportReport:
    rows: list[ImportRow] = field(default_factory=list)

    @property
    def created(self) -> int:
        return sum(1 for r in self.rows if r.status == "created")

    @property
    def duplicates(self) -> int:
        return sum(1 for r in self.rows if r.status == "duplicate")

    @property
    def errors(self) -> int:
        return sum(1 for r in self.rows if r.status == "error")

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "duplicates": self.duplicates,
            "errors": self.errors,
            "rows": [
                {
                    "line_no": r.line_no,
                    "status": r.status,
                    "message": r.message,
                    "title": r.item.title if r.item else "",
                }
                for r in self.rows
            ],
        }


# ── Парсинг ───────────────────────────────────────────────────────────────────


def _parse_date(s: str) -> Optional[date]:
    s = s.strip()
    if _ISO_DATE_RE.match(s):
        return datetime.strptime(s, "%Y-%m-%d").date()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _parse_pipe_line(line: str, line_no: int) -> ImportRow:
    parts = _SEP_RE.split(line.strip())
    if len(parts) < 5:
        return ImportRow(
            line_no=line_no,
            status="error",
            message=f"Недостаточно полей (нужно 5, получено {len(parts)}): {line[:80]}",
        )
    publish_date = _parse_date(parts[0])
    if not publish_date:
        return ImportRow(
            line_no=line_no,
            status="error",
            message=f"Не удалось распознать дату: {parts[0]!r}",
        )
    platform_name = parts[1].strip()
    material_type = parts[2].strip()
    rubric_name   = parts[3].strip()
    title         = parts[4].strip()
    extra_info    = parts[5].strip() if len(parts) > 5 else ""

    if not platform_name:
        return ImportRow(line_no=line_no, status="error", message="Площадка не указана")
    if not title:
        return ImportRow(line_no=line_no, status="error", message="Название не указано")

    return ImportRow(
        line_no=line_no,
        status="",
        item=ParsedItem(
            publish_date=publish_date,
            platform_name=platform_name,
            material_type=material_type,
            rubric_name=rubric_name,
            title=title,
            extra_info=extra_info,
            line_no=line_no,
        ),
    )


def _parse_tsv_line(cells: list[str], line_no: int) -> ImportRow:
    """Разбор строки TSV — те же колонки что и в PIPE."""
    return _parse_pipe_line(" | ".join(cells), line_no)


def _parse_json(text: str) -> list[ImportRow]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [ImportRow(line_no=0, status="error", message=f"Ошибка JSON: {exc}")]

    if not isinstance(data, list):
        return [ImportRow(line_no=0, status="error", message="JSON должен быть массивом объектов")]

    rows: list[ImportRow] = []
    for i, obj in enumerate(data, start=1):
        if not isinstance(obj, dict):
            rows.append(ImportRow(line_no=i, status="error", message="Элемент не является объектом"))
            continue

        date_raw = (obj.get("date") or obj.get("publish_date") or "").strip()
        publish_date = _parse_date(date_raw)
        if not publish_date:
            rows.append(ImportRow(line_no=i, status="error", message=f"Не удалось распознать дату: {date_raw!r}"))
            continue

        platform_name = (obj.get("platform") or obj.get("platform_name") or "").strip()
        material_type = (obj.get("material_type") or obj.get("type") or "").strip()
        rubric_name   = (obj.get("rubric") or obj.get("rubric_name") or "").strip()
        title         = (obj.get("title") or obj.get("topic") or "").strip()
        extra_info    = (obj.get("extra_info") or obj.get("description") or "").strip()

        if not platform_name:
            rows.append(ImportRow(line_no=i, status="error", message="Поле platform не указано"))
            continue
        if not title:
            rows.append(ImportRow(line_no=i, status="error", message="Поле title не указано"))
            continue

        rows.append(ImportRow(
            line_no=i,
            status="",
            item=ParsedItem(
                publish_date=publish_date,
                platform_name=platform_name,
                material_type=material_type,
                rubric_name=rubric_name,
                title=title,
                extra_info=extra_info,
                line_no=i,
            ),
        ))
    return rows


def parse_text(text: str) -> list[ImportRow]:
    """
    Определяет формат (JSON / TSV / PIPE) и парсит текст в список ImportRow.
    Строки с ошибками получают status='error', успешные — status=''.
    """
    text = text.strip()
    if not text:
        return []

    # JSON
    if text.startswith("["):
        return _parse_json(text)

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []

    # TSV: первая строка содержит TAB и не начинается с цифры/даты
    first = lines[0]
    if "\t" in first and not _parse_date(first.split("\t")[0]):
        # Первая строка — заголовок
        data_lines = lines[1:]
    elif "\t" in first:
        data_lines = lines
    else:
        data_lines = None

    if data_lines is not None:
        rows: list[ImportRow] = []
        for i, ln in enumerate(data_lines, start=2):
            cells = [c.strip() for c in ln.split("\t")]
            rows.append(_parse_tsv_line(cells, i))
        return rows

    # PIPE
    rows = []
    for i, ln in enumerate(lines, start=1):
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        rows.append(_parse_pipe_line(ln, i))
    return rows


# ── Импорт в БД ───────────────────────────────────────────────────────────────


def run_import(
    text: str,
    *,
    get_platform_by_name: Callable[[str], Optional[dict]],
    get_rubric_by_name: Callable[[str], Optional[dict]],
    get_existing_signatures: Callable[[], set],
    add_entry: Callable[..., int],
) -> ImportReport:
    """
    Полный цикл импорта: парсинг → разрешение площадки/рубрики → дедупликация → сохранение.

    Все операции с БД передаются через коллбэки для тестируемости.
    """
    report = ImportReport()
    parsed_rows = parse_text(text)

    # Строки с ошибками парсинга
    error_rows = [r for r in parsed_rows if r.status == "error"]
    report.rows.extend(error_rows)

    good_rows = [r for r in parsed_rows if r.status == "" and r.item is not None]
    if not good_rows:
        return report

    # Загружаем существующие сигнатуры для дедупликации
    existing_sigs: set = get_existing_signatures()
    # Сигнатуры внутри текущей загрузки
    batch_sigs: set = set()

    # Кэш площадок и рубрик
    platform_cache: dict[str, Optional[dict]] = {}
    rubric_cache: dict[str, Optional[dict]] = {}

    for row in good_rows:
        item = row.item

        # Разрешаем площадку
        pname_key = item.platform_name.lower()
        if pname_key not in platform_cache:
            platform_cache[pname_key] = get_platform_by_name(item.platform_name)
        platform = platform_cache[pname_key]

        if platform is None:
            report.rows.append(ImportRow(
                line_no=item.line_no,
                status="error",
                message=f"Площадка не найдена: {item.platform_name!r}",
                item=item,
            ))
            continue

        platform_id = platform["id"]

        # Разрешаем рубрику (необязательно)
        rubric_id: Optional[int] = None
        if item.rubric_name:
            rname_key = item.rubric_name.lower()
            if rname_key not in rubric_cache:
                rubric_cache[rname_key] = get_rubric_by_name(item.rubric_name)
            rubric = rubric_cache[rname_key]
            if rubric is None:
                report.rows.append(ImportRow(
                    line_no=item.line_no,
                    status="error",
                    message=f"Рубрика не найдена: {item.rubric_name!r}",
                    item=item,
                ))
                continue
            rubric_id = rubric["id"]

        # Дедупликация
        sig = (platform_id, item.publish_date.isoformat(), item.title.lower())
        if sig in existing_sigs or sig in batch_sigs:
            report.rows.append(ImportRow(
                line_no=item.line_no,
                status="duplicate",
                message="Дубликат — пропущено",
                item=item,
            ))
            continue

        # Сохранение
        add_entry(
            platform_id=platform_id,
            publish_date=item.publish_date.isoformat(),
            title=item.title,
            material_type=item.material_type,
            rubric_id=rubric_id,
            extra_info=item.extra_info,
            content_ready=False,
        )
        batch_sigs.add(sig)
        report.rows.append(ImportRow(
            line_no=item.line_no,
            status="created",
            message=f"Добавлено: {item.title[:60]}",
            item=item,
        ))

    return report
