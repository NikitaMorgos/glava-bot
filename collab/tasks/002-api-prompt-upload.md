# 002 — API-загрузка промптов, Админка только для чтения

**Статус:** `done`
**Автор:** Разработчик
**Дата:** 2026-04-06
**Тип:** `изменение-процесса`

---

## Контекст

Раньше промпты обновлялись тремя способами:
1. Даша загружает через веб-форму в Админке (только сервер, Dropbox не обновляется)
2. Разработчик делает scp вручную (только сервер)
3. Cursor редактирует локально, деплоит через scp

Это приводило к расхождению между Dropbox и сервером.

## Спек

**Новый процесс:**
- Dropbox — единственное место редактирования
- Сервер обновляется через `POST /api/prompts/<role>/upload`
- Дашин Claude Code и Cursor работают одинаково: редактируют в Dropbox → деплоят через API
- Админка: только просмотр и скачивание, загрузка убрана

## Реализация

**Что сделано:**
1. Добавлен `POST /api/prompts/<role>/upload` в `admin/blueprints/api.py`
   — авторизация по `X-Api-Key`, принимает multipart `file` + опционально `filename`
   — бэкап старого файла, сохранение нового, обновление pipeline_config.json
2. Шаблон `admin/templates/dasha/pipeline_prompts.html` — убраны кнопки загрузки,
   добавлен баннер с описанием нового процесса
3. `admin/blueprints/dasha.py` — эндпоинт `pipeline_prompts_upload` помечен как deprecated
4. `collab/context/prompt-workflow.md` — инструкция для Claude Code

**Файлы изменены:**
- `admin/blueprints/api.py`
- `admin/blueprints/dasha.py`
- `admin/templates/dasha/pipeline_prompts.html`
- `collab/context/prompt-workflow.md` (новый)

## История статусов

| Дата | Статус | Кто |
|------|--------|-----|
| 2026-04-06 | `done` | Cursor |
