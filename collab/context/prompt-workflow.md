# Как работать с промптами пайплайна GLAVA

> Этот файл — инструкция для Claude Code (Даша) и Cursor (разработчик).
> Описывает единственный правильный способ обновлять промпты.

---

## Главное правило

**Dropbox → API → Сервер**

1. Редактируешь файл в `Dropbox/GLAVA/prompts/`
2. Деплоишь через `POST /api/prompts/<role>/upload`
3. Сервер обновлён. Dropbox актуален. Готово.

Веб-загрузка в Админке отключена. Не используй `scp` вручную.

---

## Переменные окружения (нужны один раз)

Разработчик уже сгенерировал ключ и добавил его на сервер. Тебе нужно сохранить его **локально на своей машине** — не в Dropbox.

### Как сохранить ключ (macOS / Linux)

Создай файл `~/.glava_env`:
```
GLAVA_API_KEY=a9d3d3c4a9f8b9104c22bb87e44b9e22938c9b93bf3f98e5148c1c7b06070e47
GLAVA_ADMIN_URL=https://admin.glava.family
```

Или добавь в `~/.zshrc` / `~/.bashrc`:
```bash
export GLAVA_API_KEY=a9d3d3c4a9f8b9104c22bb87e44b9e22938c9b93bf3f98e5148c1c7b06070e47
export GLAVA_ADMIN_URL=https://admin.glava.family
```

### Как Claude Code читает ключ

В начале любого скрипта деплоя:
```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / ".glava_env")
API_KEY = os.environ["GLAVA_API_KEY"]
ADMIN_URL = os.environ.get("GLAVA_ADMIN_URL", "https://admin.glava.family")
```

---

## Сценарий 1: обновить существующий промпт (та же версия)

```bash
# Отредактировал prompts/05_literary_editor_v3.md
# Деплоишь под тем же именем:

curl -X POST "$GLAVA_ADMIN_URL/api/prompts/literary_editor/upload" \
  -H "X-Api-Key: $GLAVA_API_KEY" \
  -F "file=@prompts/05_literary_editor_v3.md"

# Ответ: {"ok": true, "saved_as": "05_literary_editor_v3.md", "size_kb": "12.3"}
```

---

## Сценарий 2: создать новую версию промпта

```bash
# Создал новый файл prompts/05_literary_editor_v4.md
# Деплоишь с новым именем — конфиг обновится автоматически:

curl -X POST "$GLAVA_ADMIN_URL/api/prompts/literary_editor/upload" \
  -H "X-Api-Key: $GLAVA_API_KEY" \
  -F "file=@prompts/05_literary_editor_v4.md" \
  -F "filename=05_literary_editor_v4.md"

# Ответ: {"ok": true, "saved_as": "05_literary_editor_v4.md", "size_kb": "13.1"}
# pipeline_config.json на сервере теперь указывает на v4.md
```

---

## Маппинг: агент → role для API

| Агент | role (для URL) |
|-------|---------------|
| 01 · Очиститель | `cleaner` |
| 02 · Фактолог | `fact_extractor` |
| 12 · Историк | `historian` |
| 03 · Писатель | `ghostwriter` |
| 04 · Фактчекер | `fact_checker` |
| 05 · Литредактор | `literary_editor` |
| 06 · Корректор | `proofreader` |
| 07 · Фоторедактор | `photo_editor` |
| 08 · Верстальщик | `layout_designer` |
| 09 · QA вёрстки | `qa_layout` |
| 13 · Обложка | `cover_designer` |
| 15 · Арт-директор | `layout_art_director` |
| 11 · Интервьюер | `interview_architect` |

---

## Синхронизация: скачать актуальные версии с сервера

Если давно не открывала папку или хочешь убедиться что всё актуально:

```bash
cd ~/Dropbox/GLAVA
python scripts/sync_prompts.py
```

Скрипт читает `pipeline_config.json`, скачивает с сервера все активные версии
которых нет локально.

---

## Как написать задачу на изменение промпта

1. Скопируй `collab/tasks/_template.md` → `collab/tasks/NNN-название.md`
2. Заполни спек: что изменить, зачем, как проверить
3. Статус: `new`
4. Если можешь реализовать сама — отредактируй промпт, задеплой через API,
   смени статус на `dasha-review`
5. Если нужен разработчик (изменение кода) — оставь статус `new`,
   разработчик подхватит

---

## Что НЕ делать

- Не загружать промпты через Админку (веб-форма отключена)
- Не редактировать файлы напрямую на сервере
- Не делать `scp` вручную (используй API)
- Не создавать новую версию поверх старой — всегда новый файл с суффиксом `_v4.1.md`
