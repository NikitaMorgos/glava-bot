# Этап 08 — Верстальщик (Layout Designer)

> **ID:** `08_layout_designer`  
> **Версия промпта:** v1.0  
> **Статус:** 🔴 Требует доработки  
> **Обновлён:** 2026-03-31  

---

## Для Даши — что делает этот агент

### Роль
Получает финальный текст книги, page_plan от Арт-директора и список фото — и генерирует Python/ReportLab код для сборки PDF.  
Это **технический агент**: его вывод — не текст, а работающий код. Проверить его результат можно только запустив этот код.

### Что должно быть в хорошем результате
- [ ] Код запускается без ошибок на сервере
- [ ] Текст берётся **из входного JSON-файла**, не хардкодится в коде
- [ ] Фото загружаются по абсолютным путям на сервере
- [ ] Шрифты регистрируются через реальные TTF-файлы (не системные пути macOS)
- [ ] Все главы из proofreader_report присутствуют в PDF
- [ ] Callouts и исторические вставки визуально выделены

### Типичные ошибки и как их ловить
| Симптом | Вероятная причина | Что поправить |
|---------|-------------------|---------------|
| В PDF чужой текст / придуманный | Агент хардкодит текст из контекста, не читает из файлов | **КРИТИЧНО:** добавить правило «код читает данные из файлов» (см. п. 4.1 рекомендаций) |
| `KeyError: font not found` | Код пытается использовать macOS/Windows-пути к шрифтам | Добавить правило с правильными Linux-путями к шрифтам |
| Фото не загружаются | В manifest.json Windows-пути; на сервере — Linux | Правило: пути к фото через переменную `PHOTOS_DIR`, не хардкод |
| PDF не создаётся, QA падает | Код генерируется, но не запускается автоматически | Архитектурный вопрос: нужен шаг сборки PDF перед QA (задача разработки) |

### ⚠️ Известная системная проблема
Верстальщик видит текст книги в своём промпте и вставляет его прямо в код.  
**Это неверно.** Код должен читать текст из файла. До исправления промпта PDF собирается отдельным скриптом `build_*_pdf.py`.  
**Статус:** промпт v2.0 запланирован (задача в рекомендациях для Даши).

### Как проверить результат вручную
1. Запустить `scripts/build_*_pdf.py` — собирает PDF из реальных данных
2. Открыть PDF: текст совпадает с proofreader_report? Фото на месте? Шрифты читаемые?
3. Красный флаг: в PDF есть текст которого нет в proofreader_report

---

## Для разработки — техническая спецификация

### Место в пайплайне
```
[15 Art Director] → [08 LAYOUT DESIGNER] → [сборка PDF] → [09 QA]
```
> ⚠️ Между Layout Designer и QA **обязательно** нужен шаг запуска сгенерированного кода.  
> QA проверяет PDF-файл, а не код. Без сборки QA всегда падает с CRITICAL.

### Входные данные

```json
{
  "project_id": "string",
  "book_final": {"chapters": [...], "callouts": [...], "style_passport": {...}},
  "page_plan": [{"page_num": 1, "content_type": "cover", ...}],
  "photos": [{"photo_id": "photo_002", "local_path": "/opt/glava/exports/...", "caption": "..."}],
  "cover_composition": {...},
  "book_json_path": "/opt/glava/exports/karakulina_proofreader_report_*.json",
  "photos_dir": "/opt/glava/exports/karakulina_photos/"
}
```
> `book_json_path` и `photos_dir` **должны** передаваться — без них код будет хардкодить текст.  
> **Сейчас не передаются** — это баг оркестратора (см. п. 5.2 рекомендаций).

### Выходные данные

```json
{
  "layout_code": {
    "format": "python_reportlab",
    "code": "#!/usr/bin/env python3\n...",
    "build_command": "python3 karakulina_layout.py",
    "dependencies": ["reportlab>=3.6.0", "Pillow>=8.0.0"]
  },
  "page_map": [{"page_num": 1, "content": "cover", "elements": [...]}],
  "technical_notes": {"total_pages": 34, "print_ready": false}
}
```

### Шаг сборки PDF (после Layout Designer)

```python
# В оркестраторе (задача разработки):
import subprocess, pathlib

layout_code = result["layout_code"]["code"]
script_path = exports_dir / f"{prefix}_layout_code_{ts}.py"
script_path.write_text(layout_code, encoding="utf-8")

# Запустить скрипт для сборки PDF
proc = subprocess.run(
    ["python3", str(script_path)],
    capture_output=True, text=True,
    cwd=str(exports_dir)
)
if proc.returncode != 0:
    print("[ERROR] PDF build failed:", proc.stderr[-500:])
else:
    print("[OK] PDF built")
    # Передать путь к PDF в QA
```

### Конфигурация

```json
{
  "layout_designer": {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 64000,
    "temperature": 0.25,
    "prompt_file": "08_layout_designer_v1.md"
  }
}
```

**Почему такие параметры:**
- `max_tokens: 64000` — код PDF-сборщика большой; при 32000 обрезался на 22+ фото
- `temperature: 0.25` — код должен быть рабочим, минимальная вариативность

### Доступные шрифты на сервере (Linux)

```
/usr/share/fonts/truetype/freefont/FreeSerif.ttf        (serif regular)
/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf    (serif bold)
/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf  (serif italic)
/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf         (sans regular)
/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf    (sans bold)
```
Для Google Fonts (Playfair Display и др.) — нужно скачать отдельно в `/opt/glava/fonts/`.

### Временное решение (до исправления промпта)
Пока промпт не исправлен, PDF собирается через:
```bash
python3 scripts/build_karakulina_pdf.py
```
Этот скрипт читает данные из proofreader_report и собирает корректный PDF.

### История изменений

| Версия | Дата | Что изменилось |
|--------|------|----------------|
| v1.0 | 2026-03-06 | Первая версия (Даша) |
| v2.0 | запланирован | Запрет хардкода, Linux-шрифты, чтение из файлов |
