#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patches test_stage4_karakulina.py:
  1. validate_layout_output — support layout_instructions.pages[]
  2. PDF build — use glava.pdf_builder.build_pdf instead of old subprocess
  3. run_layout_qa — pass pdf_file path; use pdf2image for vision preview
  4. QA user_message — include PDF previews
"""
import pathlib, re, sys

TARGET = pathlib.Path("/opt/glava/scripts/test_stage4_karakulina.py")
src = TARGET.read_text(encoding="utf-8")
orig = src

# ──────────────────────────────────────────────────────────────────
# 1. validate_layout_output — add layout_instructions.pages[] support
# ──────────────────────────────────────────────────────────────────
OLD_VALIDATE = '''def validate_layout_output(response: dict) -> dict | None:
    """Проверяет структуру Layout Designer. Поддерживает оба формата:
       новый (pages[]) и старый (layout_code.code).
    """
    if not isinstance(response, dict):
        return None
    # Новый формат v2: pages[] + style_guide
    pages = response.get("pages", [])
    if pages:
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", 0)
        print(f"[VALIDATE-LAYOUT] ✅ pages: {len(pages)} | page_map: {len(page_map)} | total_pages: {total_pages}")
        return response
    # Старый формат: layout_code.code (fallback)
    layout_code = response.get("layout_code", {})
    if layout_code.get("code"):
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", 0)
        print(f"[VALIDATE-LAYOUT] ✅ layout_code (old fmt): {len(layout_code.get('code',''))} симв. | "
              f"page_map: {len(page_map)} | total_pages: {total_pages}")
        return response
    print("[VALIDATE-LAYOUT] ❌ Нет ни pages[], ни layout_code.code")
    return None'''

NEW_VALIDATE = '''def validate_layout_output(response: dict) -> dict | None:
    """Проверяет структуру Layout Designer. Поддерживает три формата:
       v3: layout_instructions.pages[] (Dasha prompt v7)
       v2: pages[] + style_guide
       v1: layout_code.code (legacy)
    """
    if not isinstance(response, dict):
        return None
    # Format v3: layout_instructions.pages[] (new — Dasha v7)
    li = response.get("layout_instructions", {})
    if isinstance(li, dict):
        pages = li.get("pages", [])
        if pages:
            page_map = response.get("page_map", [])
            total = response.get("technical_notes", {}).get("total_pages", len(pages))
            print(f"[VALIDATE-LAYOUT] ✅ layout_instructions.pages: {len(pages)} | "
                  f"page_map: {len(page_map)} | total_pages: {total}")
            return response
    # Format v2: top-level pages[]
    pages = response.get("pages", [])
    if pages:
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", 0)
        print(f"[VALIDATE-LAYOUT] ✅ pages: {len(pages)} | page_map: {len(page_map)} | total_pages: {total_pages}")
        return response
    # Format v1: layout_code.code (legacy fallback)
    layout_code = response.get("layout_code", {})
    if layout_code.get("code"):
        page_map = response.get("page_map", [])
        total_pages = response.get("technical_notes", {}).get("total_pages", 0)
        print(f"[VALIDATE-LAYOUT] ✅ layout_code (legacy): {len(layout_code.get('code',''))} симв. | "
              f"page_map: {len(page_map)} | total_pages: {total_pages}")
        return response
    print("[VALIDATE-LAYOUT] ❌ Нет layout_instructions.pages[], pages[], ни layout_code.code")
    return None'''

if OLD_VALIDATE in src:
    src = src.replace(OLD_VALIDATE, NEW_VALIDATE, 1)
    print("[OK] validate_layout_output patched")
else:
    print("[WARN] validate_layout_output not found — skipping")


# ──────────────────────────────────────────────────────────────────
# 2. PDF build section — replace old subprocess with glava.pdf_builder
# ──────────────────────────────────────────────────────────────────
OLD_BUILD = '''        # Если Layout Designer вернул JSON (новый формат) — собираем PDF через build_karakulina_pdf.py
        if layout_result.get("pages"):
            import subprocess as _sp
            build_script = ROOT / "scripts" / "build_karakulina_pdf.py"
            if build_script.exists():
                print(f"\\n[BUILD_PDF] Запускаем {build_script.name} (Layout Designer → JSON → PDF)...")
                _result = _sp.run(
                    ["/opt/glava/venv/bin/python3", str(build_script)],
                    cwd=str(ROOT), capture_output=True, text=True, timeout=120,
                )
                if _result.returncode == 0:
                    print(f"[BUILD_PDF] ✅ PDF собран успешно")
                    for line in _result.stdout.strip().splitlines()[-5:]:
                        print(f"  {line}")
                else:
                    print(f"[BUILD_PDF] ⚠️  Ошибка сборки PDF (rc={_result.returncode})")
                    print(_result.stderr[-500:] if _result.stderr else "(нет stderr)")
            else:
                print(f"[BUILD_PDF] Скрипт не найден: {build_script}")'''

NEW_BUILD = '''        # Build PDF via deterministic glava.pdf_builder
        import logging as _logging
        _logging.getLogger("glava.pdf_builder").setLevel(_logging.INFO)
        from glava.pdf_builder import build_pdf as _build_pdf

        # Resolve layout_instructions (support v3 and v2 formats)
        _li = layout_result.get("layout_instructions") or layout_result

        # Latest proofreader report
        _book_candidates = sorted(ROOT.glob(f"exports/{args.prefix}_proofreader_report_*.json"))
        _book_path = str(_book_candidates[-1]) if _book_candidates else str(
            ROOT / "exports" / "karakulina_proofreader_report_20260329_065332.json")

        _photos_dir = str(ROOT / "exports" / "karakulina_photos")
        _pdf_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        _pdf_output = str(ROOT / "exports" / f"{args.prefix}_FINAL_{_pdf_ts}.pdf")

        print(f"\\n[BUILD_PDF] glava.pdf_builder → {pathlib.Path(_pdf_output).name}")
        pdf_path = _build_pdf(
            layout_instructions=_li,
            book_json_path=_book_path,
            photos_dir=_photos_dir,
            cover_portrait=cover_portrait if isinstance(cover_portrait, str) else None,
            cover_composition=cover_composition,
            output_path=_pdf_output,
        )
        if pdf_path:
            _sz = pathlib.Path(pdf_path).stat().st_size / 1024 / 1024
            print(f"[BUILD_PDF] PDF ready: {pathlib.Path(pdf_path).name} ({_sz:.1f} MB)")
        else:
            print("[BUILD_PDF] WARN: PDF build returned None — QA will run in JSON-only mode")
            pdf_path = None'''

if OLD_BUILD in src:
    src = src.replace(OLD_BUILD, NEW_BUILD, 1)
    print("[OK] PDF build section patched")
else:
    print("[WARN] PDF build section not found — skipping")


# ──────────────────────────────────────────────────────────────────
# 3. run_layout_qa — add pdf_path parameter + pdf2image previews
# ──────────────────────────────────────────────────────────────────
OLD_QA_FUNC = '''async def run_layout_qa(
    client,
    layout_result: dict,
    page_plan: dict,
    expected_content: dict,
    iteration: int,
    previous_qa_issues: list,
    cfg: dict,
) -> dict:
    """QA вёрстки — структурная проверка page_map и style_guide."""
    system_prompt = load_prompt(cfg["qa_layout"]["prompt_file"])

    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial",
            "iteration": iteration,
            "max_iterations": MAX_QA_ITERATIONS,
            "previous_agent": "layout_designer",
            "instruction": (
                "Проверь PDF-макет. ПЕРВАЯ проверка: текст читается (шрифты embedded, нет ■■■). "
                "Затем: page_plan соблюдён, фото не обрезаны, нумерация, оглавление, поля. "
                "Примечание: PDF не передаётся (режим структурной проверки). "
                "Проверяй по page_map, style_guide и expected_content."
            ),
        },
        "data": {
            "pdf_file": None,
            "page_map": layout_result.get("page_map", []),
            "page_plan": page_plan.get("page_plan", []),
            "style_guide": layout_result.get("style_guide", {}),
            "expected_content": expected_content,
            "layout_code_format": layout_result.get("layout_code", {}).get("format", ""),
            "technical_notes": layout_result.get("technical_notes", {}),
            **({"previous_qa_issues": previous_qa_issues} if previous_qa_issues else {}),
        }
    }

    result, in_tok, out_tok = await call_agent(
        client, "LAYOUT_QA", "qa_layout", system_prompt, user_message, cfg
    )
    return result'''

NEW_QA_FUNC = '''async def run_layout_qa(
    client,
    layout_result: dict,
    page_plan: dict,
    expected_content: dict,
    iteration: int,
    previous_qa_issues: list,
    cfg: dict,
    pdf_path: str | None = None,
) -> dict:
    """QA вёрстки — визуальная проверка PDF (pdf2image) + структурная по page_map."""
    system_prompt = load_prompt(cfg["qa_layout"]["prompt_file"])

    # ── pdf2image: convert first pages to PNG for vision QA ──────
    pdf_previews = []
    if pdf_path and pathlib.Path(pdf_path).exists():
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=120, first_page=1, last_page=5)
            import base64, io as _io
            for img in images:
                buf = _io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                pdf_previews.append({
                    "type": "image",
                    "media_type": "image/png",
                    "data": base64.b64encode(buf.getvalue()).decode("ascii"),
                })
            print(f"[QA] pdf2image: {len(pdf_previews)} страниц → vision")
        except Exception as ex:
            print(f"[QA] pdf2image failed ({ex}) — structural-only mode")

    instr = (
        "Проверь PDF-макет визуально (изображения страниц прикреплены). "
        "ПЕРВАЯ проверка: текст читается (шрифты embedded, нет ■■■)? "
        "Затем: page_plan соблюдён, фото не обрезаны, нумерация, оглавление, поля, "
        "нет висячих строк, нет оторванных заголовков."
        if pdf_previews else
        "PDF не передан (режим структурной проверки). "
        "Проверяй по page_map, style_guide, layout_instructions и expected_content."
    )

    user_message = {
        "context": {
            "project_id": PROJECT_ID,
            "phase": "A",
            "call_type": "initial",
            "iteration": iteration,
            "max_iterations": MAX_QA_ITERATIONS,
            "previous_agent": "layout_designer",
            "instruction": instr,
        },
        "data": {
            "pdf_file": pdf_path,
            "page_map": layout_result.get("page_map", []),
            "page_plan": page_plan.get("page_plan", []),
            "style_guide": layout_result.get("style_guide",
                layout_result.get("layout_instructions", {}).get("style_guide", {})),
            "expected_content": expected_content,
            "technical_notes": layout_result.get("technical_notes", {}),
            **({"previous_qa_issues": previous_qa_issues} if previous_qa_issues else {}),
            **({"pdf_previews": pdf_previews} if pdf_previews else {}),
        }
    }

    result, in_tok, out_tok = await call_agent(
        client, "LAYOUT_QA", "qa_layout", system_prompt, user_message, cfg
    )
    return result'''

if OLD_QA_FUNC in src:
    src = src.replace(OLD_QA_FUNC, NEW_QA_FUNC, 1)
    print("[OK] run_layout_qa patched (added pdf_path + pdf2image)")
else:
    print("[WARN] run_layout_qa not found — skipping")


# ──────────────────────────────────────────────────────────────────
# 4. QA call site — pass pdf_path
# ──────────────────────────────────────────────────────────────────
OLD_QA_CALL = '''        qa_raw = await run_layout_qa(
            client,
            layout_result=layout_result,
            page_plan=page_plan,
            expected_content=expected_content,
            iteration=qa_iteration,
            previous_qa_issues=previous_qa_issues,
            cfg=cfg,
        )'''

NEW_QA_CALL = '''        qa_raw = await run_layout_qa(
            client,
            layout_result=layout_result,
            page_plan=page_plan,
            expected_content=expected_content,
            iteration=qa_iteration,
            previous_qa_issues=previous_qa_issues,
            cfg=cfg,
            pdf_path=pdf_path if "pdf_path" in dir() else None,
        )'''

if OLD_QA_CALL in src:
    src = src.replace(OLD_QA_CALL, NEW_QA_CALL, 1)
    print("[OK] QA call site patched (pdf_path passed)")
else:
    print("[WARN] QA call site not found — skipping")


# ──────────────────────────────────────────────────────────────────
# Write
# ──────────────────────────────────────────────────────────────────
if src != orig:
    TARGET.write_text(src, encoding="utf-8")
    print(f"[SAVED] {TARGET}")
else:
    print("[WARN] No changes made")
    sys.exit(1)
