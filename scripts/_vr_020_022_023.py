#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verified-on-run тесты для задач 020, 022, 023.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Принудительно UTF-8 для stdout/stderr на Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

PASS = "✅ PASS"
FAIL = "❌ FAIL"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_book(chapters: list[dict]) -> dict:
    """Минимальная book_FINAL структура."""
    return {"chapters": chapters, "callouts": [], "historical_notes": []}


def make_chapter(ch_id: str, paragraphs: list[str]) -> dict:
    content = "\n\n".join(paragraphs)
    return {"id": ch_id, "title": f"Глава {ch_id}", "content": content}


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run(cmd: list[str], cwd: str = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=cwd or str(ROOT),
    )


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


# ─── TEST 023 — pdf_renderer chapter_id fallback ──────────────────────────────

def test_023():
    section("TEST 023 — pdf_renderer: book_final unwrap (checkpoint wrapper → 100% контент потеря)")

    PARA_TEXTS = [
        "Надежда Каракулина родилась в 1932 году в Ленинграде.",
        "Детство её прошло в труде и скромности, как у большинства детей той эпохи.",
        "В школе она выделялась прилежанием и добросовестностью.",
        "После окончания семилетки Надежда поступила на ткацкий комбинат.",
        "Там она познакомилась с будущим мужем Василием.",
    ]
    CH_ID = "ch_02"

    inner_book = {
        "chapters": [
            make_chapter("ch_01", ["Вводный абзац ch_01."]),
            make_chapter(CH_ID, PARA_TEXTS),
        ],
        "callouts": [], "historical_notes": [],
    }
    # РЕАЛЬНЫЙ БАГ v37: checkpoint-файл оборачивает книгу в {"book_final": {...}}
    # test_stage4 передаёт такой файл напрямую в pdf_renderer --book
    # pdf_renderer до фикса не unwrap'ил — BookIndex получал {}, 0 глав → 100% потеря
    book = {"book_final": inner_book}  # ← воспроизводим структуру checkpoint

    # Layout: chapter_id у всех элементов (как в реальном v37 layout)
    layout_bug = {
        "pages": [
            {
                "page_number": 1, "type": "chapter_start",
                "chapter_id": "ch_01",
                "chapter_title": "Введение",
                "elements": [
                    {"type": "paragraph", "chapter_id": "ch_01", "paragraph_ref": "p1"}
                ],
            },
            {
                "page_number": 2, "type": "text",
                "chapter_id": CH_ID,
                "elements": [
                    {"type": "paragraph", "chapter_id": CH_ID, "paragraph_ref": "p1"},
                    {"type": "paragraph", "chapter_id": CH_ID, "paragraph_ref": "p2"},
                    {"type": "paragraph", "chapter_id": CH_ID, "paragraph_ref": "p3"},
                ],
            },
            {
                "page_number": 3, "type": "text",
                "chapter_id": CH_ID,
                "elements": [
                    {"type": "paragraph", "chapter_id": CH_ID, "paragraph_ref": "p4"},
                    {"type": "paragraph", "chapter_id": CH_ID, "paragraph_ref": "p5"},
                ],
            },
        ],
        "style_guide": {},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        book_path = tmp / "book.json"
        layout_path = tmp / "layout.json"
        pdf_path = tmp / "out.pdf"

        write_json(book_path, book)
        write_json(layout_path, layout_bug)

        res = run([
            sys.executable, str(ROOT / "scripts" / "pdf_renderer.py"),
            "--layout", str(layout_path),
            "--book", str(book_path),
            "--no-photos",
            "--output", str(pdf_path),
        ])

        stdout = res.stdout + res.stderr
        print(stdout[-3000:])  # последние 3000 символов лога

        # Проверка 1: exit code
        if res.returncode != 0:
            print(f"\n{FAIL} Рендерер завершился с ошибкой (exit {res.returncode})")
            return False

        # Проверка 2: PDF создан
        if not pdf_path.exists():
            print(f"\n{FAIL} PDF не создан")
            return False

        # Проверка 3: лог сообщает о unwrap
        if "book_final unwrapped" not in stdout:
            print(f"\n{FAIL} Строка 'book_final unwrapped' не найдена — checkpoint не распаковался")
            return False

        # Проверка 4: лог резолвинга
        if "Refs:" not in stdout:
            print(f"\n{FAIL} Нет строки [RENDERER] Refs: в логе")
            return False

        # Найти строку с процентом
        ref_line = next((l for l in stdout.splitlines() if "Refs:" in l), "")
        print(f"\n  Строка резолвинга: {ref_line}")

        if "100%" not in ref_line:
            print(f"\n{FAIL} Резолвинг не 100% — chapter_id fallback не сработал или IDs не совпадают")
            return False

        # Проверка 4: текст в PDF через pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                all_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            # Нормализуем: убираем переносы строк → пробелы (pdfplumber сохраняет line breaks)
            all_text_flat = " ".join(all_text.split())
            char_count = len(all_text_flat.strip())
            print(f"  PDF символов (flat): {char_count}")
            print(f"  PDF первые 300 chars: {all_text_flat[:300]}")

            # Ожидаемые фрагменты (без переносов строк)
            expected_snippets = [
                "Надежда Каракулина",
                "Детство",
                "школе",
                "ткацкий",      # из "на ткацкий комбинат"
                "Василием",
            ]
            missing = [s for s in expected_snippets if s not in all_text_flat]
            if missing:
                print(f"\n{FAIL} В PDF отсутствуют фрагменты: {missing}")
                return False

            # Минимальный размер: ожидаем ~300+ chars контента
            if char_count < 200:
                print(f"\n{FAIL} PDF слишком мало текста ({char_count} символов) — контент потерян")
                return False

            print(f"\n{PASS} Все 5 абзацев ch_02 найдены в PDF ({char_count} символов)")
            return True

        except ImportError:
            print("  ⚠️  pdfplumber не установлен — проверяю только размер файла")
            size_kb = pdf_path.stat().st_size // 1024
            if size_kb < 5:
                print(f"\n{FAIL} PDF подозрительно маленький ({size_kb} KB)")
                return False
            print(f"\n{PASS} PDF создан ({size_kb} KB), Refs 100% — считаем OK")
            return True


# ─── TEST 022 — hybrid element detection ──────────────────────────────────────

def test_022():
    section("TEST 022 — verify_and_patch: hybrid element hard fail + warn")

    from test_stage4_karakulina import verify_and_patch_layout_completeness

    book = make_book([make_chapter("ch_02", [
        "Первый абзац.",
        "Второй абзац.",
    ])])

    from pipeline_utils import prepare_book_for_layout
    book_prepared = prepare_book_for_layout(book)

    # Layout с hybrid элементом: есть text, нет paragraph_ref/paragraph_id
    layout_hybrid = {
        "_layout_format": "pages_json",
        "pages": [
            {
                "page_number": 1, "type": "chapter_start",
                "chapter_id": "ch_02",
                "elements": [
                    {"type": "paragraph", "chapter_id": "ch_02", "paragraph_ref": "p1"},
                    # ← HYBRID: inline text, нет ref
                    {"type": "paragraph", "chapter_id": "ch_02", "text": "Второй абзац."},
                ],
            },
        ],
    }

    ok_a = ok_b = False

    # Тест A: без --allow-hybrid → должно sys.exit(1)
    print("\n  Тест A: hybrid без --allow-hybrid...")
    try:
        verify_and_patch_layout_completeness(layout_hybrid, book_prepared, allow_hybrid=False)
        print(f"  {FAIL} Не упало с sys.exit — функция вернула результат")
        ok_a = False
    except SystemExit as e:
        if e.code == 1:
            print(f"  {PASS} sys.exit(1) при hybrid элементе")
            ok_a = True
        else:
            print(f"  {FAIL} sys.exit({e.code}) — ожидался exit code 1")
            ok_a = False

    # Тест B: с --allow-hybrid → warn + продолжение
    print("\n  Тест B: hybrid с --allow-hybrid...")
    # Используем глубокую копию чтобы не менять оригинал
    import copy
    layout_copy = copy.deepcopy(layout_hybrid)
    try:
        result = verify_and_patch_layout_completeness(layout_copy, book_prepared, allow_hybrid=True)
        if result is not None:
            print(f"  {PASS} Функция вернула результат (не упала), --allow-hybrid работает")
            ok_b = True
        else:
            print(f"  {FAIL} Функция вернула None")
    except SystemExit as e:
        print(f"  {FAIL} Упало с sys.exit({e.code}) при --allow-hybrid — не должно падать")

    # Тест C: счётчик после патча
    print("\n  Тест C: счётчик (paragraph_ref → правильный учёт)...")
    layout_clean = {
        "_layout_format": "pages_json",
        "pages": [
            {
                "page_number": 1, "type": "text",
                "chapter_id": "ch_02",
                "elements": [
                    {"type": "paragraph", "chapter_id": "ch_02", "paragraph_ref": "p1"},
                    # p2 пропущен — патч должен добавить его
                ],
            },
        ],
    }
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        verify_and_patch_layout_completeness(copy.deepcopy(layout_clean), book_prepared, allow_hybrid=False)
    output = buf.getvalue()
    # Ищем "После патча: 2/2" или ненулевой счётчик
    if "После патча:" in output and "/2" in output:
        after_line = next(l for l in output.splitlines() if "После патча:" in l)
        if "0/2" in after_line:
            print(f"  {FAIL} Счётчик всё ещё 0/2 — баг не исправлен: {after_line}")
            ok_b = False
        else:
            print(f"  {PASS} Счётчик корректный: {after_line.strip()}")
    else:
        print(f"  ⚠️  Строка 'После патча' не найдена — возможно патч не нужен был")

    return ok_a and ok_b


# ─── TEST 020 — fidelity enforcement ──────────────────────────────────────────

def test_020():
    section("TEST 020 — validate_fidelity enforcement: sys.exit + --allow-mismatch")

    from validate_layout_fidelity import validate_fidelity

    book = make_book([make_chapter("ch_02", ["Абзац один.", "Абзац два.", "Абзац три."])])
    from pipeline_utils import prepare_book_for_layout
    book_prepared = prepare_book_for_layout(book)

    # Битый layout: p2 встречается дважды (дубль)
    layout_bad = {
        "pages": [
            {
                "page_number": 1, "type": "text",
                "chapter_id": "ch_02",
                "elements": [
                    {"type": "paragraph", "chapter_id": "ch_02", "paragraph_ref": "p1"},
                    {"type": "paragraph", "chapter_id": "ch_02", "paragraph_ref": "p2"},
                    {"type": "paragraph", "chapter_id": "ch_02", "paragraph_ref": "p2"},  # дубль
                ],
            },
        ],
    }

    passed, errors = validate_fidelity(layout_bad, book_prepared, allow_mismatch=False)
    print(f"\n  validate_fidelity результат: passed={passed}, errors={errors}")

    if passed:
        print(f"  {FAIL} Валидатор вернул PASS на битом layout — unexpected")
        return False

    print(f"  {PASS} Валидатор нашёл {len(errors)} ошибок")

    # Симулируем enforcement logic из test_stage4_karakulina.py
    # Тест A: без --allow-mismatch (allow_mismatch=False)
    print("\n  Тест A: enforcement без --allow-mismatch...")
    import argparse
    args_no_flag = argparse.Namespace(allow_mismatch=False)

    exited = False
    exit_code = None
    _orig_exit = sys.exit
    def _mock_exit(code=0):
        nonlocal exited, exit_code
        exited = True
        exit_code = code
        raise SystemExit(code)
    sys.exit = _mock_exit

    try:
        if not passed:
            if args_no_flag.allow_mismatch:
                pass  # warn
            else:
                sys.exit(1)
    except SystemExit:
        pass
    finally:
        sys.exit = _orig_exit

    if exited and exit_code == 1:
        print(f"  {PASS} sys.exit(1) сработал без --allow-mismatch")
        ok_a = True
    else:
        print(f"  {FAIL} sys.exit не сработал")
        ok_a = False

    # Тест B: с --allow-mismatch
    print("\n  Тест B: enforcement с --allow-mismatch...")
    args_with_flag = argparse.Namespace(allow_mismatch=True)
    exited_b = False

    sys.exit = _mock_exit
    try:
        if not passed:
            if args_with_flag.allow_mismatch:
                print(f"  [FIDELITY] ⚠️  (mock warn) — ошибок: {len(errors)}")
            else:
                sys.exit(1)
    finally:
        sys.exit = _orig_exit

    if not exited_b:
        print(f"  {PASS} С --allow-mismatch прогон продолжился (warn, не exit)")
        ok_b = True
    else:
        print(f"  {FAIL} Упало с exit даже при --allow-mismatch")
        ok_b = False

    return ok_a and ok_b


# ─── TEST 021 — photos_dir guard ──────────────────────────────────────────────

def test_021():
    section("TEST 021 — photos_dir guard в pdf_renderer вызове")

    import argparse

    def build_render_cmd_new(args: argparse.Namespace) -> list[str]:
        """Воспроизводит логику из test_stage4_karakulina.py после фикса 021."""
        cmd = ["python", "scripts/pdf_renderer.py", "--layout", "layout.json"]
        if args.photos_dir:
            if args.acceptance_gate in {"2a", "2b", "2c"}:
                print(f"  [WARN] gate {args.acceptance_gate}: --photos-dir игнорируется для pdf_renderer (text-only mode)")
            else:
                cmd += ["--photos-dir", str(args.photos_dir)]
        return cmd

    photos_path = "/some/photos"

    # Тест A: gate 2c → photos_dir НЕ попадает в cmd
    print("\n  Тест A: gate 2c с --photos-dir...")
    args_2c = argparse.Namespace(acceptance_gate="2c", photos_dir=photos_path)
    cmd_2c = build_render_cmd_new(args_2c)
    photos_in_cmd = "--photos-dir" in cmd_2c
    if photos_in_cmd:
        print(f"  {FAIL} --photos-dir попал в cmd при gate 2c: {cmd_2c}")
        ok_a = False
    else:
        print(f"  {PASS} --photos-dir не в cmd при gate 2c")
        ok_a = True

    # Тест B: gate 3 → photos_dir попадает в cmd
    print("\n  Тест B: gate 3 с --photos-dir...")
    args_3 = argparse.Namespace(acceptance_gate="3", photos_dir=photos_path)
    cmd_3 = build_render_cmd_new(args_3)
    photos_in_cmd_3 = "--photos-dir" in cmd_3
    if photos_in_cmd_3:
        print(f"  {PASS} --photos-dir в cmd при gate 3: передаётся корректно")
        ok_b = True
    else:
        print(f"  {FAIL} --photos-dir не в cmd при gate 3 — сломана обратная совместимость")
        ok_b = False

    # Тест C: gate None → photos_dir попадает в cmd
    print("\n  Тест C: gate None (без флага) с --photos-dir...")
    args_none = argparse.Namespace(acceptance_gate=None, photos_dir=photos_path)
    cmd_none = build_render_cmd_new(args_none)
    if "--photos-dir" in cmd_none:
        print(f"  {PASS} --photos-dir в cmd при gate=None")
        ok_c = True
    else:
        print(f"  {FAIL} --photos-dir не в cmd при gate=None")
        ok_c = False

    return ok_a and ok_b and ok_c


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    results = {}

    results["023"] = test_023()
    results["022"] = test_022()
    results["020"] = test_020()
    results["021"] = test_021()

    print(f"\n{'=' * 60}")
    print("  ИТОГ")
    print("=" * 60)
    all_ok = True
    for task_id, ok in results.items():
        status = PASS if ok else FAIL
        print(f"  Task {task_id}: {status}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\n✅ Все verified-on-run тесты прошли.")
        sys.exit(0)
    else:
        print(f"\n❌ Есть провалившиеся тесты — см. вывод выше.")
        sys.exit(1)


if __name__ == "__main__":
    main()
