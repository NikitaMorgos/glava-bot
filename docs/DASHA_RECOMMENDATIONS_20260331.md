# Рекомендации по доработке — Stage 4 (по итогам тест-прогонов 2026-03-31)

---

## 1. Промпт: Cover Designer (`13_cover_designer_v2.md`)

### 1.1 Дублирующиеся правила
**Проблема:** В блоке «КРИТИЧЕСКИЕ ПРАВИЛА» дублируются правила 6 и 7.  
**Действие:** Удалить один из дублей (оставить одно правило с нужным номером).

### 1.2 Устаревшая модель в заметке для разработчика
**Проблема:** В разделе для разработчика упоминается `FLUX Schnell` как модель генерации портрета.  
**Действие:** Заменить на `google/nano-banana-2 (Replicate)`.  
Точная формулировка:
```
Модель генерации портрета: google/nano-banana-2 (Replicate API)
Передаёт реальное фото референса как image_input.
Fallback при недоступности: FLUX Schnell (text-to-image, без референса).
```

---

## 2. Промпт: Interview Architect (`11_interview_architect_v2.md`)

### 2.1 Дублирующийся раздел
**Проблема:** В промпте два раза присутствует раздел «Примеры ПЛОХИХ вопросов (исключить)».  
**Действие:** Удалить дубль, оставить один.

---

## 3. Спецификация: Stage 4 (`glava-spec-stage4.md`)

### 3.1 Устаревшая модель
**Проблема:** В секции Image Generation упоминается `FLUX Schnell`.  
**Действие:** Заменить на `google/nano-banana-2 (Replicate)` (аналогично п. 1.2).

---

## 4. Промпт: Layout Designer (`08_layout_designer_v1.md`) — КРИТИЧЕСКИЙ

### 4.1 Верстальщик хардкодит текст вместо чтения из файлов
**Проблема (корневая причина плохого PDF):**  
Layout Designer получает весь текст книги в промпте и вставляет его напрямую в генерируемый Python-код:
```python
story.append(Paragraph("Валентина родилась 17 декабря 1920...", style))
```
В результате: текст свежеинвентированный (не из пайплайна), фото не грузятся, шрифты кривые.

**Действие:** Добавить в блок **КРИТИЧЕСКИЕ ПРАВИЛА** следующий пункт:

```
— КОД ЧИТАЕТ ДАННЫЕ ИЗ ФАЙЛОВ, НЕ ХАРДКОДИТ ТЕКСТ.
  Текст книги, подписи к фото и метаданные передаются через
  входной JSON. Код должен читать их динамически:

      import json, pathlib
      book = json.loads(pathlib.Path(BOOK_JSON_PATH).read_text(encoding="utf-8"))
      for chapter in book["chapters"]:
          render_chapter(chapter["title"], chapter["content"])

  Переменные BOOK_JSON_PATH и PHOTOS_DIR инициализируются в начале
  скрипта из констант, которые оркестратор подставляет при генерации.
  Жёстко вписывать текст глав, цитаты и подписи к фото в код — ЗАПРЕЩЕНО.
```

### 4.2 Шрифты: неверные пути
**Проблема:** Код использует системные пути macOS (`/System/Library/Fonts/`), которых нет на Linux-сервере.  
**Действие:** Добавить в КРИТИЧЕСКИЕ ПРАВИЛА:
```
— Шрифты регистрировать только через абсолютные пути для Linux:
    /usr/share/fonts/truetype/freefont/FreeSerif.ttf       (serif regular)
    /usr/share/fonts/truetype/freefont/FreeSerifBold.ttf   (serif bold)
    /usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf (serif italic)
    /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf        (sans regular)
    /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf   (sans bold)
  Всю регистрацию оборачивать в try/except с fallback на Helvetica/Times.
  Не использовать /System/Library, /Windows/Fonts и другие OS-специфичные пути.
```

---

## 5. Оркестратор Stage 4 (`test_stage4_karakulina.py`) — задача разработчика

### 5.1 Interview Architect пропускается из-за неверного fact_map
**Проблема:** Скрипт по умолчанию передаёт `karakulina_historian_extended.json` как fact_map.  
У historian output нет поля `gaps` — поэтому Interview Architect видит `gaps=0` и пропускается.  
**Действие:** Изменить `DEFAULT_FACT_MAP` в скрипте:
```python
# Было:
DEFAULT_FACT_MAP = ROOT / "exports" / "karakulina_historian_extended_20260327_183739.json"
# Стало:
DEFAULT_FACT_MAP = ROOT / "exports" / "test_fact_map_karakulina_v5.json"  # выход Fact Extractor
```
Источник gaps — **Fact Extractor** (Stage 1), не Historian.

### 5.2 Layout Designer не получает пути к файлам
**Проблема:** В user message для Layout Designer не передаются `book_json_path` и `photos_dir`.  
Без них верстальщик не может генерировать код, читающий данные из файлов.  
**Действие:** При вызове Layout Designer добавить в user message:
```json
{
  "book_json_path": "/opt/glava/exports/karakulina_proofreader_report_20260329_065332.json",
  "photos_dir": "/opt/glava/exports/karakulina_photos/"
}
```

### 5.3 QA вёрстки падает т.к. PDF не существует
**Проблема:** Layout Designer генерирует Python-код, но не запускает его.  
QA (Роль 09) пытается проверить PDF — а PDF ещё не собран.  
Всё три итерации QA неизбежно падают с CRITICAL «PDF-файл не предоставлен».  
**Действие (архитектурное):** Между Layout Designer и QA добавить шаг **сборки PDF**:
```
Шаг 2.5: Запустить сгенерированный Python-скрипт → получить karakulina_biography.pdf
Шаг 3: QA передаётся путь к реальному PDF-файлу
```
Это либо делается в оркестраторе (subprocess.run), либо Layout Designer должен сам собирать PDF — что реалистичнее технически.

---

## 6. Сводная таблица приоритетов

| # | Файл | Что сделать | Приоритет |
|---|------|-------------|-----------|
| 1 | `08_layout_designer_v1.md` | Запретить хардкод текста, добавить правило чтения из файлов | 🔴 Высокий |
| 2 | `08_layout_designer_v1.md` | Добавить правильные пути к шрифтам для Linux | 🔴 Высокий |
| 3 | `test_stage4_karakulina.py` | DEFAULT_FACT_MAP → fact extractor output (для Interview Architect) | 🔴 Высокий |
| 4 | `test_stage4_karakulina.py` | Передавать `book_json_path` и `photos_dir` в Layout Designer | 🔴 Высокий |
| 5 | `test_stage4_karakulina.py` | Добавить шаг сборки PDF (subprocess) перед QA | 🟡 Средний |
| 6 | `13_cover_designer_v2.md` | Удалить дублирующиеся правила 6 и 7 | 🟢 Низкий |
| 7 | `13_cover_designer_v2.md` | Заменить FLUX Schnell → google/nano-banana-2 | 🟢 Низкий |
| 8 | `11_interview_architect_v2.md` | Удалить дублирующийся раздел «Примеры ПЛОХИХ вопросов» | 🟢 Низкий |
| 9 | `glava-spec-stage4.md` | Заменить FLUX Schnell → google/nano-banana-2 | 🟢 Низкий |

---

## 7. Что уже исправлено в коде (не требует действий Даши)

| Что | Где |
|-----|-----|
| Референс-фото теперь передаётся в nano-banana-2 | `scripts/test_stage4_karakulina.py` |
| Retry 3×30с при "Service unavailable" для nano-banana-2 | `replicate_client.py` |
| Cover Designer v2 загружен на сервер и активен | `prompts/pipeline_config.json` |
| Interview Architect v2 загружен на сервер | `prompts/pipeline_config.json` |
| Fact Extractor v3.2 загружен на сервер | `prompts/pipeline_config.json` |
| Временный PDF-сборщик из данных пайплайна | `scripts/build_karakulina_pdf.py` |
